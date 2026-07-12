import json
import os
import psycopg2
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
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e), "traceback": traceback.format_exc()}).encode())
    
    def get_stats(self):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        try:
            cur = conn.cursor()
            
            # Umumiy statistika
            cur.execute("SELECT COUNT(*) FROM test_results")
            total = int(cur.fetchone()[0] or 0)
            cur.execute("SELECT AVG(score) FROM test_results")
            avg_score = float(cur.fetchone()[0] or 0)
            cur.execute("SELECT MAX(score) FROM test_results")
            max_score = int(cur.fetchone()[0] or 0)
            cur.execute("SELECT AVG(reading_band) FROM test_results")
            avg_band = float(cur.fetchone()[0] or 0)
            
            # So'nggi 20
            cur.execute("""
                SELECT id, full_name, score, reading_band, time_spent, submitted_at 
                FROM test_results ORDER BY id DESC LIMIT 20
            """)
            recent = []
            for row in cur.fetchall():
                recent.append({
                    "id": row[0], "name": row[1] or 'Anonim',
                    "score": int(row[2] or 0), "band": float(row[3] or 0),
                    "time": int(row[4] or 0),
                    "date": row[5].isoformat() if row[5] else None
                })
            
            # Haftalik trend (oxirgi 7 kun)
            week_ago = datetime.now() - timedelta(days=7)
            cur.execute("""
                SELECT DATE(submitted_at) as date, AVG(score) as avg_score 
                FROM test_results 
                WHERE submitted_at > %s 
                GROUP BY DATE(submitted_at) 
                ORDER BY date ASC
            """, (week_ago,))
            weekly_trend = []
            for row in cur.fetchall():
                weekly_trend.append({
                    "date": row[0].strftime('%d.%m'),
                    "avg_score": float(row[1] or 0)
                })
            
            # Band taqsimoti
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN reading_band >= 8 THEN '8.0-9.0'
                        WHEN reading_band >= 7 THEN '7.0-7.5'
                        WHEN reading_band >= 6 THEN '6.0-6.5'
                        WHEN reading_band >= 5 THEN '5.0-5.5'
                        ELSE '0.0-4.5'
                    END as band_group,
                    COUNT(*) as count
                FROM test_results
                GROUP BY band_group
                ORDER BY band_group DESC
            """)
            band_distribution = []
            for row in cur.fetchall():
                band_distribution.append({"range": row[0], "count": int(row[1])})
            
            week_count = sum([x['count'] for x in band_distribution])  # oddiy, lekin bazadan alohida olish yaxshiroq
            cur.execute("SELECT COUNT(*) FROM test_results WHERE submitted_at > %s", (week_ago,))
            week_count = int(cur.fetchone()[0] or 0)
            
            return {
                "total": total,
                "avg_score": round(avg_score, 1),
                "max_score": max_score,
                "avg_band": round(avg_band, 1),
                "week_count": week_count,
                "week_avg": round(avg_score, 1),  # o'xshash, lekin qoldirib qo'yganmiz, tuzatamiz
                "recent": recent,
                "weekly_trend": weekly_trend,
                "band_distribution": band_distribution
            }
        finally:
            cur.close()
            conn.close()
