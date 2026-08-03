#!/usr/bin/env python3
"""
FiberHome Router Password Bot + Web Server API
----------------------------------------------------------------------------
"""

import os
import re
import asyncio
import logging
from urllib.parse import urlencode
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

raw_bot_token = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = "".join(raw_bot_token.split())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

raw_mini_app_url = os.environ.get("MINI_APP_URL", "")
MINI_APP_URL = raw_mini_app_url.strip()

if not MINI_APP_URL:
    raise RuntimeError("MINI_APP_URL environment variable is not set!")

BASE_WEBAPP_URL = MINI_APP_URL.rstrip('/')
PORT = int(os.environ.get("PORT", 8080))

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
            
            # نمرر chat_id و name في الـ URL
            query_string = urlencode({
                "name": clean_hex, 
                "chat_id": msg.chat_id,
                "v": "60"
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


# --- HTTP API Web Server ---
async def handle_verify_api(request):
    try:
        data = await request.json()
        router_name = data.get("name", "")
        chat_id = data.get("chat_id")

        if not router_name or not chat_id:
            return web.json_response({"error": "Missing parameters"}, status=400)

        clean_hex, full_network_name = validate_router_name(router_name)
        password = generate_fiberhome_password(clean_hex)

        bot = request.app['bot']
        response_text = (
            f"🎉 **Ad Watch Verified!**\n\n"
            f"📌 **Network:** `{full_network_name}`\n"
            f"🔑 **Password:** `{password}`"
        )

        await bot.send_message(chat_id=chat_id, text=response_text, parse_mode="Markdown")
        return web.json_response({"status": "success"})
    except Exception as e:
        logging.error(f"API Error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def serve_index(request):
    return web.FileResponse('./index.html')


async def main():
    # 1. إعداد تطبيق البوت
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    # 2. إعداد سيرفر الـ Web للـ HTML والـ API
    web_app = web.Application()
    web_app['bot'] = bot_app.bot
    web_app.router.add_post('/api/verify', handle_verify_api)
    web_app.router.add_get('/', serve_index)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    print(f"Server and Bot running on port {PORT}...")
    
    # الإبقاء على التشغيل المستمر
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
