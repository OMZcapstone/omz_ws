import cv2
import easyocr
import requests
import re
import time
from datetime import datetime

# === 설정 ===
SERVER_URL = "http://127.0.0.1:8000/entry"  # FastAPI 서버 주소
MIN_CONFIDENCE = 0.5  # OCR 정확도 최소 기준 (0.0 ~ 1.0)
COOLDOWN_SECONDS = 5  # 같은 차량 재전송 방지 시간 (초)

# === 번호판 정규식 (한국 번호판 패턴) ===
# 예: 12가3456, 123가4567
plate_pattern = re.compile(r'\d{2,3}[가-힣]\d{4}')

def send_entry(plate_text):
    """서버로 입차 정보를 보냅니다."""
    try:
        # FastAPI 서버로 POST 요청
        payload = {"plate": plate_text, "color": "unknown", "vehicle_type": "auto"}
        res = requests.post(SERVER_URL, json=payload)
        
        if res.status_code == 200:
            print(f"✅ [서버 전송 성공] {plate_text} 입차 등록 완료")
        else:
            print(f"❌ [서버 오류] {res.text}")
    except Exception as e:
        print(f"⚠️ [통신 오류] 서버와 연결할 수 없습니다: {e}")

def main():
    print("📷 카메라 및 OCR 모델을 로딩 중입니다... (잠시만 기다려주세요)")
    
    # 1. OCR 리더기 초기화 (한국어, 영어) - 처음 실행 시 모델 다운로드로 시간 걸림
    # gpu=False는 CPU만 쓸 때 사용. NVIDIA 그래픽카드 있으면 True로 변경.
    reader = easyocr.Reader(['ko', 'en'], gpu=False) 

    # 2. 웹캠 켜기 (0번은 보통 노트북 내장 웹캠이지만 웹캠 연결시 0번은 웹캠으로 바뀌는 것 확인함)
    cap = cv2.VideoCapture(0) 
    
    # 카메라가 안 열리면 종료
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return

    last_sent_time = {} # 중복 전송 방지용 기록

    print("🚀 주차 관제 카메라 시작! (종료하려면 화면 클릭 후 'q' 누르세요)")

    while True:
        # 프레임 읽기
        ret, frame = cap.read()
        if not ret:
            break

        # --- OCR 인식 부분 ---
        # 매 프레임마다 하면 느리므로 5프레임마다 하거나, 여기서 바로 실행
        # 성능을 위해 이미지를 흑백으로 변환하거나 크기를 줄일 수도 있음
        
        # OCR 실행 (결과: [좌표, 텍스트, 정확도])
        results = reader.readtext(frame)

        for (bbox, text, prob) in results:
            # 공백 제거 및 정리
            clean_text = text.replace(" ", "")

            # 1) 정확도가 너무 낮으면 무시
            if prob < MIN_CONFIDENCE:
                continue

            # 2) 차량 번호판 형식인지 확인 (정규식)
            if plate_pattern.search(clean_text):
                matched_plate = plate_pattern.search(clean_text).group()
                
                # 화면에 인식된 박스와 글자 그리기
                (tl, tr, br, bl) = bbox
                top_left = (int(tl[0]), int(tl[1]))
                bottom_right = (int(br[0]), int(br[1]))
                
                cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
                cv2.putText(frame, f"{matched_plate} ({prob:.2f})", 
                            (top_left[0], top_left[1] - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # 3) 중복 전송 방지 (쿨다운 체크)
                now = time.time()
                if matched_plate not in last_sent_time or (now - last_sent_time[matched_plate] > COOLDOWN_SECONDS):
                    print(f"✨ 번호판 인식됨: {matched_plate} (정확도: {prob:.2f})")
                    send_entry(matched_plate) # 서버 전송 함수 호출
                    last_sent_time[matched_plate] = now
        
        # 화면 출력
        cv2.imshow('Parking System Camera', frame)

        # 'q' 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 정리
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()