cmake_minimum_required(VERSION 3.8)
project(my_robot_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY behavior_trees config launch maps rviz urdf
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/paint_keepout_rect.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME paint_keepout_rect
)

install(
  PROGRAMS scripts/q_emergency_stop.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME q_emergency_stop
)

install(
  PROGRAMS scripts/scan_visual_filter.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME scan_visual_filter
)

install(
  PROGRAMS scripts/odom_drive_test.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME odom_drive_test
)

install(
  PROGRAMS scripts/rviz_waypoint_goal.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME rviz_waypoint_goal
)

ament_package()
