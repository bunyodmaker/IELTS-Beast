import json
import os
import asyncpg
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            data = json.loads(body)
            
            # Bot application yaratish
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_command))
            
            # Webhook dan kelgan update ni qayta ishlash
            update = Update.de_json(data, app.bot)
            app.process_update(update)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Webhook is active")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\n"
        "IELTS Reading testini boshlash uchun tugmani bosing:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Testni boshlash", url="https://ielts-beast.vercel.app")]
        ])
    )
    # Foydalanuvchini bazaga yozib qo'yamiz
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_sessions (user_id, full_name) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
                user.id, user.full_name
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot yordami:\n"
        "/start - Testni boshlash\n"
        "/help - Yordam\n"
        "/status - Natijalaringizni ko'rish"
    )

# Bu funksiya API dan chaqiriladi (test_results ga yozilganda)
async def send_to_channel(result_id):
    """Natijalarni kanalga yuborish"""
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM test_results WHERE id = $1",
                result_id
            )
            if not row:
                return
            
            text = (
                f"🎯 **Yangi IELTS natijasi!**\n"
                f"👤 **Ism:** {row['full_name']}\n"
                f"📝 **Ball:** {row['score']}/40\n"
                f"📊 **Band:** {row['reading_band']}\n"
                f"⏱ **Vaqt:** {row['time_spent']} daqiqa\n"
                f"📅 **Sana:** {row['submitted_at'].strftime('%d.%m.%Y %H:%M')}"
            )
            
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(chat_id=CHANNEL_ID, text=text)
