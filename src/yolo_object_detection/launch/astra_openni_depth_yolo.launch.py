from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    image_topic = LaunchConfiguration('image_topic')
    depth_topic = LaunchConfiguration('depth_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    model = LaunchConfiguration('model')
    confidence = LaunchConfiguration('confidence')
    process_every_n = LaunchConfiguration('process_every_n')
    depth_window = LaunchConfiguration('depth_window')
    max_depth_age_sec = LaunchConfiguration('max_depth_age_sec')
    show_preview = LaunchConfiguration('show_preview')
    rviz = LaunchConfiguration('rviz')

    rviz_config = PathJoinSubstitution([
        FindPackageShare('yolo_object_detection'),
        'rviz',
        'yolo_depth.rviz',
    ])

    return LaunchDescription([
        DeclareLaunchArgument('image_topic', default_value='/camera/color/image_raw'),
        DeclareLaunchArgument('depth_topic', default_value='/camera/depth/image_raw'),
        DeclareLaunchArgument('camera_info_topic', default_value='/camera/color/camera_info'),
        DeclareLaunchArgument('model', default_value='models/yolov8n.pt'),
        DeclareLaunchArgument('confidence', default_value='0.45'),
        DeclareLaunchArgument('process_every_n', default_value='1'),
        DeclareLaunchArgument('depth_window', default_value='7'),
        DeclareLaunchArgument('max_depth_age_sec', default_value='0.5'),
        DeclareLaunchArgument('show_preview', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='false'),
        Node(
            package='yolo_object_detection',
            executable='openni_astra_camera_node',
            name='openni_astra_camera_node',
            output='screen',
        ),
        Node(
            package='yolo_object_detection',
            executable='depth_yolo_detector_node',
            name='depth_yolo_detector_node',
            output='screen',
            parameters=[{
                'image_topic': image_topic,
                'depth_topic': depth_topic,
                'camera_info_topic': camera_info_topic,
                'model': model,
                'confidence': ParameterValue(confidence, value_type=float),
                'process_every_n': ParameterValue(process_every_n, value_type=int),
                'depth_window': ParameterValue(depth_window, value_type=int),
                'max_depth_age_sec': ParameterValue(max_depth_age_sec, value_type=float),
                'class_ids': [0, 2, 3, 5, 7],
            }],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(rviz),
            arguments=['-d', rviz_config],
        ),
        Node(
            package='yolo_object_detection',
            executable='camera_preview_node',
            name='camera_preview_node',
            output='screen',
            condition=IfCondition(show_preview),
            parameters=[{
                'color_topic': image_topic,
                'depth_topic': depth_topic,
                'yolo_topic': '/yolo_depth/image',
            }],
        ),
    ])
