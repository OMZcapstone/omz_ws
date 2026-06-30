#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
source install/setup.bash

if [[ -z "${DISPLAY:-}" ]]; then
  export DISPLAY=:0
fi

echo "DISPLAY=${DISPLAY}"

if [[ -z "${XAUTHORITY:-}" && -f "${HOME}/.Xauthority" ]]; then
  export XAUTHORITY="${HOME}/.Xauthority"
fi

if ! xdpyinfo >/dev/null 2>&1; then
  echo "Cannot open the Jetson Nano desktop display (${DISPLAY})."
  echo "Run this from the Jetson Nano desktop terminal, or allow this user to use the local display:"
  echo "  xhost +SI:localuser:${USER}"
  exit 1
fi

rviz2 -d config/robot.rviz
