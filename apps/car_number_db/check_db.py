import sqlite3
import os
from pathlib import Path

db_path = Path(__file__).parent / "parking.db"
print("DB 절대경로:", os.path.abspath(db_path))

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== parked_vehicle ===")
for row in cur.execute("SELECT plate, entry_time, status FROM parked_vehicle"):
    print(row)

conn.close()
