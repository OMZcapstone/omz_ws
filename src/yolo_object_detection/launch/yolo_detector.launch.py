from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    image_topic = LaunchConfiguration('image_topic')
    annotated_image_topic = LaunchConfiguration('annotated_image_topic')
    detections_topic = LaunchConfiguration('detections_topic')
    model = LaunchConfiguration('model')
    confidence = LaunchConfiguration('confidence')
    iou = LaunchConfiguration('iou')
    image_size = LaunchConfiguration('image_size')
    process_every_n = LaunchConfiguration('process_every_n')

    return LaunchDescription([
        DeclareLaunchArgument(
            'image_topic',
            default_value='/camera/color/image_raw',
            description='RGB image topic from the depth camera'),
        DeclareLaunchArgument(
            'annotated_image_topic',
            default_value='/yolo/image',
            description='Annotated image output topic'),
        DeclareLaunchArgument(
            'detections_topic',
            default_value='/yolo/detections',
            description='JSON detection output topic'),
        DeclareLaunchArgument(
            'model',
            default_value='models/yolov8n.pt',
            description='Ultralytics YOLO model path or model name'),
        DeclareLaunchArgument(
            'confidence',
            default_value='0.45',
            description='Minimum confidence threshold'),
        DeclareLaunchArgument(
            'iou',
            default_value='0.45',
            description='NMS IOU threshold'),
        DeclareLaunchArgument(
            'image_size',
            default_value='640',
            description='YOLO inference image size'),
        DeclareLaunchArgument(
            'process_every_n',
            default_value='1',
            description='Process one out of every N frames'),
        Node(
            package='yolo_object_detection',
            executable='yolo_detector_node',
            name='yolo_detector_node',
            output='screen',
            parameters=[{
                'image_topic': image_topic,
                'annotated_image_topic': annotated_image_topic,
                'detections_topic': detections_topic,
                'model': model,
                'confidence': ParameterValue(confidence, value_type=float),
                'iou': ParameterValue(iou, value_type=float),
                'image_size': ParameterValue(image_size, value_type=int),
                'process_every_n': ParameterValue(process_every_n, value_type=int),
                'class_ids': [0, 2, 3, 5, 7],
            }],
        ),
    ])
