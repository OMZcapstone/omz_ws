"""
젯슨 TTS 서버 - 오디오 파일 재생 방식
- 라즈베리파이로부터 "사람" / "차량" / "물체" / "불법" / "완료" 키워드를 수신
- "사람" / "차량" / "물체": warning.mp3 재생
- "불법": detection.mp3 재생
- "완료": restart.mp3 재생

사전 준비 (최초 1회):
    sudo apt install mpg123
    → warning.mp3, detection.mp3, restart.mp3를 이 스크립트와 같은 폴더에 넣기

실행:
    python3 jetson_tts_server.py
"""

import os
import queue
import socket
import subprocess
import threading

HOST = "0.0.0.0"
PORT = 9999
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_BY_KEYWORD = {
    "사람": os.path.join(SCRIPT_DIR, "warning.mp3"),
    "차량": os.path.join(SCRIPT_DIR, "warning.mp3"),
    "물체": os.path.join(SCRIPT_DIR, "warning.mp3"),
    "불법": os.path.join(SCRIPT_DIR, "detection.mp3"),
    "완료": os.path.join(SCRIPT_DIR, "restart.mp3"),
}
ENFORCE_MODE_BY_KEYWORD = {
    "불법": True,
    "완료": False,
}
WARNING_KEYWORDS = {"사람", "차량", "물체"}
illegal_parking_active = False
_enforce_keepalive_interval = 1.0

_play_q = queue.Queue()


def _publish_ros_topic(topic, msg_type, payload):
    try:
        subprocess.Popen(
            [
                "ros2",
                "topic",
                "pub",
                "--once",
                topic,
                msg_type,
                payload,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[ROS] {topic} -> {payload}")
    except FileNotFoundError:
        print("[WARN] ros2 명령을 찾을 수 없어 ROS 토픽을 발행하지 못했습니다.")


def _publish_enforce_mode(enabled):
    value = "true" if enabled else "false"
    _publish_ros_topic("/enforce_mode", "std_msgs/msg/Bool", f"{{data: {value}}}")


def _enforce_keepalive_worker():
    while True:
        if illegal_parking_active:
            _publish_enforce_mode(True)
        threading.Event().wait(_enforce_keepalive_interval)


def _play_worker():
    global illegal_parking_active

    while True:
        keyword = _play_q.get()
        audio_path = AUDIO_BY_KEYWORD.get(keyword)
        if audio_path is None:
            print(f"[WARN] 수신된 키워드가 유효하지 않습니다: {keyword}")
            _play_q.task_done()
            continue

        if keyword in ENFORCE_MODE_BY_KEYWORD:
            illegal_parking_active = ENFORCE_MODE_BY_KEYWORD[keyword]
            _publish_enforce_mode(illegal_parking_active)
        elif illegal_parking_active and keyword in WARNING_KEYWORDS:
            print(f"[SKIP] 불법주차 인식중 warning 오디오 생략: {keyword}")
            _play_q.task_done()
            continue

        if os.path.exists(audio_path):
            print(f"[PLAY] {keyword} -> {audio_path}")
            subprocess.run(["mpg123", "-q", audio_path])
        else:
            print(f"[WARN] 오디오 파일 없음: {audio_path}")
        _play_q.task_done()


threading.Thread(target=_play_worker, daemon=True).start()
threading.Thread(target=_enforce_keepalive_worker, daemon=True).start()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()
print(f"[INFO] TTS 서버 대기 중 (port {PORT})")
print("[INFO] 오디오 파일:")
for keyword, audio_path in AUDIO_BY_KEYWORD.items():
    print(f"  - {keyword}: {audio_path}")

while True:
    conn, addr = server.accept()
    with conn:
        keyword = conn.recv(1024).decode("utf-8").strip()
        if keyword:
            print(f"[수신] {keyword}")
            _play_q.put(keyword)
