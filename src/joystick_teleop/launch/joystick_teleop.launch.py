from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('max_lin_vel', default_value='0.09'),
        DeclareLaunchArgument('max_ang_vel', default_value='0.12'),
        DeclareLaunchArgument('cmd_vel_topic', default_value='cmd_vel'),
        DeclareLaunchArgument('joy_dev', default_value='0'),
        DeclareLaunchArgument('joy_device_name', default_value=''),
        DeclareLaunchArgument('axis_linear', default_value='1'),
        DeclareLaunchArgument('axis_angular', default_value='0'),
        DeclareLaunchArgument('button_speed_up', default_value='3'),
        DeclareLaunchArgument('button_speed_down', default_value='0'),
        DeclareLaunchArgument('button_deadman', default_value='5'),
        DeclareLaunchArgument('button_stop', default_value='1'),
        DeclareLaunchArgument('invert_linear', default_value='false'),
        DeclareLaunchArgument('invert_angular', default_value='false'),
        DeclareLaunchArgument('initial_linear_speed', default_value='0.03'),
        DeclareLaunchArgument('initial_reverse_linear_speed', default_value='0.03'),
        DeclareLaunchArgument('button_speed_step', default_value='0.01'),

        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_id': LaunchConfiguration('joy_dev'),
                'device_name': LaunchConfiguration('joy_device_name'),
                'deadzone': 0.1,
                'autorepeat_rate': 20.0,
            }],
            output='screen',
        ),

        Node(
            package='joystick_teleop',
            executable='joystick_teleop',
            name='joystick_teleop',
            parameters=[{
                'max_lin_vel': ParameterValue(LaunchConfiguration('max_lin_vel'), value_type=float),
                'max_ang_vel': ParameterValue(LaunchConfiguration('max_ang_vel'), value_type=float),
                'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic'),
                'axis_linear': ParameterValue(LaunchConfiguration('axis_linear'), value_type=int),
                'axis_angular': ParameterValue(LaunchConfiguration('axis_angular'), value_type=int),
                'button_speed_up': ParameterValue(
                    LaunchConfiguration('button_speed_up'),
                    value_type=int,
                ),
                'button_speed_down': ParameterValue(
                    LaunchConfiguration('button_speed_down'),
                    value_type=int,
                ),
                'button_deadman': ParameterValue(LaunchConfiguration('button_deadman'), value_type=int),
                'button_stop': ParameterValue(LaunchConfiguration('button_stop'), value_type=int),
                'invert_linear': ParameterValue(LaunchConfiguration('invert_linear'), value_type=bool),
                'invert_angular': ParameterValue(LaunchConfiguration('invert_angular'), value_type=bool),
                'initial_linear_speed': ParameterValue(
                    LaunchConfiguration('initial_linear_speed'),
                    value_type=float,
                ),
                'initial_reverse_linear_speed': ParameterValue(
                    LaunchConfiguration('initial_reverse_linear_speed'),
                    value_type=float,
                ),
                'button_speed_step': ParameterValue(
                    LaunchConfiguration('button_speed_step'),
                    value_type=float,
                ),
            }],
            output='screen',
        ),
    ])
