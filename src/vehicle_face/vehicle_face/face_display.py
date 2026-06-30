#!/usr/bin/env python3
"""
자율주행 차량 감정 표현 디스플레이 (EMO 스타일 둥근 눈 + 입)

상태 4종:
  stop     멈춤   - 노란색, 아래로 볼록한 반달 눈 + 짧은 일자 입 (차분)
  driving  주행   - 초록색, 위로 휜 반달 눈(^^) + 활짝 웃는 입 (활기)
  obstacle 장애물 - 주황색, 크고 동그란 눈 + 작은 o 입 (놀람)
  enforce  단속   - 빨간색, 사선 찡그린 눈 + 아래로 휜 입 (경계)

키보드 1~4번으로 수동 전환 가능 / ESC 종료
/emotion_state (std_msgs/String) 토픽으로 자동 전환
"""
import math
import threading

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
import pygame

# 상태별 발광 색상 (R, G, B)
COLORS = {
    "stop":     (255, 210, 63),
    "driving":  (93, 255, 90),
    "obstacle": (255, 138, 60),
    "enforce":  (255, 59, 48),
}
DEFAULT_STATE = "stop"

BG_COLOR = (13, 13, 13)

KEYMAP = {
    pygame.K_1: "stop",
    pygame.K_2: "driving",
    pygame.K_3: "obstacle",
    pygame.K_4: "enforce",
}


# ---------- 발광(glow) 그리기 헬퍼 ----------
# pygame은 그림자/글로우 기본 지원이 없어, 반투명 레이어를 겹쳐 발광을 흉내냄.

def _blend(color, t):
    """color를 배경색 쪽으로 t(0~1)만큼 섞어 어둡게."""
    return tuple(int(c * (1 - t) + BG_COLOR[i] * t) for i, c in enumerate(color))


def glow_circle(surf, color, center, radius, filled=True, width=0):
    """동그란 발광 원/링."""
    # 바깥 발광 헤일로 (큰 반투명 원 여러 겹)
    for i in range(6, 0, -1):
        halo = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        a = int(22 * i / 6)
        pygame.draw.circle(halo, (*color, a), (radius * 2, radius * 2),
                           int(radius + i * radius * 0.18))
        surf.blit(halo, (center[0] - radius * 2, center[1] - radius * 2))
    if filled:
        pygame.draw.circle(surf, color, center, radius)
    else:
        pygame.draw.circle(surf, color, center, radius, width)


def glow_ellipse(surf, color, rect, filled=True, width=0):
    """가로/세로 비율을 줄 수 있는 둥근 발광 타원."""
    x, y, w, h = rect
    for i in range(6, 0, -1):
        grow = i * min(w, h) * 0.09
        halo = pygame.Rect(x - grow, y - grow, w + grow * 2, h + grow * 2)
        col = _blend(color, 0.55 + 0.06 * i)
        pygame.draw.ellipse(surf, col, halo, 0 if filled else width + i * 2)
    pygame.draw.ellipse(surf, color, rect, 0 if filled else width)


def _ellipse_point(rect, angle):
    cx = rect[0] + rect[2] / 2
    cy = rect[1] + rect[3] / 2
    return (
        int(cx + (rect[2] / 2) * math.cos(angle)),
        int(cy - (rect[3] / 2) * math.sin(angle)),
    )


def _arc_points(rect, start, end, steps=36):
    if end < start:
        end += math.tau
    return [_ellipse_point(rect, start + (end - start) * i / steps)
            for i in range(steps + 1)]


def glow_arc(surf, color, rect, start, end, width):
    """발광 호(반달/곡선 입). rect=(x,y,w,h), 각도는 라디안."""
    points = _arc_points(rect, start, end)
    # 헤일로: 같은 호를 더 두껍고 어둡게 여러 겹
    for i in range(4, 0, -1):
        col = _blend(color, 0.55 + 0.1 * i)
        layer_width = width + i * 3
        pygame.draw.lines(surf, col, False, points, layer_width)
        for p in points:
            pygame.draw.circle(surf, col, p, max(1, layer_width // 2))
    pygame.draw.lines(surf, color, False, points, width)
    for p in points:
        pygame.draw.circle(surf, color, p, max(1, width // 2))


def glow_line(surf, color, p1, p2, width):
    """발광 직선(일자 입)."""
    for i in range(4, 0, -1):
        col = _blend(color, 0.55 + 0.1 * i)
        layer_width = width + i * 3
        pygame.draw.line(surf, col, p1, p2, layer_width)
        pygame.draw.circle(surf, col, p1, max(1, layer_width // 2))
        pygame.draw.circle(surf, col, p2, max(1, layer_width // 2))
    pygame.draw.line(surf, color, p1, p2, width)
    pygame.draw.circle(surf, color, p1, max(1, width // 2))
    pygame.draw.circle(surf, color, p2, max(1, width // 2))


def glow_round_rect(surf, color, cx, cy, w, h, radius, angle):
    """회전된 둥근 사각형 발광 (단속용 사선 눈)."""
    pad = 40
    box = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    # 헤일로
    for i in range(5, 0, -1):
        a = int(20 * i / 5)
        grow = i * 4
        pygame.draw.rect(box, (*color, a),
                         (pad - grow / 2, pad - grow / 2, w + grow, h + grow),
                         border_radius=int(radius + grow / 2))
    pygame.draw.rect(box, color, (pad, pad, w, h), border_radius=radius)
    rot = pygame.transform.rotate(box, math.degrees(angle))
    rect = rot.get_rect(center=(cx, cy))
    surf.blit(rot, rect)


# ---------- 표정 그리기 ----------

def draw_face(screen, state, w, h):
    screen.fill(BG_COLOR)
    color = COLORS[state]

    # 화면 크기에 맞춰 스케일 (기준 520x400 디자인)
    s = min(w / 520.0, h / 400.0)
    cx = w / 2
    eye_y = h / 2 - 30 * s
    ex_l = cx - 95 * s
    ex_r = cx + 95 * s
    m_y = h / 2 + 95 * s

    if state == "stop":
        # 눈: 아래로 볼록한 반달 (∪) - pygame은 하단 절반 호
        for ex in (ex_l, ex_r):
            rect = (ex - 56 * s, eye_y - 54 * s, 112 * s, 88 * s)
            glow_arc(screen, color, rect, math.pi * 1.12, math.pi * 1.88, int(14 * s))
        # 입: 짧은 일자
        glow_line(screen, color, (cx - 42 * s, m_y), (cx + 42 * s, m_y), int(12 * s))

    elif state == "driving":
        # 눈: 세로 캡슐눈
        for ex in (ex_l, ex_r):
            glow_round_rect(screen, color, int(ex), int(eye_y),
                            int(58 * s), int(98 * s), int(29 * s), 0.0)
        # 입: 활짝 웃는 곡선 (아래로 볼록 ∪)
        r = 58 * s
        rect = (cx - r, m_y - 26 * s - r, r * 2, r * 2)
        glow_arc(screen, color, rect, math.pi * 1.15, math.pi * 1.85, int(15 * s))

    elif state == "obstacle":
        # 눈: 놀란 느낌의 둥근 눈
        for ex in (ex_l, ex_r):
            glow_ellipse(screen, color,
                         (ex - 32 * s, eye_y - 37 * s, 64 * s, 74 * s),
                         filled=True)
        # 입: 작은 동그란 o
        glow_circle(screen, color, (int(cx), int(m_y)), int(22 * s),
                    filled=False, width=int(12 * s))

    elif state == "enforce":
        # 눈: 안쪽이 내려간 사선 둥근 네모 (찡그림)
        glow_round_rect(screen, color, int(ex_l), int(eye_y),
                        int(94 * s), int(58 * s), int(29 * s), +0.34)
        glow_round_rect(screen, color, int(ex_r), int(eye_y),
                        int(94 * s), int(58 * s), int(29 * s), -0.34)
        # 입: 위로 볼록한 곡선 (∩, 불만/찡그림)
        r = 46 * s
        rect = (cx - r, m_y - 10 * s - r, r * 2, r * 2)
        glow_arc(screen, color, rect, math.pi * 0.2, math.pi * 0.8, int(13 * s))


class FaceDisplay(Node):
    def __init__(self):
        super().__init__('face_display')
        self.state = DEFAULT_STATE
        self.create_subscription(String, '/emotion_state', self.cb, 10)

    def cb(self, msg):
        # 주행 상태 노드(emotion_node)가 발행하는 토픽으로 표정 변경
        if msg.data in COLORS:
            self.state = msg.data


def main():
    rclpy.init()
    node = FaceDisplay()

    def spin_ros():
        try:
            rclpy.spin(node)
        except ExternalShutdownException:
            pass

    threading.Thread(target=spin_ros, daemon=True).start()

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    w, h = screen.get_size()
    clock = pygame.time.Clock()

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key in KEYMAP:
                    # 키보드로 누르면 토픽보다 우선해 즉시 덮어씀
                    node.state = KEYMAP[e.key]
        draw_face(screen, node.state, w, h)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
