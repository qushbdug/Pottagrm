# Pro Telegram Bot (Clean Skeleton)

- Role-aware inline menu (customer, supplier, admin)
- Strong configuration management via environment variables
- Structured logging and robust error handling
- Minimal, extendable architecture (config, logging, bot wiring)

## Requirements

- Python 3.9+
- Telegram Bot API token

## Installation

```bash
cd pro_telegram_bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set environment variables (create a `.env` file locally if desired):

```env
BOT_TOKEN=123456:ABC-DEF
ADMIN_USER_IDS=12345,67890
LOG_LEVEL=INFO
```

## Run

```bash
python3 main.py
```

## Usage

- /start: shows a role-aware menu
- /be_customer, /be_supplier, /be_admin: simulate role changes for testing

Buttons:
- 💳 محفظتي, 🛒 شراء كروت, 💸 تحويل رصيد, ❓ المساعدة
- Supplier-only: 🏪 لوحة المزود, 📶 إدارة الشبكات
- Admin-only: 👑 لوحة الإدارة

## Tests

Install dev deps (pytest):

```bash
pip install pytest
pytest -q
```

## Next Steps / Suggestions

- Replace in-memory user store with a database (SQLite/PostgreSQL) and repository layer.
- Add domain services for wallet, transfers, and network management with unit tests.
- Introduce dependency injection for testability.
- Implement i18n and message templating to avoid hard-coded strings.
- Add CI (lint, tests) and containerization for deployment.