import json
import os
import asyncio
import traceback
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN environment variable not set")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            # Bot application yaratish
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_command))
            
            # Update ni qayta ishlash (async)
            update = Update.de_json(data, app.bot)
            asyncio.run(app.process_update(update))
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            # Xatolikni logga chiqarish
            err = traceback.format_exc()
            print(err)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Webhook is active")

# Handler funksiyalar (async)
async def start(update: Update, context):
    await update.message.reply_text(
        "Assalomu alaykum! Testni boshlash uchun tugmani bosing:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Testni boshlash", url="https://ielts-beast.vercel.app")]
        ])
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "/start - testni boshlash\n/help - yordam"
    )
