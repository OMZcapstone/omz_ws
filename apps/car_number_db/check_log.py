import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path(__file__).parent / "parking.db")
cur = conn.cursor()

print("=== 최근 10개 verify 로그 ===")

for row in cur.execute("""
  SELECT time, ocr_text, best_plate, score, top_candidates
  FROM plate_read_log
  ORDER BY id DESC
  LIMIT 10
"""):
    print(row)

conn.close()
