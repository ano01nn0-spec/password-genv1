#!/usr/bin/env python3
"""
FiberHome Router Password Bot - Telegram (Pure Bot Service)
----------------------------------------------------------------------------
"""

import os
import re
import logging
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# التوكن مدمج مباشرة
BOT_TOKEN = "8879617300:AAFTuNpM77iZ_qTG5idjVwDCynM_9HQB1iU"

raw_mini_app_url = os.environ.get("MINI_APP_URL", "")
MINI_APP_URL = raw_mini_app_url.strip()

if not MINI_APP_URL:
    raise RuntimeError("MINI_APP_URL environment variable is not set!")

BASE_WEBAPP_URL = MINI_APP_URL.rstrip('/')
logging.basicConfig(level=logging.INFO)


def validate_router_name(router_name: str) -> tuple[str, str]:
    raw = router_name.strip()
    clean = re.sub(r'^(fh[_\-]?|Fh[_\-]?)', '', raw, flags=re.IGNORECASE).strip().lower()

    if not clean or len(clean) != 6 or not all(c in '0123456789abcdef' for c in clean):
        raise ValueError("Invalid format. Router name must contain 6 hex characters.")

    return clean, f"Fh_{clean}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to FiberHome Password Generator!**\n\n"
        "Send me your router name (e.g., `fh_123574` or `123574`) to get started.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    lines = [line for line in text.splitlines() if line.strip()]

    tokens = []
    for line in lines:
        tokens.extend(line.split())

    buttons = []
    errors = []

    for token in tokens:
        try:
            clean_hex, full_network_name = validate_router_name(token)
            
            query_string = urlencode({
                "name": clean_hex, 
                "chat_id": msg.chat_id,
                "v": "200"
            })
            url = f"{BASE_WEBAPP_URL}?{query_string}"
            
            buttons.append([InlineKeyboardButton(
                f"🔒 {full_network_name}", 
                web_app=WebAppInfo(url=url)
            )])
            
        except ValueError:
            errors.append(f"❌ `{token}` -> Invalid format.")

    if buttons:
        await msg.reply_text(
            "Tap to reveal the password (watch a short ad first):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    if errors:
        await msg.reply_text("\n".join(errors))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
