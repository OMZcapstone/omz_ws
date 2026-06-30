import re
import threading
import time
from pathlib import Path

import cv2
import easyocr
import requests


USE_WEBCAM = True
VIDEO_PATH = str(Path(__file__).parent / "test_video.mp4")
SERVER_URL = "http://127.0.0.1:8000/verify"

MIN_CONFIDENCE = 0.5
COOLDOWN_SECONDS = 5

DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480

plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')


def verify_plate(plate_text):
    try:
        payload = {"ocr_text": plate_text}
        res = requests.post(SERVER_URL, json=payload)

        if res.status_code == 200:
            data = res.json()
            best_plate = data.get("best_plate")
            score = data.get("score")

            if best_plate:
                print(
                    f"OCR: {plate_text} -> DB 번호판: {best_plate} "
                    f"(유사도 {score:.2f})"
                )
            else:
                print(f"OCR: {plate_text} -> DB에서 일치하는 번호판 없음")
        else:
            print("서버 오류:", res.text)

    except Exception as e:
        print("서버 연결 실패:", e)


def main():
    print("OCR 모델 로딩 중...")
    reader = easyocr.Reader(['ko', 'en'], gpu=False)

    print("영상 소스 로딩")
    if USE_WEBCAM:
        cap = cv2.VideoCapture(0)
        frame_skip = 20
    else:
        cap = cv2.VideoCapture(VIDEO_PATH)
        frame_skip = 10

    if not cap.isOpened():
        print("카메라/영상 열기 실패")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    delay = int(1000 / fps)

    frame_count = 0
    last_sent_time = {}
    seen_plates = set()

    print("번호판 인식 시작")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("영상 종료")
            break

        frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        frame_count += 1

        display_frame = frame.copy()
        ocr_frame = cv2.resize(frame, None, fx=0.7, fy=0.7) if USE_WEBCAM else frame

        if frame_count % frame_skip != 0:
            cv2.imshow("Parking System", display_frame)
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                break
            continue

        results = reader.readtext(ocr_frame)

        for bbox, text, prob in results:
            clean_text = text.replace(" ", "")

            if prob < MIN_CONFIDENCE:
                continue

            match = plate_pattern.search(clean_text)
            if not match:
                continue

            matched_plate = match.group()
            tl, _, br, _ = bbox
            top_left = (int(tl[0]), int(tl[1]))
            bottom_right = (int(br[0]), int(br[1]))

            cv2.rectangle(display_frame, top_left, bottom_right, (0, 255, 0), 2)
            cv2.putText(
                display_frame,
                f"OCR: {matched_plate}",
                (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            now = time.time()
            last_sent_at = last_sent_time.get(matched_plate, 0)
            if matched_plate in seen_plates and now - last_sent_at < COOLDOWN_SECONDS:
                continue

            print(f"번호판 인식: {matched_plate} (정확도 {prob:.2f})")
            threading.Thread(
                target=verify_plate,
                args=(matched_plate,),
                daemon=True,
            ).start()

            seen_plates.add(matched_plate)
            last_sent_time[matched_plate] = now

        cv2.imshow("Parking System", display_frame)
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
