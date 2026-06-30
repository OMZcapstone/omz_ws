# 🚗 AI 스마트 주차 관제 시스템 (AI Smart Parking System)

**FastAPI** 서버와 **EasyOCR (AI)** 기술을 활용하여 차량의 입차와 출차를 자동으로 관리하는 시스템입니다.
주차장 입구와 출구에 설치된 카메라(웹캠)가 번호판을 인식하면 서버로 전송하여 DB에 기록하고, 출차 시 상태를 업데이트합니다.

---

## 📂 프로젝트 파일 구조

| 파일명 | 설명 |
| :--- | :--- |
| **`app.py`** | **메인 서버**. 입차(`entry`), 출차(`exit`), 검증(`verify`) API를 제공합니다. |
| **`db.py`** | SQLite 데이터베이스(`parking.db`) 연결 및 초기화를 담당합니다. |
| **`camera_entry.py`** | **입구 카메라**. 차량 번호를 인식하여 `/entry` API로 전송합니다. |
| **`camera_exit.py`** | **출구 카메라**. 차량 번호를 인식하여 `/exit` API로 전송합니다. |
| **`client.ps1`** | **수동 테스트 도구**. PowerShell에서 API를 쉽게 호출하기 위한 스크립트입니다. |
| **`check_db.py`** | 현재 주차 중인 차량 목록(`parked_vehicle`)을 조회합니다. |
| **`check_log.py`** | OCR 인식 로그 및 정확도 점수(`plate_read_log`)를 조회합니다. |

---

## 🛠️ 1. 설치 및 환경 설정

프로젝트 실행에 필요한 Python 라이브러리를 설치합니다.

```bash
pip install fastapi uvicorn opencv-python easyocr requests
```

## 🚀 2. 서버 실행 (Backend)
가장 먼저 주차 관제 서버를 실행해야 합니다.
```
uvicorn app:app --reload
```
서버 주소: http://127.0.0.1:8000

API 문서: http://127.0.0.1:8000/docs 

## 📷 3. 카메라 자동화 모드 (AI)
실제 카메라를 연결하여 입차와 출차를 자동으로 처리합니다.

🟢 **입차 게이트 (Entry)**   
입구 쪽 카메라가 번호판을 인식하면 DB에 parked 상태로 저장합니다.   

```
python camera_entry.py
```
🔴 **출차 게이트 (Exit)**   
출구 쪽 카메라가 번호판을 인식하면 DB 상태를 exited로 업데이트합니다.

```
python camera_exit.py
```

💡 **설정 팁 (오인식 방지)**

카메라 ID: cv2.VideoCapture(0)은 노트북 내장캠, USB 웹캠 연결 시 0이 웹캠으로 바뀝니다. 연결환경에 따라 다르므로 0~3으로 숫자를 높여가며 원하는 캠에 연결하면 됩니다. 

정확도(Confidence): "154러"가 "154리"로 인식되는 등 오인식이 발생하는 경우가 있으므로 이 문제는 추후에 정확도가 0.8이상인 경우에만 서버에 등록하는 것으로 개선할 필요가 있습니다. 