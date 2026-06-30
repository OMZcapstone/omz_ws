# vehicle_face

자율주행 차량 감정 표현 디스플레이 (도트 매트릭스 LED 스타일 표정)

상태 4종: 멈춤(stop) / 주행(driving) / 장애물(obstacle) / 단속(enforce)

## 1. 설치 위치

워크스페이스의 `src` 폴더 안에 이 폴더(`vehicle_face`)를 통째로 넣으세요.

    ~/ros2_ws/
    └── src/
        └── vehicle_face/   ← 이 폴더

Nav2와 같은 워크스페이스에 넣어도 되고, 별도 워크스페이스로 분리해도 됩니다.
토픽으로만 통신하므로 같은 ROS_DOMAIN_ID면 워크스페이스가 달라도 동작합니다.

## 2. pygame 설치 (face_display 실행에 필요)

    pip install pygame

## 3. 빌드

    cd ~/ros2_ws
    colcon build --packages-select vehicle_face
    source install/setup.bash

## 4. 실행

표정 화면 (모니터가 연결된 환경에서 실행):

    ros2 run vehicle_face face_display

상태 판단 노드 (주행 상태 → 표정 토픽 발행):

    ros2 run vehicle_face emotion_node

## 5. 테스트

토픽 수동 발행으로 표정 바꾸기:

    ros2 topic pub /emotion_state std_msgs/String "data: driving"

키보드 테스트: face_display 창에서 1~4번 키
    1=멈춤  2=주행  3=장애물  4=단속
    ESC = 종료

## 참고

- face_display 는 디스플레이(모니터)가 있는 환경에서만 실행됩니다.
  (SSH 단독 접속 시 화면 출력 불가)
- 단속 모드는 /enforce_mode (std_msgs/Bool) 토픽으로 트리거됩니다.
  카메라/단속 감지 노드에서 true 를 발행하면 표정이 단속으로 바뀝니다.
- 표정 픽셀 모양은 face_display.py 의 FACES 딕셔너리에서
  (열, 행) 좌표를 수정해 바꿀 수 있습니다.
