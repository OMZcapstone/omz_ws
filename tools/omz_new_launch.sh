#!/usr/bin/env bash
set -euo pipefail

WS="${OMZ_WS:-$HOME/omz_ws}"
LOG_DIR="$HOME/.ros/omz_new"
PID_FILE="$LOG_DIR/pids"

mkdir -p "$LOG_DIR"

source_ros() {
  cd "$WS"
  set +u
  source /opt/ros/humble/setup.bash
  source install/setup.bash
  set -u
  export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
  export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
}

matching_pids() {
  local pattern="$1"
  pgrep -f "$pattern" 2>/dev/null | grep -v "^$$\$" || true
}

stop_existing() {
  local patterns=(
    "ros2 launch my_robot_description nav2_navigation.launch.py"
    "nav2_map_server/map_server"
    "nav2_map_server/costmap_filter_info_server"
    "nav2_lifecycle_manager/lifecycle_manager"
    "nav2_amcl/amcl"
    "nav2_controller/controller_server"
    "nav2_smoother/smoother_server"
    "nav2_planner/planner_server"
    "nav2_behaviors/behavior_server"
    "nav2_bt_navigator/bt_navigator"
    "nav2_waypoint_follower/waypoint_follower"
    "nav2_velocity_smoother/velocity_smoother"
    "ros2 launch my_robot_description robot_bringup.launch.py"
    "md_controller/lib/md_controller/md_controller"
    "sllidar_ros2/lib/sllidar_ros2/sllidar_node"
    "robot_state_publisher/robot_state_publisher"
  )

  echo "[new] stopping old bringup/nav2 processes..."
  for pattern in "${patterns[@]}"; do
    local pids
    pids="$(matching_pids "$pattern")"
    if [ -n "$pids" ]; then
      kill $pids 2>/dev/null || true
    fi
  done
  sleep 2

  for pattern in "${patterns[@]}"; do
    local pids
    pids="$(matching_pids "$pattern")"
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
    fi
  done
}

wait_for_topic_once() {
  local topic="$1"
  local timeout_s="$2"
  echo "[new] waiting for $topic..."
  local end=$((SECONDS + timeout_s))
  while [ "$SECONDS" -lt "$end" ]; do
    if timeout 4 bash -lc "
      set +u
      source /opt/ros/humble/setup.bash
      source '$WS/install/setup.bash'
      set -u
      export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
      export ROS_DOMAIN_ID='${ROS_DOMAIN_ID:-0}'
      export ROS_LOCALHOST_ONLY='${ROS_LOCALHOST_ONLY:-0}'
      ros2 topic echo '$topic' --once >/dev/null 2>&1
    "; then
      return 0
    fi
    sleep 1
  done
  echo "[new] timed out waiting for $topic" >&2
  return 1
}

wait_for_tf() {
  local target="$1"
  local source="$2"
  local timeout_s="$3"
  echo "[new] waiting for TF $target -> $source..."
  local end=$((SECONDS + timeout_s))
  while [ "$SECONDS" -lt "$end" ]; do
    if timeout 5 bash -lc "
      set +u
      source /opt/ros/humble/setup.bash
      source '$WS/install/setup.bash'
      set -u
      export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
      export ROS_DOMAIN_ID='${ROS_DOMAIN_ID:-0}'
      export ROS_LOCALHOST_ONLY='${ROS_LOCALHOST_ONLY:-0}'
      ros2 topic echo /tf --once 2>/dev/null
    " | grep -q "frame_id: $target" && timeout 5 bash -lc "
      set +u
      source /opt/ros/humble/setup.bash
      source '$WS/install/setup.bash'
      set -u
      export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
      export ROS_DOMAIN_ID='${ROS_DOMAIN_ID:-0}'
      export ROS_LOCALHOST_ONLY='${ROS_LOCALHOST_ONLY:-0}'
      ros2 topic echo /tf --once 2>/dev/null
    " | grep -q "child_frame_id: $source"; then
      return 0
    fi
    sleep 1
  done
  echo "[new] timed out waiting for TF $target -> $source" >&2
  return 1
}

start_launches() {
  : > "$LOG_DIR/bringup.log"
  : > "$LOG_DIR/nav.log"
  : > "$PID_FILE"

  echo "[new] starting robot_bringup..."
  setsid bash -lc "
    set +u
    source /opt/ros/humble/setup.bash
    source '$WS/install/setup.bash'
    set -u
    cd '$WS'
    export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
    export ROS_DOMAIN_ID='${ROS_DOMAIN_ID:-0}'
    export ROS_LOCALHOST_ONLY='${ROS_LOCALHOST_ONLY:-0}'
    exec ros2 launch my_robot_description robot_bringup.launch.py odom_encoder_ppr:=55
  " >>"$LOG_DIR/bringup.log" 2>&1 &
  local bringup_pid=$!
  echo "bringup=$bringup_pid" >> "$PID_FILE"

  wait_for_topic_once /odom 45
  wait_for_topic_once /scan 30
  wait_for_tf odom base_footprint 30

  echo "[new] robot is ready. starting nav2..."
  setsid bash -lc "
    set +u
    source /opt/ros/humble/setup.bash
    source '$WS/install/setup.bash'
    set -u
    cd '$WS'
    export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
    export ROS_DOMAIN_ID='${ROS_DOMAIN_ID:-0}'
    export ROS_LOCALHOST_ONLY='${ROS_LOCALHOST_ONLY:-0}'
    unset LIBGL_ALWAYS_INDIRECT
    export LIBGL_ALWAYS_SOFTWARE=1
    export QT_X11_NO_MITSHM=1
    export MESA_GL_VERSION_OVERRIDE=3.3
    exec ros2 launch my_robot_description nav2_navigation.launch.py use_rviz:=false
  " >>"$LOG_DIR/nav.log" 2>&1 &
  local nav_pid=$!
  echo "nav=$nav_pid" >> "$PID_FILE"

  echo "[new] started."
  echo "[new] bringup log: $LOG_DIR/bringup.log"
  echo "[new] nav log:     $LOG_DIR/nav.log"
  echo "[new] next: set 2D Pose Estimate in RViz, then send a goal."
}

show_status() {
  source_ros
  echo "[new] process summary:"
  ps -eo pid,ppid,pcpu,pmem,etimes,cmd | grep -E "robot_bringup|md_controller|sllidar|robot_state_publisher|nav2_navigation|controller_server|planner_server|bt_navigator|amcl|velocity_smoother" | grep -v grep || true
  echo
  echo "[new] ros nodes:"
  ros2 node list | sort || true
}

case "${1:-start}" in
  start)
    stop_existing
    ros2 daemon stop >/dev/null 2>&1 || true
    ros2 daemon start >/dev/null 2>&1 || true
    start_launches
    ;;
  stop)
    stop_existing
    ;;
  status)
    show_status
    ;;
  logs)
    echo "$LOG_DIR"
    ;;
  *)
    echo "usage: new [start|stop|status|logs]" >&2
    exit 2
    ;;
esac
