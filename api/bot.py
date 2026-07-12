import json
import os
import asyncpg
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            data = json.loads(body)
            
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("status", status))  # YANGI
            
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

# ==================== YANGI: STATUS BUYRUG'I ====================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        async with asyncpg.create_pool(DATABASE_URL) as pool:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT score, reading_band, time_spent, submitted_at FROM test_results WHERE user_id = $1 ORDER BY submitted_at DESC LIMIT 5",
                    user_id
                )
        
        if not rows:
            await update.message.reply_text("📭 Siz hali hech qanday test topshirmagansiz.")
            return
        
        text = "📊 *So‘nggi 5 ta natijangiz:*\n\n"
        for i, row in enumerate(rows, 1):
            date_str = row['submitted_at'].strftime('%d.%m.%Y %H:%M')
            text += f"{i}. 🎯 Ball: {row['score']}/40 | Band: {row['reading_band']}\n"
            text += f"   ⏱ Vaqt: {row['time_spent']} daqiqa | 📅 {date_str}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {e}")
