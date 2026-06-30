import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():

  # Set the path to this package.
  pkg_share = FindPackageShare(package='md_controller').find('md_controller')

  # Set the path to the RViz configuration settings
  default_rviz_config_path = os.path.join(pkg_share, 'rviz/md.rviz')

  ########### YOU DO NOT NEED TO CHANGE ANYTHING BELOW THIS LINE ##############  
  # Launch configuration variables specific to simulation
  rviz_config_file = LaunchConfiguration('rviz_config_file')
  use_rviz = LaunchConfiguration('use_rviz')
  use_sim_time = LaunchConfiguration('use_sim_time')
  port = LaunchConfiguration('port')
  baudrate = LaunchConfiguration('baudrate')
  id1 = LaunchConfiguration('id1')
  gear_ratio = LaunchConfiguration('gear_ratio')
  poles = LaunchConfiguration('poles')
  wheel_radius = LaunchConfiguration('wheel_radius')
  wheel_base = LaunchConfiguration('wheel_base')
  angular_cmd_scale = LaunchConfiguration('angular_cmd_scale')
  odom_encoder_ppr = LaunchConfiguration('odom_encoder_ppr')
  odom_publish_rate = LaunchConfiguration('odom_publish_rate')
  odom_tf_time_offset = LaunchConfiguration('odom_tf_time_offset')
  publish_tf = LaunchConfiguration('publish_tf')
  motor_cmd_scale = LaunchConfiguration('motor_cmd_scale')
  left_motor_cmd_scale = LaunchConfiguration('left_motor_cmd_scale')
  right_motor_cmd_scale = LaunchConfiguration('right_motor_cmd_scale')
  use_rpm_odom_fallback = LaunchConfiguration('use_rpm_odom_fallback')
  rpm_odom_min_abs = LaunchConfiguration('rpm_odom_min_abs')
  debug_serial = LaunchConfiguration('debug_serial')
    
  declare_rviz_config_file_cmd = DeclareLaunchArgument(
    name='rviz_config_file',
    default_value=default_rviz_config_path,
    description='Full path to the RVIZ config file to use')

  declare_use_rviz_cmd = DeclareLaunchArgument(
    name='use_rviz',
    default_value='False',
    description='Whether to start RVIZ')

  declare_use_sim_time_cmd = DeclareLaunchArgument(
    name='use_sim_time',
    default_value='False',
    description='Use simulation clock. Keep false on the real robot.')

  declare_port_cmd = DeclareLaunchArgument(
    name='port',
    default_value='/dev/ttyUSB0',
    description='Serial port for the MD motor driver')

  declare_baudrate_cmd = DeclareLaunchArgument(
    name='baudrate',
    default_value='19200',
    description='Serial baudrate for the MD motor driver')

  declare_id1_cmd = DeclareLaunchArgument(
    name='id1',
    default_value='1',
    description='First motor ID')

  declare_gear_ratio_cmd = DeclareLaunchArgument(
    name='gear_ratio',
    default_value='25',
    description='Motor gear ratio')

  declare_poles_cmd = DeclareLaunchArgument(
    name='poles',
    default_value='8',
    description='Motor pole count')

  declare_wheel_radius_cmd = DeclareLaunchArgument(
    name='wheel_radius',
    default_value='0.065',
    description='Wheel radius in meters')

  declare_wheel_base_cmd = DeclareLaunchArgument(
    name='wheel_base',
    default_value='0.288',
    description='Distance between left and right wheel centers in meters')

  declare_angular_cmd_scale_cmd = DeclareLaunchArgument(
    name='angular_cmd_scale',
    default_value='0.6',
    description='Scale applied only to /cmd_vel angular.z before sending wheel RPM commands')

  declare_odom_encoder_ppr_cmd = DeclareLaunchArgument(
    name='odom_encoder_ppr',
    default_value='55',
    description='Encoder ticks per wheel revolution used for odometry')

  declare_odom_publish_rate_cmd = DeclareLaunchArgument(
    name='odom_publish_rate',
    default_value='20.0',
    description='Rate in Hz for /odom and /joint_states')

  declare_odom_tf_time_offset_cmd = DeclareLaunchArgument(
    name='odom_tf_time_offset',
    default_value='0.0',
    description='Optional time offset in seconds for odom TF stamp')

  declare_publish_tf_cmd = DeclareLaunchArgument(
    name='publish_tf',
    default_value='True',
    description='Whether to publish odom -> base_footprint TF')

  declare_debug_serial_cmd = DeclareLaunchArgument(
    name='debug_serial',
    default_value='False',
    description='Print raw serial bytes and decoded MD packets')

  declare_motor_cmd_scale_cmd = DeclareLaunchArgument(
    name='motor_cmd_scale',
    default_value='10.0',
    description='Final scale applied to wheel RPM commands before sending them to the motor driver')

  declare_left_motor_cmd_scale_cmd = DeclareLaunchArgument(
    name='left_motor_cmd_scale',
    default_value='1.0',
    description='Left wheel command trim')

  declare_right_motor_cmd_scale_cmd = DeclareLaunchArgument(
    name='right_motor_cmd_scale',
    default_value='1.0',
    description='Right wheel command trim')

  declare_use_rpm_odom_fallback_cmd = DeclareLaunchArgument(
    name='use_rpm_odom_fallback',
    default_value='False',
    description='Integrate odom from measured RPM when encoder position ticks are not changing')

  declare_rpm_odom_min_abs_cmd = DeclareLaunchArgument(
    name='rpm_odom_min_abs',
    default_value='1.0',
    description='Minimum absolute measured wheel RPM to enable RPM odom fallback')
  
  # Launch motor driver controller
  md_controller_cmd = Node(
    package='md_controller',
    executable='md_controller',
    parameters=[{
      "MDUI":184,
      "MDT":183,
      "Port":port,
      "Baudrate":ParameterValue(baudrate, value_type=int),
      "ID":ParameterValue(id1, value_type=int),
      "GearRatio":ParameterValue(gear_ratio, value_type=int),
      "poles":ParameterValue(poles, value_type=int),
      "odom_encoder_ppr": ParameterValue(odom_encoder_ppr, value_type=int),
      "wheel_radius": ParameterValue(wheel_radius, value_type=float),
      "wheel_base": ParameterValue(wheel_base, value_type=float),
      "angular_cmd_scale": ParameterValue(angular_cmd_scale, value_type=float),
      "odom_publish_rate": ParameterValue(odom_publish_rate, value_type=float),
      "odom_tf_time_offset": ParameterValue(odom_tf_time_offset, value_type=float),
      "publish_tf": ParameterValue(publish_tf, value_type=bool),
      "motor_cmd_scale": ParameterValue(motor_cmd_scale, value_type=float),
      "left_motor_cmd_scale": ParameterValue(left_motor_cmd_scale, value_type=float),
      "right_motor_cmd_scale": ParameterValue(right_motor_cmd_scale, value_type=float),
      "use_rpm_odom_fallback": ParameterValue(use_rpm_odom_fallback, value_type=bool),
      "rpm_odom_min_abs": ParameterValue(rpm_odom_min_abs, value_type=float),
      "debug_serial": ParameterValue(debug_serial, value_type=bool),
      "use_sim_time": ParameterValue(use_sim_time, value_type=bool)
    }],
    output='screen'
  )

  # Launch RViz
  start_rviz_cmd = Node(
    condition=IfCondition(use_rviz),
    package='rviz2',
    executable='rviz2',
    name='rviz2',
    parameters=[{'use_sim_time': ParameterValue(use_sim_time, value_type=bool)}],
    output='screen',
    arguments=['-d', rviz_config_file])
  
  # Create the launch description and populate
  ld = LaunchDescription()

  # Declare the launch options
  ld.add_action(declare_rviz_config_file_cmd)
  ld.add_action(declare_use_rviz_cmd) 
  ld.add_action(declare_use_sim_time_cmd)
  ld.add_action(declare_port_cmd)
  ld.add_action(declare_baudrate_cmd)
  ld.add_action(declare_id1_cmd)
  ld.add_action(declare_gear_ratio_cmd)
  ld.add_action(declare_poles_cmd)
  ld.add_action(declare_wheel_radius_cmd)
  ld.add_action(declare_wheel_base_cmd)
  ld.add_action(declare_angular_cmd_scale_cmd)
  ld.add_action(declare_odom_encoder_ppr_cmd)
  ld.add_action(declare_odom_publish_rate_cmd)
  ld.add_action(declare_odom_tf_time_offset_cmd)
  ld.add_action(declare_publish_tf_cmd)
  ld.add_action(declare_motor_cmd_scale_cmd)
  ld.add_action(declare_left_motor_cmd_scale_cmd)
  ld.add_action(declare_right_motor_cmd_scale_cmd)
  ld.add_action(declare_use_rpm_odom_fallback_cmd)
  ld.add_action(declare_rpm_odom_min_abs_cmd)
  ld.add_action(declare_debug_serial_cmd)

  # Add any actions
  ld.add_action(md_controller_cmd)
  ld.add_action(start_rviz_cmd)

  return ld
