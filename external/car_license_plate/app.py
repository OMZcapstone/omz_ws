# app.py
import json
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from db import init_db, get_conn
from matcher import find_best_plate
from fastapi import Body
from contextlib import asynccontextmanager

# 1. Lifespan 함수 정의
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [시작 시 실행될 코드]
    init_db()
    yield
    # [종료 시 실행될 코드 (필요하다면 여기에 작성)]
    # 예: conn.close()

# 2. FastAPI 앱 생성 시 lifespan 주입
app = FastAPI(title="Plate Verify Local Server", lifespan=lifespan)

class EntryRequest(BaseModel):
    plate: str
    entry_time: str | None = None  # 없으면 서버시간
    color: str | None = None
    vehicle_type: str | None = None
    plate_crop_path: str | None = None

class VerifyRequest(BaseModel):
    ocr_text: str
    time: str | None = None  # 없으면 서버시간
    color: str | None = None
    vehicle_type: str | None = None

@app.post("/entry")
def register_entry(req: EntryRequest):
    entry_time = req.entry_time or datetime.now().isoformat(timespec="seconds")

    conn = get_conn()
    cur = conn.cursor()

    # 같은 번호판이 이미 있으면 갱신(upsert)
    cur.execute("""
    INSERT INTO parked_vehicle(plate, entry_time, status, color, vehicle_type, plate_crop_path)
    VALUES(?, ?, 'parked', ?, ?, ?)
    ON CONFLICT(plate) DO UPDATE SET
        entry_time=excluded.entry_time,
        status='parked',
        color=excluded.color,
        vehicle_type=excluded.vehicle_type,
        plate_crop_path=excluded.plate_crop_path;
    """, (req.plate, entry_time, req.color, req.vehicle_type, req.plate_crop_path))

    conn.commit()
    conn.close()

    return {"ok": True, "plate": req.plate, "entry_time": entry_time}

@app.post("/exit/{plate}")
def mark_exit(plate: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE parked_vehicle SET status='exited' WHERE plate=?", (plate,))
    conn.commit()
    conn.close()
    return {"ok": True, "plate": plate, "status": "exited"}

@app.post("/verify")
def verify_plate(req: VerifyRequest):
    t = req.time or datetime.now().isoformat(timespec="seconds")

    conn = get_conn()
    cur = conn.cursor()

    # 현재 주차중인 차량만 후보로
    rows = cur.execute("SELECT plate FROM parked_vehicle WHERE status='parked'").fetchall()
    parked_plates = [r["plate"] for r in rows]

    best_plate, best_score, top_candidates = find_best_plate(req.ocr_text, parked_plates, top_k=5)

    # 임계값(초기 추천): 0.75 ~ 0.85 사이에서 현장 데이터 보고 조정
    threshold = 0.80
    is_confident = (best_score >= threshold)

    # 로그 저장
    cur.execute("""
    INSERT INTO plate_read_log(time, ocr_text, best_plate, score, top_candidates)
    VALUES(?, ?, ?, ?, ?)
    """, (t, req.ocr_text, best_plate, best_score, json.dumps(top_candidates, ensure_ascii=False)))

    conn.commit()
    conn.close()

    return {
        "time": t,
        "ocr_text": req.ocr_text,
        "best_plate": best_plate,
        "score": best_score,
        "confident": is_confident,
        "threshold": threshold,
        "top_candidates": top_candidates
    }


@app.post("/echo")
def echo(payload: dict = Body(...)):
    return payload

@app.get("/")
def read_root():
    return {"message": "주차 관제 서버가 정상적으로 실행 중입니다!"}