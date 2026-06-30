from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='illegal_parking_detector',
            executable='illegal_parking_node',
            name='illegal_parking_node',
            output='screen',
        ),
    ])
