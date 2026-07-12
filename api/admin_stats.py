import json
import os
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            password = params.get('password', [''])[0]
            
            if password != 'admin123':
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Noto'g'ri parol"}).encode())
                return
            
            data = self.get_stats()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            # Xatolikni batafsil chiqaramiz
            error_detail = {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_detail).encode())
    
    def get_stats(self):
        try:
            import psycopg2
        except ImportError:
            raise Exception("psycopg2 o'rnatilmagan. Iltimos, requirements.txt ni tekshiring.")
        
        if not DATABASE_URL:
            raise Exception("DATABASE_URL environment variable o'rnatilmagan")
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM test_results")
            total = cur.fetchone()[0] or 0
            
            cur.execute("SELECT AVG(score) FROM test_results")
            avg_score = cur.fetchone()[0] or 0
            
            cur.execute("SELECT MAX(score) FROM test_results")
            max_score = cur.fetchone()[0] or 0
            
            cur.execute("SELECT AVG(reading_band) FROM test_results")
            avg_band = cur.fetchone()[0] or 0
            
            cur.execute("""
                SELECT id, full_name, score, reading_band, time_spent, submitted_at 
                FROM test_results 
                ORDER BY id DESC 
                LIMIT 20
            """)
            recent = []
            for row in cur.fetchall():
                recent.append({
                    "id": row[0],
                    "name": row[1] or 'Anonim',
                    "score": row[2] or 0,
                    "band": float(row[3]) if row[3] is not None else 0,
                    "time": row[4] or 0,
                    "date": row[5].isoformat() if row[5] else None
                })
            
            week_ago = datetime.now() - timedelta(days=7)
            cur.execute("SELECT COUNT(*) FROM test_results WHERE submitted_at > %s", (week_ago,))
            week_count = cur.fetchone()[0] or 0
            
            cur.execute("SELECT AVG(score) FROM test_results WHERE submitted_at > %s", (week_ago,))
            week_avg = cur.fetchone()[0] or 0
            
            return {
                "total": total,
                "avg_score": round(avg_score, 1),
                "max_score": max_score,
                "avg_band": round(avg_band, 1),
                "week_count": week_count,
                "week_avg": round(week_avg, 1),
                "recent": recent
            }
        finally:
            cur.close()
            conn.close()
