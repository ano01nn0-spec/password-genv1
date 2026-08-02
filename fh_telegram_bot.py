#!/usr/bin/env python3
"""
FiberHome Router Password Bot - Telegram
------------------------------------------
Send the router name (e.g. fh_48a4ce) to the bot, it replies with the password.

SETUP:
1. pip install python-telegram-bot --break-system-packages   (or in a venv)
2. Replace BOT_TOKEN below with the token from @BotFather
3. Run: python3 fh_telegram_bot.py
4. Keep it running 24/7 on a VPS (see notes at the bottom of the chat)
"""

import os
import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# The bot token is read from an environment variable (set it in Railway's
# "Variables" tab as BOT_TOKEN). This keeps the token out of the code/repo.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(level=logging.INFO)


def swap_char(ch: str) -> str:
    """Swap a single hex digit with its complement (15 - value)."""
    val = int(ch, 16)
    return format(15 - val, 'x')


def get_password(router_name: str) -> str:
    name = router_name.strip().lower()
    name = re.sub(r'^fh[_\-]?', '', name)
    name = name.strip()

    if not name or not all(c in '0123456789abcdef' for c in name):
        raise ValueError(f"No valid hex digits found in: {router_name}")

    swapped = ''.join(swap_char(c) for c in name)
    return "wlan" + swapped


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a router name (e.g. fh_48a4ce) and I'll give you its default password.\n"
        "You can also send several names, one per line, for a batch."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = [line for line in text.splitlines() if line.strip()]

    replies = []
    for line in lines:
        # allow multiple names separated by spaces on the same line too
        for token in line.split():
            try:
                pwd = get_password(token)
                replies.append(f"{token} -> {pwd}")
            except ValueError as e:
                replies.append(f"{token} -> Error: {e}")

    await update.message.reply_text("\n".join(replies))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
