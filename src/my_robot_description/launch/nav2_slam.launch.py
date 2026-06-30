import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('my_robot_description')
    default_params = os.path.join(package_dir, 'config', 'slam_toolbox.yaml')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    slam_start_delay = LaunchConfiguration('slam_start_delay')

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Full path to slam_toolbox parameters file',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock',
        ),
        DeclareLaunchArgument(
            'slam_start_delay',
            default_value='10.0',
            description='Delay SLAM startup so odom/base_link/laser TF is available first',
        ),
        TimerAction(
            period=slam_start_delay,
            actions=[
                Node(
                    package='slam_toolbox',
                    executable='async_slam_toolbox_node',
                    name='slam_toolbox',
                    output='screen',
                    parameters=[
                        params_file,
                        {'use_sim_time': use_sim_time},
                    ],
                ),
            ],
        ),
    ])
