# Robot Run Commands

## 0. 빌드





face status
face stop
face restart
face log

 sudo modprobe xpad
```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
colcon build --symlink-install
source install/setup.bash
```

source ~/.bashrc

## 1. 로봇 전체 실행 start

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch my_robot_description robot_bringup.launch.py
```

현재 주행 기준 odometry는 휠 오돔 `/odom`만 사용합니다. EKF는 실행하지 않습니다.
현재 휠 오돔 보정값은 `odom_encoder_ppr:=55`입니다.

## 1-1. 로봇 + Nav2 한번에 실행 new

중복으로 떠 있는 bringup/Nav2를 먼저 정리한 뒤, `robot_bringup`을 켜고 `/odom`, `/scan`, TF 준비를 확인한 다음 Nav2를 켭니다.

```bash
new
```

상태/로그/정지:

```bash
newstatus
newlogs
newstop
```



## 2. SLAM Toolbox 맵 생성 toolbox

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch my_robot_description nav2_slam.launch.py
```


## 4. 키보드 조종 key

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard
```

## 5. 맵 저장 map

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch my_robot_description save_current_map.launch.py
```

저장 위치:

```text
/home/omz/omz_ws/src/my_robot_description/maps/current/omz_map.yaml
/home/omz/omz_ws/src/my_robot_description/maps/current/omz_map.pgm
```

## 6. 자율주행 테스트 코드 
```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch my_robot_description nav2_navigation.launch.py
```

휠 오돔 1m 직진 테스트:

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run my_robot_description odom_drive_test --ros-args -p speed:=0.05 -p target_distance:=1.0 -p duration:=20.0
```

## 6. Depth Camera + YOLO 실행

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch yolo_object_detection orbbec_yolo.launch.py
```

## 7. Depth Camera + YOLO 실행, 미리보기 끄기

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch yolo_object_detection orbbec_yolo.launch.py show_preview:=false
```

## 8. 모니터 표정 실행 face

원격 터미널에서 로봇에 연결된 모니터로 표정창 실행 + 자동 표정 변경 노드 실행:

```bash
face
```

표정창 관리:

```bash
face status
face stop
face restart
face log
```

모니터가 연결된 화면 터미널에서 실행:

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run vehicle_face face_display
```

자동 표정 변경 노드만 따로 실행할 때:

```bash
cd ~/omz_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run vehicle_face emotion_node
```

표정 수동 테스트:

```bash
ros2 topic pub /emotion_state std_msgs/String "data: driving"
```

## 9. USB 스피커 + TTS 서버 실행 say

0번 USB Audio를 기본 스피커로 잡고 `jetson_tts_server.py` 실행:

```bash
say
```

직접 실행할 때:

```bash
pactl set-default-sink alsa_output.usb-Generic_AB13X_USB_Audio_20210726905926-00.analog-stereo
python3 ~/omz_ws/external/depth_camera/jetson_tts_server.py
```

mkdir -p ~/restore_omz_ws
cd ~/restore_omz_ws
tar --zstd -xf ~/omz_ws/snapshots/full_workspace/omz_ws_full_snapshot_20260526_124345.tar.zst
