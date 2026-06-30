# db.py
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "parking.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # 현재 주차중 차량 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS parked_vehicle (
        plate TEXT PRIMARY KEY,
        entry_time TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('parked','exited')),
        color TEXT,
        vehicle_type TEXT,
        plate_crop_path TEXT
    );
    """)

    # 로봇 판독 로그(디버깅용)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS plate_read_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT NOT NULL,
        ocr_text TEXT NOT NULL,
        best_plate TEXT,
        score REAL,
        top_candidates TEXT
    );
    """)

    conn.commit()
    conn.close()
