#!/usr/bin/env python3
"""
Pro Telegram Bot (clean skeleton)
- Role-aware menu rendering (customer, supplier, admin)
- Robust error handling and structured logging
- Clear separation of configuration, logging, and bot wiring

Requires: python-telegram-bot>=20.7
"""

from __future__ import annotations

import logging
from typing import Dict, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

from .config import Settings
from .logger import setup_logging


LOG = logging.getLogger(__name__)

# In-memory user store for demo purposes (replace with DB)
User = Dict[str, str]
_USERS: Dict[int, User] = {}


def build_main_menu(role: str) -> InlineKeyboardMarkup:
    """Return a role-aware inline keyboard for the main menu."""
    buttons: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("💳 محفظتي", callback_data="wallet"),
         InlineKeyboardButton("🛒 شراء كروت", callback_data="buy")],
        [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer"),
         InlineKeyboardButton("❓ المساعدة", callback_data="help")],
    ]
    if role == "supplier":
        buttons.append([
            InlineKeyboardButton("🏪 لوحة المزود", callback_data="supplier_panel"),
            InlineKeyboardButton("📶 إدارة الشبكات", callback_data="manage_networks"),
        ])
    if role in ("admin", "super_admin"):
        buttons.append([
            InlineKeyboardButton("👑 لوحة الإدارة", callback_data="admin_panel"),
        ])
    return InlineKeyboardMarkup(buttons)


def get_role(user_id: int) -> str:
    user = _USERS.get(user_id)
    return user.get("role", "customer") if user else "customer"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_user
    user_id = update.effective_user.id
    _USERS.setdefault(user_id, {"role": "customer"})
    role = get_role(user_id)

    await update.message.reply_text(
        f"مرحبا بك! تم ضبط دورك الحالي على: {role}.\n"
        f"يمكنك تغيير الدور للاختبار باستخدام الأوامر: /be_customer /be_supplier /be_admin",
        reply_markup=build_main_menu(role),
    )


async def be_customer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _USERS[update.effective_user.id] = {"role": "customer"}
    await update.message.reply_text("تم التغيير إلى: عميل", reply_markup=build_main_menu("customer"))


async def be_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _USERS[update.effective_user.id] = {"role": "supplier"}
    await update.message.reply_text("تم التغيير إلى: مزود", reply_markup=build_main_menu("supplier"))


async def be_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _USERS[update.effective_user.id] = {"role": "admin"}
    await update.message.reply_text("تم التغيير إلى: مشرف", reply_markup=build_main_menu("admin"))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    role = get_role(query.from_user.id)
    data = query.data or ""

    # Minimal demo routing
    if data == "wallet":
        await query.edit_message_text("💳 محفظتك فارغة الآن (تجريبي)", reply_markup=build_main_menu(role))
    elif data == "buy":
        await query.edit_message_text("🛒 شراء (تجريبي)", reply_markup=build_main_menu(role))
    elif data == "transfer":
        await query.edit_message_text("💸 تحويل (تجريبي)", reply_markup=build_main_menu(role))
    elif data == "supplier_panel":
        if role != "supplier":
            await query.edit_message_text("❌ هذه الميزة للمزود فقط", reply_markup=build_main_menu(role))
        else:
            await query.edit_message_text("🏪 لوحة المزود (تجريبي)", reply_markup=build_main_menu(role))
    elif data == "manage_networks":
        if role != "supplier":
            await query.edit_message_text("❌ هذه الميزة للمزود فقط", reply_markup=build_main_menu(role))
        else:
            await query.edit_message_text("📶 إدارة الشبكات (تجريبي)", reply_markup=build_main_menu(role))
    elif data == "admin_panel":
        if role not in ("admin", "super_admin"):
            await query.edit_message_text("❌ هذه الميزة للمشرفين فقط", reply_markup=build_main_menu(role))
        else:
            await query.edit_message_text("👑 لوحة الإدارة (تجريبي)", reply_markup=build_main_menu(role))
    elif data == "help":
        await query.edit_message_text("❓ المساعدة: استخدم الأزرار أو الأوامر المتاحة.", reply_markup=build_main_menu(role))
    else:
        await query.edit_message_text("⚠️ خيار غير معروف.", reply_markup=build_main_menu(role))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Echo-like behavior for unsupported messages in this skeleton
    role = get_role(update.effective_user.id)
    await update.message.reply_text("نص غير معروف، استخدم الأزرار.", reply_markup=build_main_menu(role))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOG.exception("Unhandled error: %s", context.error)
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(update.effective_chat.id, "حدث خطأ غير متوقع")
    except Exception:
        pass


def build_app(settings: Settings) -> Application:
    return (
        Application.builder()
        .token(settings.bot_token)
        .build()
    )


def wire_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("be_customer", be_customer))
    app.add_handler(CommandHandler("be_supplier", be_supplier))
    app.add_handler(CommandHandler("be_admin", be_admin))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)


def run() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)

    app = build_app(settings)
    wire_handlers(app)

    LOG.info("Starting Pro Telegram Bot...")
    app.run_polling()


if __name__ == "__main__":
    run()