import json
import os
import urllib.request
import asyncpg
import asyncio
import traceback
from http.server import BaseHTTPRequestHandler
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not set")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            data = json.loads(body)
            
            message = data.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            
            if chat_id:
                if text == '/start':
                    self.send_menu(chat_id)
                elif text == '/help' or text == '❓ Yordam':
                    self.send_message(chat_id, "/start - boshlash\n/help - yordam\n/status - natijalarim")
                elif text == '/status' or text == '📊 Natijalarim':
                    result = asyncio.run(self.get_user_results(chat_id))
                    self.send_message(chat_id, result)
                elif text == '📝 Test boshlash':
                    self.send_message(chat_id, "📝 Testni boshlash uchun havola:\nhttps://ielts-beast.vercel.app")
                else:
                    self.send_message(chat_id, "Tushunarsiz buyruq. Iltimos, quyidagi tugmalardan foydalaning:", menu=True)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            err = traceback.format_exc()
            print("BOT XATOLIK:", err)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Webhook is active")

    def send_menu(self, chat_id):
        """Tugmali menyu yuborish - to'g'ri format"""
        try:
            keyboard = {
                "keyboard": [
                    ["📝 Test boshlash", "📊 Natijalarim"],
                    ["❓ Yordam"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            payload = json.dumps({
                "chat_id": chat_id,
                "text": "Assalomu alaykum! Quyidagi tugmalardan birini tanlang:",
                "reply_markup": keyboard
            }).encode()
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req)
            print(f"Menyu yuborildi: {response.read().decode()}")
        except Exception as e:
            print(f"Menyu yuborishda xatolik: {e}")
            traceback.print_exc()

    def send_message(self, chat_id, text, menu=False):
        try:
            payload = {"chat_id": chat_id, "text": text}
            if menu:
                keyboard = {
                    "keyboard": [
                        ["📝 Test boshlash", "📊 Natijalarim"],
                        ["❓ Yordam"]
                    ],
                    "resize_keyboard": True
                }
                payload["reply_markup"] = keyboard
            payload = json.dumps(payload).encode()
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req)
            print(f"Xabar yuborildi: {response.read().decode()}")
        except Exception as e:
            print(f"Xabar yuborishda xatolik: {e}")
            traceback.print_exc()

    async def get_user_results(self, user_id):
        try:
            if not DATABASE_URL:
                return "❌ Ma'lumotlar bazasi ulanishi sozlanmagan."
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                rows = await conn.fetch(
                    "SELECT score, reading_band, time_spent, submitted_at FROM test_results WHERE user_id = $1 ORDER BY submitted_at DESC LIMIT 5",
                    user_id
                )
            finally:
                await conn.close()
            if not rows:
                return "📭 Siz hali hech qanday test topshirmagansiz."
            text = "📊 So'nggi 5 ta natijangiz:\n\n"
            for i, row in enumerate(rows, 1):
                date_str = row['submitted_at'].strftime('%d.%m.%Y %H:%M')
                text += f"{i}. 🎯 Ball: {row['score']}/40 | Band: {row['reading_band']}\n"
                text += f"   ⏱ Vaqt: {row['time_spent']} daqiqa | 📅 {date_str}\n\n"
            return text
        except Exception as e:
            return f"❌ Xatolik yuz berdi: {e}"
