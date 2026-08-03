#!/usr/bin/env python3
"""
FiberHome Router Password Bot - Telegram (Ad Verification + Direct Bot Reveal)
----------------------------------------------------------------------------
"""

import os
import re
import json
import logging
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

raw_bot_token = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = "".join(raw_bot_token.split())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

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


def generate_fiberhome_password(clean_hex: str) -> str:
    """FiberHome Password Generation Algorithm"""
    char_map = {
        '0': 'f', '1': 'e', '2': 'd', '3': 'c',
        '4': 'b', '5': 'a', '6': '9', '7': '8'
    }
    converted = "".join(char_map.get(c, c) for c in clean_hex)
    return f"wlan{converted}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to FiberHome Password Generator!**\n\n"
        "Send me your router name (e.g., `fh_123574` or `123574`) to get started.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إذا كانت الرسالة القادمة تحتوي على بيانات web_app_data، قم بتوجيهها مباشرة للـ Handler الخاص بها
    if update.effective_message and update.effective_message.web_app_data:
        await handle_webapp_data(update, context)
        return

    text = update.message.text.strip() if update.message and update.message.text else ""
    if not text:
        return

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
            
            # Cache buster & name query
            query_string = urlencode({"name": clean_hex, "v": "30"})
            url = f"{BASE_WEBAPP_URL}?{query_string}"
            
            buttons.append([InlineKeyboardButton(
                f"🔒 {full_network_name}", 
                web_app=WebAppInfo(url=url)
            )])
            validated_names.append(f"`{full_network_name}`")
            
        except ValueError:
            errors.append(f"❌ `{token}` -> No valid hex digits found.")

    if buttons:
        message_text = "Tap to reveal the password (watch a short ad first):"
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    if errors:
        await update.message.reply_text("\n".join(errors))


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles verification signal returned from Mini App after ad completion"""
    try:
        raw_data = update.effective_message.web_app_data.data
        logging.info(f"Received WebApp Data: {raw_data}")
        
        data = json.loads(raw_data)
        router_name = data.get("name", "")
        
        clean_hex, full_network_name = validate_router_name(router_name)
        password = generate_fiberhome_password(clean_hex)
        
        response_text = (
            f"🎉 **Ad Watch Verified!**\n\n"
            f"📌 **Network:** `{full_network_name}`\n"
            f"🔑 **Password:** `{password}`"
        )
        
        await update.effective_message.reply_text(response_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error processing webapp data: {e}")
        await update.effective_message.reply_text("❌ Verification failed. Please try again.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    # التقاط بيانات الـ WebApp سواء بالفلتر الخاص بها أو كـ StatusUpdate
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    # الفلتر العام للرسائل
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
