import json
import os
import psycopg2
import urllib.request
import traceback
from http.server import BaseHTTPRequestHandler
from datetime import datetime

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
            time_spent = data.get('time_spent', 0)
            
            band = self.calc_band(score)
            result_id = self.save_result(user_id, name, score, band, answers, time_spent)
            
            if BOT_TOKEN and CHANNEL_ID:
                self.send_to_channel(result_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success", "result_id": result_id,
                "score": score, "band": band,
                "message": f"Natijangiz saqlandi! Ball: {score}/40, Band: {band}"
            }).encode())
        except Exception as e:
            err = traceback.format_exc()
            print("SUBMIT XATOLIK:", err)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
    
    def calc_band(self, score):
        if score >= 39: return 9.0
        elif score >= 37: return 8.5
        elif score >= 35: return 8.0
        elif score >= 33: return 7.5
        elif score >= 30: return 7.0
        elif score >= 27: return 6.5
        elif score >= 23: return 6.0
        elif score >= 19: return 5.5
        elif score >= 15: return 5.0
        else: return 4.0
    
    def save_result(self, user_id, full_name, score, band, answers, time_spent):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO test_results (user_id, full_name, score, reading_band, answers, time_spent)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (user_id, full_name, score, band, json.dumps(answers), time_spent))
            result_id = cur.fetchone()[0]
            conn.commit()
            return result_id
        finally:
            cur.close()
            conn.close()
    
    def send_to_channel(self, result_id):
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT full_name, score, reading_band, time_spent, submitted_at FROM test_results WHERE id = %s",
                    (result_id,)
                )
                row = cur.fetchone()
                if not row:
                    print(f"Result ID {result_id} topilmadi")
                    return
                name, score, band, time_spent, submitted_at = row
                caption = (
                    f"🎯 **Yangi IELTS natijasi!**\n"
                    f"👤 **Ism:** {name}\n"
                    f"📝 **Ball:** {score}/40\n"
                    f"📊 **Band:** {band}\n"
                    f"⏱ **Vaqt:** {time_spent} daqiqa\n"
                    f"📅 **Sana:** {submitted_at.strftime('%d.%m.%Y %H:%M')}"
                )
                # Grafik URL (quickchart.io)
                wrong = 40 - score
                chart_url = f"https://quickchart.io/chart?c={{type:'doughnut',data:{{labels:['To‘g‘ri ({score})', 'Xato ({wrong})'], datasets:[{{data:[{score},{wrong}], backgroundColor:['#48bb78','#fc8181']}}]}}}}"
                caption += f"\n\n📊 Grafik: {chart_url}"
            finally:
                cur.close()
                conn.close()
            
            # Xabarni matn sifatida yuborish (grafik URL bilan)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = json.dumps({
                "chat_id": CHANNEL_ID,
                "text": caption,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False  # Grafik preview chiqsin
            }).encode()
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req)
            print(f"Kanalga xabar yuborildi: {response.read().decode()}")
        except Exception as e:
            print(f"Kanalga yuborishda xatolik: {e}")
            traceback.print_exc()
