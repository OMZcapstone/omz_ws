"""
젯슨 불법주차 판별 ROS2 노드
- 라즈베리파이로부터 차량 3D 위치를 TCP로 수신
- TF2로 카메라 좌표 → 맵 좌표 변환
- keepout_mask(경로)와 비교해 5초 이상 경로 위에 있으면 불법주차 판정
- 불법주차 차량 정보를 라즈베리파이로 반환

실행:
    python3 illegal_parking_node.py

사전 준비:
    pip install opencv-python pyyaml
"""

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
from geometry_msgs.msg import PointStamped
import tf2_geometry_msgs  # Registers geometry_msgs types for tf_buffer.transform().
import cv2
import numpy as np
import yaml
import json
import socket
import threading
import time
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────────────
MASK_PATH  = "/home/omz/omz_ws/src/my_robot_description/maps/current/keepout_mask_full_centerline_bias.pgm"
YAML_PATH  = "/home/omz/omz_ws/src/my_robot_description/maps/current/om_map_original_cleaned.yaml"
CAMERA_FRAME  = "camera_color_optical_frame"  # ros2 topic echo /tf_static 로 확인 후 수정
MAP_FRAME     = "map"
TCP_PORT      = 9997
ILLEGAL_SECS  = 5.0    # 경로 위 정지 판단 시간


class IllegalParkingNode(Node):
    def __init__(self):
        super().__init__('illegal_parking_node')

        # TF2
        self.tf_buffer   = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # keepout mask 로드
        self.mask = cv2.imread(MASK_PATH, cv2.IMREAD_GRAYSCALE)
        if self.mask is None:
            self.get_logger().error(f"마스크 파일 없음: {MASK_PATH}")
            raise FileNotFoundError(MASK_PATH)

        with open(YAML_PATH) as f:
            info = yaml.safe_load(f)
        self.resolution = info['resolution']          # m/pixel
        self.origin_x   = info['origin'][0]
        self.origin_y   = info['origin'][1]
        self.map_h      = self.mask.shape[0]
        self.get_logger().info(
            f"맵 로드 완료: {self.mask.shape}, "
            f"resolution={self.resolution}, origin=({self.origin_x},{self.origin_y})")

        # 차량 추적: {id: {first_on_path, alerted, box}}
        self._tracks = {}

        # TCP 서버 시작
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("0.0.0.0", TCP_PORT))
        self._server.listen()
        threading.Thread(target=self._tcp_accept, daemon=True).start()
        self.get_logger().info(f"TCP 서버 대기 중 (port {TCP_PORT})")

    # ── 좌표 변환 유틸 ─────────────────────────────────────────────────────────
    def _world_to_pixel(self, x_world, y_world):
        px = int((x_world - self.origin_x) / self.resolution)
        py = int(self.map_h - (y_world - self.origin_y) / self.resolution)
        return px, py

    def _is_on_path(self, px, py):
        if 0 <= py < self.mask.shape[0] and 0 <= px < self.mask.shape[1]:
            return int(self.mask[py, px]) > 127   # 흰색 = 경로
        return False

    def _to_map_frame(self, x_cam, y_cam, z_cam, frame):
        try:
            pt = PointStamped()
            pt.header.frame_id = frame
            pt.header.stamp    = self.get_clock().now().to_msg()
            pt.point.x = float(x_cam)
            pt.point.y = float(y_cam)
            pt.point.z = float(z_cam)
            out = self.tf_buffer.transform(pt, MAP_FRAME,
                                           timeout=Duration(seconds=0.1))
            return out.point.x, out.point.y
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            return None, None

    # ── TCP 서버 ───────────────────────────────────────────────────────────────
    def _tcp_accept(self):
        while True:
            conn, addr = self._server.accept()
            self.get_logger().info(f"라즈베리파이 연결: {addr}")
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        buf = ""
        try:
            while True:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    illegal_list  = self._process(msg)
                    response      = json.dumps({"illegal": illegal_list}) + '\n'
                    conn.sendall(response.encode('utf-8'))
        except Exception as e:
            self.get_logger().warn(f"클라이언트 오류: {e}")
        finally:
            conn.close()
            self.get_logger().info("라즈베리파이 연결 종료")

    def _process(self, msg):
        now         = time.time()
        vehicles    = msg.get('vehicles', [])
        current_ids = set()
        illegal     = []

        for v in vehicles:
            vid   = v['id']
            box   = v['box']
            frame = v.get('frame', CAMERA_FRAME)
            current_ids.add(vid)

            # 카메라 좌표 → 맵 좌표
            x_map, y_map = self._to_map_frame(v['x'], v['y'], v['z'], frame)
            if x_map is None:
                self.get_logger().warn("TF 변환 실패 — Nav2/SLAM이 실행 중인지 확인하세요", once=True)
                continue

            # 경로 위 여부 확인
            px, py    = self._world_to_pixel(x_map, y_map)
            on_path   = self._is_on_path(px, py)

            # 추적 상태 갱신
            if vid not in self._tracks:
                self._tracks[vid] = {
                    'first_on_path': now if on_path else None,
                    'alerted': False,
                    'box': box,
                }
            else:
                t = self._tracks[vid]
                t['box'] = box
                if on_path:
                    if t['first_on_path'] is None:
                        t['first_on_path'] = now
                else:
                    t['first_on_path'] = None
                    t['alerted']       = False

            # 불법주차 판정
            t = self._tracks[vid]
            if (on_path
                    and t['first_on_path'] is not None
                    and not t['alerted']
                    and (now - t['first_on_path']) >= ILLEGAL_SECS):
                t['alerted'] = True
                illegal.append({'id': vid, 'box': box})
                self.get_logger().info(f"불법주차 감지! 차량 ID={vid}")

        # 사라진 차량 제거
        for old_id in list(self._tracks.keys()):
            if old_id not in current_ids:
                del self._tracks[old_id]

        return illegal


def main():
    rclpy.init()
    node = IllegalParkingNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
