import cv2
import easyocr
import requests
import re
import threading
import time
from ultralytics import YOLO
from pathlib import Path

# === 설정 ===
USE_WEBCAM = True
VIDEO_PATH = str(Path(__file__).parent / "test_video.mp4")
SERVER_URL = "http://127.0.0.1:8000/verify"

DISPLAY_WIDTH  = 640
DISPLAY_HEIGHT = 480
MIN_CONFIDENCE = 0.4
FRAME_SKIP     = 3
COOLDOWN       = 8    # 같은 번호판 재전송 방지 (초)
SHOW_DURATION  = 3.0  # ILLEGAL PARKING 표시 유지 시간 (초)

plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')
correction_map = {'O':'0','Q':'0','D':'0','I':'1','B':'8','Z':'2','S':'5'}

# === 모델 로드 ===
print("YOLO 번호판 모델 로딩...")
model = YOLO(str(Path(__file__).parent / "best.pt"))
print("OCR 모델 로딩...")
reader = easyocr.Reader(['ko'], gpu=False)

# === 감지 상태 (스레드 공유) ===
# { plate_text: { "is_illegal": bool, "expire": float, "box": (x1,y1,x2,y2) } }
detections = {}
det_lock = threading.Lock()

def verify_and_update(plate_text, box):
    try:
        res = requests.post(SERVER_URL, json={"ocr_text": plate_text}, timeout=3)
        if res.status_code != 200:
            return
        data = res.json()
        confident  = data.get("confident", False)
        best_plate = data.get("best_plate")
        score      = data.get("score", 0)

        is_illegal = (not confident) or (not best_plate)

        with det_lock:
            detections[plate_text] = {
                "is_illegal": is_illegal,
                "expire": time.time() + SHOW_DURATION,
                "box": box,
            }

        if is_illegal:
            print(f"🚨 불법 주차 차량 번호: {plate_text}")
        else:
            print(f"✅ 등록 차량: {plate_text} → {best_plate} (유사도 {score:.2f})")

    except Exception as e:
        print("서버 오류:", e)

# === 카메라 / 영상 ===
cap = cv2.VideoCapture(0 if USE_WEBCAM else VIDEO_PATH)
if not cap.isOpened():
    print("❌ 카메라/영상 열기 실패")
    exit()

fps   = cap.get(cv2.CAP_PROP_FPS) or 30
delay = max(1, int(1000 / fps))
frame_count = 0
last_sent   = {}  # plate -> 마지막 전송 시각

print("🚀 불법 주차 탐지 시작 (종료: q)")

while True:
    ret, frame = cap.read()
    if not ret:
        print("영상 종료")
        break

    frame_count += 1
    frame   = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    display = frame.copy()
    now     = time.time()

    # 만료된 감지 정보 제거
    with det_lock:
        expired = [k for k, v in detections.items() if v["expire"] <= now]
        for k in expired:
            del detections[k]
        active = dict(detections)

    # YOLO 번호판 영역 탐지
    yolo_res = model(frame, conf=0.5, verbose=False)

    for r in yolo_res:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # 번호판 박스 (빨간색)
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)

            # n프레임마다 OCR 실행
            if frame_count % FRAME_SKIP != 0:
                continue

            my = max(1, int((y2 - y1) * 0.05))
            mx = max(1, int((x2 - x1) * 0.05))
            plate_crop = frame[max(0, y1+my):min(DISPLAY_HEIGHT, y2-my),
                               max(0, x1+mx):min(DISPLAY_WIDTH,  x2-mx)]
            if plate_crop.size == 0:
                continue

            plate_crop = cv2.resize(plate_crop, None, fx=2, fy=2,
                                    interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)

            for (_, text, prob) in reader.readtext(gray):
                clean = text.replace(" ", "")
                for k, v in correction_map.items():
                    clean = clean.replace(k, v)
                if prob < MIN_CONFIDENCE:
                    continue
                m = plate_pattern.search(clean)
                if not m:
                    continue

                plate = m.group()

                # 번호판 텍스트 표시
                cv2.putText(display, plate,
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

                # 쿨다운 후 서버 전송
                if plate not in last_sent or (now - last_sent[plate]) > COOLDOWN:
                    last_sent[plate] = now
                    threading.Thread(
                        target=verify_and_update,
                        args=(plate, (x1, y1, x2, y2)),
                        daemon=True
                    ).start()

    # 불법 주차 오버레이
    for plate, state in active.items():
        if state["is_illegal"]:
            bx1, by1, bx2, by2 = state["box"]

            # 차량 주변 큰 박스
            pad = 40
            cx1 = max(0, bx1 - pad)
            cy1 = max(0, by1 - pad * 3)
            cx2 = min(DISPLAY_WIDTH,  bx2 + pad)
            cy2 = min(DISPLAY_HEIGHT, by2 + pad)
            cv2.rectangle(display, (cx1, cy1), (cx2, cy2), (0, 0, 255), 3)

            # ILLEGAL PARKING 텍스트
            cv2.putText(display, "ILLEGAL PARKING",
                        (cx1, cy2 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

    cv2.imshow("Parking AI", display)
    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
