#!/usr/bin/env python3
"""
FiberHome Router Password Bot - Telegram (with Mini App + ad-gated reveal)
----------------------------------------------------------------------------
User sends a router name (e.g. fh_48a4ce). The bot validates the format and
replies with a button that opens the Mini App (WebApp), where the customer
watches a short ad and then sees the password with a copy button.

SETUP:
1. pip install python-telegram-bot --break-system-packages
2. Set env vars: BOT_TOKEN (from BotFather) and MINI_APP_URL
   (the public https URL of the deployed webapp, e.g.
   https://your-webapp.up.railway.app)
3. Run: python3 fh_telegram_bot.py
"""

import os
import re
import logging
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# Clean environment variables thoroughly to prevent HTTPX InvalidURL error (\n or spaces)
raw_bot_token = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = "".join(raw_bot_token.split())  # Removes all whitespace, newline (\n), and carriage returns (\r)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

raw_mini_app_url = os.environ.get("MINI_APP_URL", "")
MINI_APP_URL = raw_mini_app_url.strip()

if not MINI_APP_URL:
    raise RuntimeError("MINI_APP_URL environment variable is not set!")

# Ensure base URL has no trailing slash
BASE_WEBAPP_URL = MINI_APP_URL.rstrip('/')

logging.basicConfig(level=logging.INFO)


def validate_router_name(router_name: str) -> str:
    """
    Checks the router name has the right shape (fh_XXXXXX, hex only).
    Returns the cleaned name (without the fh_ prefix) or raises ValueError.
    The actual password swap happens client-side inside the Mini App,
    only after the customer watches the ad.
    """
    name = router_name.strip().lower()
    name = re.sub(r'^fh[_\-]?', '', name)
    name = name.strip()

    if not name or not all(c in '0123456789abcdef' for c in name):
        raise ValueError(f"No valid hex digits found in: {router_name}")

    return name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a router name (e.g. fh_48a4ce) and I'll open the app to reveal its password.\n"
        "You can also send several names, one per line, for a batch."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = [line for line in text.splitlines() if line.strip()]

    tokens = []
    for line in lines:
        tokens.extend(line.split())

    buttons = []
    errors = []
    for token in tokens:
        try:
            clean_name = validate_router_name(token)
            # Clean and clean query parameter mapping for Telegram WebApp compatibility
            query_string = urlencode({"name": clean_name})
            url = f"{BASE_WEBAPP_URL}?{query_string}"  # Fixed: removed trailing slash before '?'
            
            buttons.append([InlineKeyboardButton(
                f"🔓 {token}", web_app=WebAppInfo(url=url)
            )])
        except ValueError as e:
            errors.append(f"{token} -> {e}")

    if buttons:
        await update.message.reply_text(
            "Tap to reveal the password (watch a short ad first):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    if errors:
        await update.message.reply_text("\n".join(errors))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
