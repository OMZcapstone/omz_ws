import os
import shutil
from datetime import datetime

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import ExecuteProcess
from launch.actions import OpaqueFunction
from launch.substitutions import LaunchConfiguration


def backup_existing_map(context, *args, **kwargs):
    map_file = LaunchConfiguration('map_file').perform(context)
    current_dir = os.path.dirname(map_file)
    old_dir = os.path.abspath(os.path.join(current_dir, '..', 'old'))
    basename = os.path.basename(map_file)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    os.makedirs(old_dir, exist_ok=True)

    for extension in ('.yaml', '.pgm', '.png'):
        source = f'{map_file}{extension}'
        if not os.path.exists(source):
            continue

        destination = os.path.join(old_dir, f'{basename}_{timestamp}{extension}')
        counter = 1
        while os.path.exists(destination):
            destination = os.path.join(old_dir, f'{basename}_{timestamp}_{counter}{extension}')
            counter += 1

        shutil.move(source, destination)
        print(f'Moved previous map to {destination}')

    return []


def generate_launch_description():
    map_file = LaunchConfiguration('map_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map_file',
            default_value='/home/omz/omz_ws/src/my_robot_description/maps/current/omz_map',
            description='Output map file path without extension',
        ),
        OpaqueFunction(function=backup_existing_map),
        ExecuteProcess(
            cmd=[
                'ros2',
                'run',
                'nav2_map_server',
                'map_saver_cli',
                '-f',
                map_file,
            ],
            output='screen',
        ),
    ])
