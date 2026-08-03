#!/usr/bin/env python3
"""
FiberHome Router Password Bot - Telegram (with Mini App + ad-gated reveal)
----------------------------------------------------------------------------
User sends a router name (e.g., fh_48a4ce or Fh_1ff1c1). The bot validates
the format, displays the recognized network name, and provides a button
to open the Mini App to unlock the password.
"""

import os
import re
import logging
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# Clean environment variables thoroughly to prevent HTTPX InvalidURL error (\n or spaces)
raw_bot_token = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = "".join(raw_bot_token.split())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

raw_mini_app_url = os.environ.get("MINI_APP_URL", "")
MINI_APP_URL = raw_mini_app_url.strip()

if not MINI_APP_URL:
    raise RuntimeError("MINI_APP_URL environment variable is not set!")

# Ensure base URL has no trailing slash
BASE_WEBAPP_URL = MINI_APP_URL.rstrip('/')

logging.basicConfig(level=logging.INFO)


def validate_router_name(router_name: str) -> tuple[str, str]:
    """
    Validates router name and returns a tuple: (cleaned_hex, full_network_name)
    Example input: "fh_1ff1c1" -> ("1ff1c1", "Fh_1ff1c1")
    """
    raw = router_name.strip()
    clean = re.sub(r'^(fh[_\-]?|Fh[_\-]?)', '', raw, flags=re.IGNORECASE).strip().lower()

    if not clean or len(clean) != 6 or not all(c in '0123456789abcdef' for c in clean):
        raise ValueError("Invalid format. Router name must contain exactly 6 hex characters.")

    formatted_network_name = f"Fh_{clean}"
    return clean, formatted_network_name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to FiberHome Password Generator!**\n\n"
        "Send me your router name (e.g., `fh_1ff1c1` or `1ff1c1`) and I will help you retrieve its default Wi-Fi password.\n\n"
        " You can also send multiple names separated by newlines.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = [line for line in text.splitlines() if line.strip()]

    tokens = []
    for line in lines:
        tokens.extend(line.split())

    buttons = []
    errors = []
    validated_names = []

    for token in tokens:
        try:
            clean_hex, full_network_name = validate_router_name(token)
            
            # Cache buster & parameter passing for Mini App
            query_string = urlencode({"name": clean_hex, "v": "15"})
            url = f"{BASE_WEBAPP_URL}?{query_string}"
            
            buttons.append([InlineKeyboardButton(
                f"🔓 Watch Ad to Unlock Password ({full_network_name})", 
                web_app=WebAppInfo(url=url)
            )])
            validated_names.append(f"`{full_network_name}`")
            
        except ValueError:
            errors.append(f"❌ `{token}` -> Invalid router name format.")

    if buttons:
        networks_str = ", ".join(validated_names)
        message_text = (
            f"✅ **Network Identified:** {networks_str}\n\n"
            "Tap the button below to watch a short ad and reveal your Wi-Fi password:"
        )
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    if errors:
        await update.message.reply_text("\n".join(errors), parse_mode="Markdown")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
