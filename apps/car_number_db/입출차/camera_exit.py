import cv2
import easyocr
import requests
import re
import time

# === 설정 ===
# 주의: 출차는 주소 뒤에 번호판이 붙습니다 (예: .../exit/12가3456)
BASE_URL = "http://127.0.0.1:8000/exit" 
MIN_CONFIDENCE = 0.5
COOLDOWN_SECONDS = 5
CAMERA_ID = 1  # ★ USB 웹캠을 사용한다면 1번, 노트북 내장은 0번

# 번호판 정규식
plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')

def send_exit(plate_text):
    """서버로 출차 요청을 보냅니다."""
    try:
        # FastAPI의 exit 주소 형식에 맞춰 URL 생성
        url = f"{BASE_URL}/{plate_text}"
        
        # POST 요청 전송 (Body 없음)
        res = requests.post(url)
        
        if res.status_code == 200:
            print(f"👋 [출차 완료] {plate_text} 안녕히 가세요!")
        else:
            print(f"❌ [서버 오류] {res.text}")
    except Exception as e:
        print(f"⚠️ [통신 오류] {e}")

def main():
    print("📷 [출차용] 카메라 및 OCR 로딩 중...")
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
    
    # 웹캠 켜기 (0번은 보통 노트북 내장 웹캠이지만 웹캠 연결시 0번은 웹캠으로 바뀌는 것 확인함)
    cap = cv2.VideoCapture(0) 
    
    # 카메라가 안 열리면 종료
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return

    last_sent_time = {}

    print("🚀 출차 게이트 가동 시작! (종료: 'q')")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = reader.readtext(frame)

        for (bbox, text, prob) in results:
            clean_text = text.replace(" ", "")

            if prob < MIN_CONFIDENCE:
                continue

            if plate_pattern.search(clean_text):
                matched_plate = plate_pattern.search(clean_text).group()
                
                # 시각화 (출차는 빨간색 BGR: 0, 0, 255)
                (tl, tr, br, bl) = bbox
                top_left = (int(tl[0]), int(tl[1]))
                bottom_right = (int(br[0]), int(br[1]))
                
                cv2.rectangle(frame, top_left, bottom_right, (0, 0, 255), 2)
                cv2.putText(frame, f"EXIT: {matched_plate}", 
                            (top_left[0], top_left[1] - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                # 중복 전송 방지
                now = time.time()
                if matched_plate not in last_sent_time or (now - last_sent_time[matched_plate] > COOLDOWN_SECONDS):
                    print(f"✨ 출차 차량 인식: {matched_plate}")
                    send_exit(matched_plate)
                    last_sent_time[matched_plate] = now
        
        cv2.imshow('Exit Gate Camera', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()