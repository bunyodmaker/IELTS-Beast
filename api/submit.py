import json
import os
import asyncpg
from http.server import BaseHTTPRequestHandler
import asyncio
import aiohttp

DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            
            user_id = data.get('user_id')
            name = data.get('full_name', 'Anonim')
            score = data.get('score', 0)
            answers = data.get('answers', [])
            time = data.get('time_spent', 0)
            
            band = self.calc_band(score)
            result_id = self.save_result(user_id, name, score, band, answers, time)
            
            # Kanalga xabar yuborish (agar token va kanal ID bo'lsa)
            if BOT_TOKEN and CHANNEL_ID:
                asyncio.run(self.send_to_channel(result_id))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status":"ok","score":score,"band":band}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status":"error","msg":str(e)}).encode())
    
    def calc_band(self, s):
        if s >= 39: return 9.0
        elif s >= 37: return 8.5
        elif s >= 35: return 8.0
        elif s >= 33: return 7.5
        elif s >= 30: return 7.0
        elif s >= 27: return 6.5
        elif s >= 23: return 6.0
        elif s >= 19: return 5.5
        elif s >= 15: return 5.0
        else: return 4.0
    
    def save_result(self, uid, name, score, band, answers, time):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_id = loop.run_until_complete(self._async_save(uid, name, score, band, answers, time))
        loop.close()
        return result_id
    
    async def _async_save(self, uid, name, score, band, answers, time):
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                "INSERT INTO test_results (user_id, full_name, score, reading_band, answers, time_spent) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id",
                uid, name, score, band, json.dumps(answers), time
            )
            return row['id']
        finally:
            await conn.close()
    
    async def send_to_channel(self, result_id):
        """Kanalga natija haqida xabar yuborish"""
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                row = await conn.fetchrow("SELECT * FROM test_results WHERE id = $1", result_id)
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
            finally:
                await conn.close()
            
            # Telegram API ga so'rov
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHANNEL_ID,
                "text": text,
                "parse_mode": "Markdown"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        print(f"Xatolik: {await resp.text()}")
        except Exception as e:
            print(f"Kanalga yuborishda xatolik: {e}")
