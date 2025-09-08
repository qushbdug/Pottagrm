#!/usr/bin/env python3
"""
UI Utilities for Pottagrm Enhanced Bot
"""

from src.core.config import EMOJIS, USER_ROLES

def format_user_info(user) -> str:
    """Format user information for display"""
    if not user:
        return "معلومات المستخدم غير متوفرة"

    role_name = USER_ROLES.get(user['role'], user['role'])
    status = "مفعل" if user['is_active'] else "غير مفعل"

    return f"""
{EMOJIS['user']} **{user['full_name']}**
{EMOJIS['phone']} {user['phone']}
🏷️ {role_name}
{EMOJIS['wallet']} {user['balance']:.2f} ريال
{EMOJIS['id']} {user['wallet_number']}
📊 حالة الحساب: {status}
"""
