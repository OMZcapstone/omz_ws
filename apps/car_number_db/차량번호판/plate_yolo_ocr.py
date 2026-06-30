import cv2
import easyocr
import requests
import re
import threading
from pathlib import Path
from ultralytics import YOLO

# 설정
USE_WEBCAM = False
VIDEO_PATH = str(Path(__file__).parent / "test_video.mp4")
SERVER_URL = "http://127.0.0.1:8000/verify"

DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480
MIN_CONFIDENCE = 0.4 # OCR 신뢰도 컷 / 여러 번 읽을 것이므로 컷을 살짝 낮춤 0.5 → 0.4
REQUIRED_HITS = 3  # 같은 번호판을 3번 연속으로 읽어야 확정!
FRAME_SKIP = 3     # 3프레임당 1번만 OCR 검사 (버퍼링 방지)

plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')

# 🚀 1. 모델 로드 (새로 학습한 번호판 전용 모델 적용!)
print("YOLO 번호판 전용 모델 로딩...")
model = YOLO(str(Path(__file__).parent / "best.pt")) # 다운받은 best.pt가 같은 폴더에 있어야 합니다.

print("OCR 모델 로딩...")
reader = easyocr.Reader(['ko'], gpu=False)

# 서버 요청
def verify_plate(plate):
    try:
        res = requests.post(SERVER_URL, json={"ocr_text": plate})
        if res.status_code == 200:
            data = res.json()
            best_plate = data.get("best_plate")
            score = data.get("score")
            print(f"🔎 OCR:{plate} → DB:{best_plate} ({score:.2f})")
    except Exception as e:
        print("서버 오류:", e)

# 카메라 시작
if USE_WEBCAM:
    cap = cv2.VideoCapture(0)
else:
    cap = cv2.VideoCapture(VIDEO_PATH)

seen_plates = set()
plate_buffer = {}          # 현재 화면에서 읽고 있는 번호판 임시 카운터 🌟
frame_count = 0            # 버퍼링 방지용 프레임 카운터 🌟
print("번호판 탐지 시작")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    display = frame.copy()

    # 🚀 2. YOLO 번호판 탐지 (이제 차량이 아니라 번호판 영역만 쏙쏙 찾아냅니다)
    results = model(frame, conf=0.5, verbose=False)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)

            # 🌟 버퍼링(렉) 방지를 위해 OCR은 n프레임에 한 번만 실행!
            if frame_count % FRAME_SKIP != 0:
                continue

            # 1. 번호판 가장자리(테두리) 노이즈를 피하기 위해 상하좌우 마진을 살짝 깎고 자릅니다.
            margin_y = int((y2 - y1) * 0.05) # 5% 깎기
            margin_x = int((x2 - x1) * 0.05)

            # 박스가 너무 작아서 마진을 빼면 에러나는 경우 방지
            if (y2-margin_y) - (y1+margin_y) <= 0 or (x2-margin_x) - (x1+margin_x) <= 0:
                continue
            
            plate_area = frame[y1+margin_y : y2-margin_y, x1+margin_x : x2-margin_x]

            if plate_area.size == 0:
                continue

            # 2. 전처리: 이진화(까맣고 하얗게)가 오히려 독이 될 수 있어, '회색조(Grayscale)'만 적용해 봅니다.
            # 크기 확대 (2배)
            plate_area = cv2.resize(plate_area, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            # 흑백 변환 (이진화 없이 회색조까지만)
            gray = cv2.cvtColor(plate_area, cv2.COLOR_BGR2GRAY)

            # [디버깅 용도] OCR이 읽을 이미지를 확인
            cv2.imshow("OCR Target", gray)

            # 3. OCR 실행 (전처리된 gray 이미지를 넘김)
            results_ocr = reader.readtext(gray)

            for (bbox, text, prob) in results_ocr:
                print(f"🧐 [Raw OCR] 인식된 텍스트: '{text}', 신뢰도: {prob:.2f}")
                clean = text.replace(" ", "")
                
                # 🚀 4. 자주 발생하는 OCR 오인식 자동 교정
                correction_map = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'B': '8', 'Z': '2', 'S': '5'}
                for k, v in correction_map.items():
                    clean = clean.replace(k, v)

                if prob < MIN_CONFIDENCE:
                    continue

                match = plate_pattern.search(clean)

                if match:
                    plate = match.group()
                    # 이미 인식한 번호판이면 무시
                    if plate in seen_plates:
                        continue

                    # 기록
                    seen_plates.add(plate)
                    print(f"✅ 번호판 인식 성공: {plate} (신뢰도: {prob:.2f})")

                    threading.Thread(
                        target=verify_plate,
                        args=(plate,),
                        daemon=True
                    ).start()

                    cv2.putText(display, plate, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    cv2.imshow("Plate Detection", display)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
