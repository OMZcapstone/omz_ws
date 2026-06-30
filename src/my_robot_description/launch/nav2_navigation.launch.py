import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('my_robot_description')
    nav2_launch_dir = os.path.join(get_package_share_directory('nav2_bringup'), 'launch')
    source_map_dir = os.path.expanduser(
        '~/omz_ws/src/my_robot_description/maps/current'
    )
    installed_map_dir = os.path.join(package_dir, 'maps', 'current')
    map_dir = source_map_dir if os.path.exists(source_map_dir) else installed_map_dir

    default_map = os.path.join(map_dir, 'om_map_original_cleaned.yaml')
    keepout_mask = os.path.join(map_dir, 'keepout_mask_full_centerline_bias.yaml')
    default_params = os.path.join(package_dir, 'config', 'nav2_params.yaml')
    default_rviz = os.path.join(package_dir, 'rviz', 'slam.rviz')

    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')
    use_rviz_waypoint_goal = LaunchConfiguration('use_rviz_waypoint_goal')
    rviz_config = LaunchConfiguration('rviz_config')
    display = LaunchConfiguration('display')
    xauthority = LaunchConfiguration('xauthority')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Full path to the map yaml file',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Full path to the Nav2 parameters file',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz with the navigation launch',
        ),
        DeclareLaunchArgument(
            'use_rviz_waypoint_goal',
            default_value='true',
            description='Collect RViz Publish Point clicks as waypoints and send them with 2D Goal Pose',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz,
            description='Full path to the RViz config file',
        ),
        DeclareLaunchArgument(
            'display',
            default_value=EnvironmentVariable('DISPLAY', default_value=''),
            description='X11 display used by RViz. Uses the current shell DISPLAY by default.',
        ),
        DeclareLaunchArgument(
            'xauthority',
            default_value=EnvironmentVariable('XAUTHORITY', default_value=''),
            description='Xauthority file used by RViz. Uses the current shell XAUTHORITY by default.',
        ),

        SetEnvironmentVariable('DISPLAY', display),
        SetEnvironmentVariable('XAUTHORITY', xauthority),


        Node(
            package='nav2_map_server',
            executable='map_server',
            name='keepout_filter_mask_server',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'yaml_filename': keepout_mask,
                'topic_name': 'keepout_filter_mask',
                'frame_id': 'map',
            }],
        ),

        Node(
            package='nav2_map_server',
            executable='costmap_filter_info_server',
            name='costmap_filter_info_server',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'type': 0,
                'filter_info_topic': '/costmap_filter_info',
                'mask_topic': '/keepout_filter_mask',
                'base': 0.0,
                'multiplier': 1.0,
            }],
        ),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_keepout_filter',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': [
                    'keepout_filter_mask_server',
                    'costmap_filter_info_server',
                ],
            }],
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_launch_dir, 'bringup_launch.py')
            ),
            launch_arguments={
                'map': map_file,
                'params_file': params_file,
                'use_sim_time': use_sim_time,
                'use_composition': 'False',
            }.items(),
        ),

        Node(
            condition=IfCondition(use_rviz),
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
        ),

        Node(
            condition=IfCondition(use_rviz_waypoint_goal),
            package='my_robot_description',
            executable='rviz_waypoint_goal',
            name='rviz_waypoint_goal',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        ),
    ])
