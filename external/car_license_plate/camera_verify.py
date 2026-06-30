import cv2
import easyocr
import requests
import re
import time
import threading

# 설정
USE_WEBCAM = True
VIDEO_PATH = "test_video.mp4"   # 테스트 영상
SERVER_URL = "http://127.0.0.1:8000/verify"

MIN_CONFIDENCE = 0.8 # 체크할 신뢰도 
COOLDOWN_SECONDS = 5

# 화면 표시 크기 (웹캠/영상 동일하게)
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480

# 한국 번호판 패턴
plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')

# 서버에 OCR 결과 보내기
def verify_plate(plate_text):

    try:

        payload = {"ocr_text": plate_text} # 서버에 보낼 JSON 데이터
        res = requests.post(SERVER_URL, json=payload)

        if res.status_code == 200: # 서버 응답이 정상이면 

            data = res.json()

            best_plate = data.get("best_plate")
            score = data.get("score")

            if best_plate:
                print(
                    f"🔎 OCR: {plate_text} → DB 번호판: {best_plate} (유사도 {score:.2f})"
                )

            else: # import cv2
import easyocr
import requests
import re
import time
import threading

# 설정
USE_WEBCAM = True
VIDEO_PATH = "test_video.mp4"   # 테스트 영상
SERVER_URL = "http://127.0.0.1:8000/verify"

MIN_CONFIDENCE = 0.5
COOLDOWN_SECONDS = 5
# FRAME_SKIP = 10

# 화면 표시 크기 (웹캠/영상 동일하게)
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480

# 한국 번호판 패턴
plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')

# 서버에 OCR 결과 보내기
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
                    f"🔎 OCR: {plate_text} → DB 번호판: {best_plate} (유사도 {score:.2f})"
                )

            else:
                print(
                    f"❌ OCR: {plate_text} → DB에서 일치하는 번호판 없음"
                )

        else:
            print("❌ 서버 오류:", res.text)

    except Exception as e:

        print("⚠️ 서버 연결 실패:", e)

# 메인 프로그램
def main():

    print("📷 OCR 모델 로딩 중...")

    reader = easyocr.Reader(['ko', 'en'], gpu=False)

    print("📷 영상 소스 로딩")

    if USE_WEBCAM:
        cap = cv2.VideoCapture(0)
        FRAME_SKIP = 20
    else:
        cap = cv2.VideoCapture(VIDEO_PATH)
        FRAME_SKIP = 10

    if not cap.isOpened():
        print("❌ 카메라/영상 열기 실패")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps == 0:
        fps = 30

    delay = int(1000 / fps)

    frame_count = 0
    last_sent_time = {}
    seen_plates = set()

    print("🚀 번호판 인식 시작")

    while True:

        ret, frame = cap.read()

        if not ret:
            print("영상 종료")
            break

        # 웹캠/영상 동일한 크기로 맞춤
        frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        frame_count += 1

        # 해상도 축소 (속도 개선)
        display_frame = frame.copy()
        if USE_WEBCAM:
            ocr_frame = cv2.resize(frame, None, fx=0.7, fy=0.7)
        else:
            ocr_frame = frame 

        # 프레임 스킵
        if frame_count % FRAME_SKIP != 0:

            cv2.imshow("Parking System", display_frame)

            if cv2.waitKey(delay) & 0xFF == ord('q'):
                break

            continue

        # OCR 실행
        results = reader.readtext(ocr_frame)

        for (bbox, text, prob) in results:

            clean_text = text.replace(" ", "")

            if prob < MIN_CONFIDENCE:
                continue

            match = plate_pattern.search(clean_text)

            if match:

                matched_plate = match.group()
                scale = 1 # / 0.7
                (tl, tr, br, bl) = bbox
                top_left = (int(tl[0]*scale), int(tl[1]*scale))
                bottom_right = (int(br[0]*scale), int(br[1]*scale))

                cv2.rectangle(
                    display_frame,
                    top_left,
                    bottom_right,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    f"OCR: {matched_plate}",
                    (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )
                                
                
                now = time.time()

                # 이미 처리한 번호판이면 무시
                if matched_plate in seen_plates:
                    continue

                print(
                    f"✨ 번호판 인식: {matched_plate} (정확도 {prob:.2f})"
                )

                threading.Thread(
                    target=verify_plate,
                    args=(matched_plate,),
                    daemon=True
                ).start()

                # 기록
                seen_plates.add(matched_plate)
                last_sent_time[matched_plate] = now

        cv2.imshow("Parking System", display_frame)

        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

                print(
                    f"❌ OCR: {plate_text} → DB에서 일치하는 번호판 없음"
                )

        else:
            print("❌ 서버 오류:", res.text)

    except Exception as e:

        print("⚠️ 서버 연결 실패:", e)

# 메인 프로그램
def main():

    print("📷 OCR 모델 로딩 중...")

    reader = easyocr.Reader(['ko', 'en'], gpu=False)

    print("📷 영상 소스 로딩")

    if USE_WEBCAM:
        cap = cv2.VideoCapture(0)
        FRAME_SKIP = 20
    else:
        cap = cv2.VideoCapture(VIDEO_PATH)
        FRAME_SKIP = 10

    if not cap.isOpened():
        print("❌ 카메라/영상 열기 실패")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps == 0:
        fps = 30

    delay = int(1000 / fps)

    frame_count = 0
    last_sent_time = {}
    seen_plates = set()

    print("🚀 번호판 인식 시작")

    while True:

        ret, frame = cap.read()

        if not ret:
            print("영상 종료")
            break

        # 웹캠/영상 동일한 크기로 맞춤
        frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        frame_count += 1

        # 해상도 축소 (속도 개선)
        display_frame = frame.copy()
        if USE_WEBCAM:
            ocr_frame = cv2.resize(frame, None, fx=0.7, fy=0.7)
        else:
            ocr_frame = frame 

        # 프레임 스킵
        if frame_count % FRAME_SKIP != 0:

            cv2.imshow("Parking System", display_frame)

            if cv2.waitKey(delay) & 0xFF == ord('q'):
                break

            continue

        # OCR 실행
        results = reader.readtext(ocr_frame)

        for (bbox, text, prob) in results:

            clean_text = text.replace(" ", "")

            if prob < MIN_CONFIDENCE:
                continue

            match = plate_pattern.search(clean_text)

            if match:

                matched_plate = match.group()
                scale = 1 # / 0.7
                (tl, tr, br, bl) = bbox
                top_left = (int(tl[0]*scale), int(tl[1]*scale))
                bottom_right = (int(br[0]*scale), int(br[1]*scale))

                cv2.rectangle(
                    display_frame,
                    top_left,
                    bottom_right,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    f"OCR: {matched_plate}",
                    (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )
                                
                
                now = time.time()

                # 이미 처리한 번호판이면 무시
                if matched_plate in seen_plates:
                    continue

                print(
                    f"✨ 번호판 인식: {matched_plate} (정확도 {prob:.2f})"
                )

                threading.Thread(
                    target=verify_plate,
                    args=(matched_plate,),
                    daemon=True
                ).start()

                # 기록
                seen_plates.add(matched_plate)
                last_sent_time[matched_plate] = now

        cv2.imshow("Parking System", display_frame)

        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
