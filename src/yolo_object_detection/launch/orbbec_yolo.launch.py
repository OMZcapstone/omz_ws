from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera_model = LaunchConfiguration('camera_model')
    camera_name = LaunchConfiguration('camera_name')
    model = LaunchConfiguration('model')
    confidence = LaunchConfiguration('confidence')
    process_every_n = LaunchConfiguration('process_every_n')
    image_topic = LaunchConfiguration('image_topic')
    show_preview = LaunchConfiguration('show_preview')

    orbbec_launch = PathJoinSubstitution([
        FindPackageShare('orbbec_camera'),
        'launch',
        'orbbec_camera.launch.py',
    ])

    return LaunchDescription([
        DeclareLaunchArgument('camera_model', default_value='gemini330_series'),
        DeclareLaunchArgument('camera_name', default_value='camera'),
        DeclareLaunchArgument('image_topic', default_value='/camera/color/image_raw'),
        DeclareLaunchArgument('model', default_value='models/yolov8n.pt'),
        DeclareLaunchArgument('confidence', default_value='0.45'),
        DeclareLaunchArgument('process_every_n', default_value='1'),
        DeclareLaunchArgument(
            'show_preview',
            default_value='true',
            description='Open an OpenCV preview window for color, depth, and YOLO output'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(orbbec_launch),
            launch_arguments={
                'camera_model': camera_model,
                'camera_name': camera_name,
                'enable_color': 'true',
                'enable_depth': 'true',
            }.items(),
        ),
        Node(
            package='yolo_object_detection',
            executable='yolo_detector_node',
            name='yolo_detector_node',
            output='screen',
            parameters=[{
                'image_topic': image_topic,
                'model': model,
                'confidence': ParameterValue(confidence, value_type=float),
                'process_every_n': ParameterValue(process_every_n, value_type=int),
                'class_ids': [0, 2, 3, 5, 7],
            }],
        ),
        Node(
            package='yolo_object_detection',
            executable='camera_preview_node',
            name='camera_preview_node',
            output='screen',
            condition=IfCondition(show_preview),
            parameters=[{
                'color_topic': '/camera/color/image_raw',
                'depth_topic': '/camera/depth/image_raw',
                'yolo_topic': '/yolo/image',
            }],
        ),
    ])
