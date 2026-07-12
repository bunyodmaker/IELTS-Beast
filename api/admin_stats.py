import json
import os
import asyncpg
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Admin paroli (oddiy, lekin yetarli)
            # URL dan ?password=... parametrini o'qiymiz
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            password = params.get('password', [''])[0]
            
            # Parolni tekshirish (o'zingiz xohlagan parolni qo'ying)
            if password != 'admin123':
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Noto'g'ri parol"}).encode())
                return
            
            # Ma'lumotlarni olish
            data = self.get_stats()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def get_stats(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self._async_get_stats())
        loop.close()
        return result
    
    async def _async_get_stats(self):
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # Umumiy statistika
            total = await conn.fetchval("SELECT COUNT(*) FROM test_results")
            avg_score = await conn.fetchval("SELECT AVG(score) FROM test_results")
            max_score = await conn.fetchval("SELECT MAX(score) FROM test_results")
            avg_band = await conn.fetchval("SELECT AVG(reading_band) FROM test_results")
            
            # So'nggi 20 ta natija
            recent = await conn.fetch(
                "SELECT id, full_name, score, reading_band, time_spent, submitted_at FROM test_results ORDER BY id DESC LIMIT 20"
            )
            recent_list = []
            for row in recent:
                recent_list.append({
                    "id": row['id'],
                    "name": row['full_name'],
                    "score": row['score'],
                    "band": float(row['reading_band']),
                    "time": row['time_spent'],
                    "date": row['submitted_at'].isoformat()
                })
            
            # Haftalik statistika (oxirgi 7 kun)
            week_ago = datetime.now() - timedelta(days=7)
            week_count = await conn.fetchval(
                "SELECT COUNT(*) FROM test_results WHERE submitted_at > $1",
                week_ago
            )
            week_avg = await conn.fetchval(
                "SELECT AVG(score) FROM test_results WHERE submitted_at > $1",
                week_ago
            )
            
            return {
                "total": total,
                "avg_score": round(avg_score or 0, 1),
                "max_score": max_score or 0,
                "avg_band": round(avg_band or 0, 1),
                "week_count": week_count or 0,
                "week_avg": round(week_avg or 0, 1),
                "recent": recent_list
            }
        finally:
            await conn.close()
