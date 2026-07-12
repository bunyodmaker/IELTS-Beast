import json
import os
import asyncpg
from http.server import BaseHTTPRequestHandler

DATABASE_URL = os.getenv("DATABASE_URL")

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
            self.save_result(user_id, name, score, band, answers, time)
            
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
        return 9.0 if s>=39 else 8.5 if s>=37 else 8.0 if s>=35 else 7.5 if s>=33 else 7.0 if s>=30 else 6.5 if s>=27 else 6.0 if s>=23 else 5.5 if s>=19 else 5.0 if s>=15 else 4.0
    
    def save_result(self, uid, name, score, band, answers, time):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_save(uid, name, score, band, answers, time))
        loop.close()
    
    async def _async_save(self, uid, name, score, band, answers, time):
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO test_results (user_id, full_name, score, reading_band, answers, time_spent) VALUES ($1,$2,$3,$4,$5,$6)",
                uid, name, score, band, json.dumps(answers), time
            )
        finally:
            await conn.close()
