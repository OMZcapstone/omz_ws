import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_dir = get_package_share_directory('my_robot_description')
    orbbec_dir = get_package_share_directory('orbbec_camera')
    urdf_path = os.path.join(package_dir, 'urdf', 'two_wheel_caster_robot.urdf')
    astra_launch_path = os.path.join(orbbec_dir, 'launch', 'astra.launch.py')

    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    motor_port = LaunchConfiguration('motor_port')
    motor_baudrate = LaunchConfiguration('motor_baudrate')
    lidar_port = LaunchConfiguration('lidar_port')
    lidar_baudrate = LaunchConfiguration('lidar_baudrate')
    imu_port = LaunchConfiguration('imu_port')
    imu_baudrate = LaunchConfiguration('imu_baudrate')
    use_motor = LaunchConfiguration('use_motor')
    use_lidar = LaunchConfiguration('use_lidar')
    use_imu = LaunchConfiguration('use_imu')
    use_camera = LaunchConfiguration('use_camera')
    use_sim_time = LaunchConfiguration('use_sim_time')
    angular_cmd_scale = LaunchConfiguration('angular_cmd_scale')
    odom_encoder_ppr = LaunchConfiguration('odom_encoder_ppr')
    odom_tf_time_offset = LaunchConfiguration('odom_tf_time_offset')
    odom_publish_rate = LaunchConfiguration('odom_publish_rate')
    debug_motor_serial = LaunchConfiguration('debug_motor_serial')
    publish_odom_tf = LaunchConfiguration('publish_odom_tf')
    motor_cmd_scale = LaunchConfiguration('motor_cmd_scale')
    left_motor_cmd_scale = LaunchConfiguration('left_motor_cmd_scale')
    right_motor_cmd_scale = LaunchConfiguration('right_motor_cmd_scale')
    use_rpm_odom_fallback = LaunchConfiguration('use_rpm_odom_fallback')
    rpm_odom_min_abs = LaunchConfiguration('rpm_odom_min_abs')

    return LaunchDescription([
        DeclareLaunchArgument(
            'motor_port',
            default_value='/dev/serial/by-path/platform-3610000.usb-usb-0:2.1:1.0-port0'),
        DeclareLaunchArgument('motor_baudrate', default_value='19200'),
        DeclareLaunchArgument(
            'lidar_port',
            default_value='/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_fa428e004b7fef11973d241cedd322a4-if00-port0'),
        DeclareLaunchArgument('lidar_baudrate', default_value='460800'),
        DeclareLaunchArgument(
            'imu_port',
            default_value='/dev/serial/by-path/platform-3610000.usb-usb-0:2.4.1:1.0-port0'),
        DeclareLaunchArgument('imu_baudrate', default_value='9600'),
        DeclareLaunchArgument('use_motor', default_value='true'),
        DeclareLaunchArgument('use_lidar', default_value='true'),
        DeclareLaunchArgument('use_imu', default_value='false'),
        DeclareLaunchArgument('use_camera', default_value='false'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('angular_cmd_scale', default_value='0.6'),
        DeclareLaunchArgument(
            'odom_encoder_ppr',
            default_value='55',
            description='Encoder ticks per wheel revolution used only for odometry.'),
        DeclareLaunchArgument(
            'odom_tf_time_offset',
            default_value='0.0',
            description='Time offset in seconds for odom TF stamp. Keep 0.0 for real-time Nav2/AMCL.'),
        DeclareLaunchArgument(
            'odom_publish_rate',
            default_value='20.0',
            description='Rate in Hz for publishing /odom and odom->base_footprint TF.'),
        DeclareLaunchArgument('debug_motor_serial', default_value='false'),
        DeclareLaunchArgument('publish_odom_tf', default_value='true'),
        DeclareLaunchArgument(
            'motor_cmd_scale',
            default_value='10.0',
            description='Final scale applied to wheel RPM commands before sending them to the motor driver.'),
        DeclareLaunchArgument(
            'left_motor_cmd_scale',
            default_value='1.00',
            description='Left wheel trim. Lower this if the robot drifts right while commanded straight.'),
        DeclareLaunchArgument(
            'right_motor_cmd_scale',
            default_value='1.00',
            description='Right wheel trim. Lower this if the robot drifts left while commanded straight.'),
        DeclareLaunchArgument(
            'use_rpm_odom_fallback',
            default_value='false',
            description='Integrate odom from measured RPM when encoder position ticks are not changing.'),
        DeclareLaunchArgument(
            'rpm_odom_min_abs',
            default_value='1.0',
            description='Minimum absolute measured wheel RPM to enable RPM odom fallback.'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
            }],
            output='screen',
        ),

        Node(
            package='md_controller',
            executable='md_controller',
            name='md_controller_node',
            condition=IfCondition(use_motor),
            parameters=[{
                'MDUI': 184,
                'MDT': 183,
                'Port': motor_port,
                'Baudrate': ParameterValue(motor_baudrate, value_type=int),
                'ID': 1,
                'GearRatio': 25,
                'poles': 8,
                'odom_encoder_ppr': ParameterValue(odom_encoder_ppr, value_type=int),
                'wheel_radius': 0.065,
                'wheel_base': 0.288,
                'angular_cmd_scale': ParameterValue(angular_cmd_scale, value_type=float),
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
                'odom_tf_time_offset': ParameterValue(odom_tf_time_offset, value_type=float),
                'odom_publish_rate': ParameterValue(odom_publish_rate, value_type=float),
                'debug_serial': ParameterValue(debug_motor_serial, value_type=bool),
                'publish_tf': ParameterValue(publish_odom_tf, value_type=bool),
                'max_wheel_delta_per_update': 0.20,
                'motor_cmd_scale': ParameterValue(motor_cmd_scale, value_type=float),
                'left_motor_cmd_scale': ParameterValue(left_motor_cmd_scale, value_type=float),
                'right_motor_cmd_scale': ParameterValue(right_motor_cmd_scale, value_type=float),
                'use_rpm_odom_fallback': ParameterValue(use_rpm_odom_fallback, value_type=bool),
                'rpm_odom_min_abs': ParameterValue(rpm_odom_min_abs, value_type=float),
            }],
            output='screen',
        ),

        Node(
            package='sllidar_ros2',
            executable='sllidar_node',
            name='sllidar_node',
            condition=IfCondition(use_lidar),
            parameters=[{
                'channel_type': 'serial',
                'serial_port': lidar_port,
                'serial_baudrate': ParameterValue(lidar_baudrate, value_type=int),
                'frame_id': 'laser',
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
                'inverted': False,
                'angle_compensate': True,
                'scan_mode': 'Standard',
            }],
            output='screen',
        ),

        Node(
            package='wit_imu_driver',
            executable='wit_imu_node',
            name='wit_imu_node',
            namespace='imu',
            condition=IfCondition(use_imu),
            parameters=[{
                'device': imu_port,
                'baud': ParameterValue(imu_baudrate, value_type=int),
                'frame_id': 'imu_link',
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
                'gravity': 9.80665,
            }],
            output='screen',
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(astra_launch_path),
            condition=IfCondition(use_camera),
            launch_arguments={
                'camera_name': 'camera',
                'enable_color': 'true',
                'enable_depth': 'true',
                'enable_point_cloud': 'true',
                'enable_colored_point_cloud': 'false',
                'depth_registration': 'false',
                'color_width': '640',
                'color_height': '480',
                'color_fps': '10',
                'depth_width': '640',
                'depth_height': '480',
                'depth_fps': '10',
            }.items(),
        ),
    ])
