#!/usr/bin/env python3
import math

import rclpy
from rclpy.time import Time
from rclpy.node import Node
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class EmotionNode(Node):
    """
    주행 상태를 판단해 /emotion_state 토픽으로 표정 상태를 발행.
    발행 값: "stop" | "driving" | "obstacle" | "enforce"

    판단 우선순위 (위에서부터):
      1. enforce  : 불법주차 단속 모드 (/enforce_mode = true)
      2. obstacle : 라이다 전방 60도 최소거리 < 0.4m
      3. driving  : 속도가 있음 (이동 중)
      4. stop     : 정지 상태
    """

    def __init__(self):
        super().__init__('emotion_node')
        self.pub = self.create_publisher(String, '/emotion_state', 10)

        self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        # 불법주차 단속 모드 신호 (카메라/단속 노드가 발행한다고 가정)
        self.create_subscription(Bool, '/enforce_mode', self.enforce_cb, 10)

        self.last_speed = 0.0
        self.min_dist = 999.0
        self.enforce = False
        self.last_state = None
        self.obstacle = False

        # enforce 상태 10초 자동 해제용
        self.enforce_time = None
        self.enforce_timeout = 10.0  # 초

        # 임계값 (필요시 조정)
        # 전방 60도 범위 내에서 2m 이내를 장애물로 판단하도록 변경
        self.obstacle_dist = 1.0   # m
        self.obstacle_clear_dist = 2.2   # m, 경계 깜빡임 방지
        self.front_angle = math.radians(60.0)   # 전방 좌우 30도
        self.move_speed = 0.01     # 이 이상이면 주행으로 판단

        self.create_timer(0.3, self.update)   # 약 3Hz 발행
        self.get_logger().info(
            'emotion_node started: publishing /emotion_state. '
            'Run "ros2 run vehicle_face face_display" to show the face.'
        )

    def cmd_cb(self, msg):
        self.last_speed = abs(msg.linear.x) + abs(msg.angular.z)

    def scan_cb(self, msg):
        # 전방(center at 0) 60도(좌우 30도) 범위의 유효 거리만 수집
        half_front = self.front_angle / 2.0
        valid = []

        for i, r in enumerate(msg.ranges):
            angle = msg.angle_min + i * msg.angle_increment
            # 각도를 -pi..pi 범위로 정규화 (forward center = 0)
            ang_norm = (angle + math.pi) % math.tau - math.pi
            if abs(ang_norm) <= half_front and math.isfinite(r) and r > 0.0:
                valid.append(r)

        self.min_dist = min(valid) if valid else 999.0

    def enforce_cb(self, msg):
        self.enforce = msg.data
        # enforce가 처음 진입할 때만 타이머 시작
        if msg.data and self.enforce_time is None:
            self.enforce_time = self.get_clock().now()

    def update(self):
        moving = self.last_speed > self.move_speed
        if self.min_dist < self.obstacle_dist:
            self.obstacle = True
        elif self.min_dist > self.obstacle_clear_dist:
            self.obstacle = False

        # enforce 타이머 체크: 10초 지나면 enforce 해제
        if self.enforce and self.enforce_time is not None:
            elapsed = (self.get_clock().now() - self.enforce_time).nanoseconds / 1e9
            if elapsed >= self.enforce_timeout:
                self.enforce = False
                self.enforce_time = None

        # 상태 결정: 정지 표정은 '정지'이면서 '장애물 없음'일 때만 표시
        if self.enforce:
            state = "enforce"
        elif not moving and not self.obstacle:
            state = "stop"
        elif self.obstacle:
            state = "obstacle"
        elif moving:
            state = "driving"
        else:
            state = "stop"

        msg = String()
        msg.data = state
        self.pub.publish(msg)

        if state != self.last_state:
            self.get_logger().info(f'emotion_state: {state}')
            self.last_state = state


def main():
    rclpy.init()
    rclpy.spin(EmotionNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
