import json
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String


PERSON_CLASS_IDS = {0}
VEHICLE_CLASS_IDS = {2, 3, 5, 7}
DEFAULT_CLASS_IDS = sorted(PERSON_CLASS_IDS | VEHICLE_CLASS_IDS)
CLASS_COLORS = {
    'person': (40, 210, 255),
    'vehicle': (20, 220, 20),
}


class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__('yolo_detector_node')

        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('annotated_image_topic', '/yolo/image')
        self.declare_parameter('detections_topic', '/yolo/detections')
        self.declare_parameter('model', 'models/yolov8n.pt')
        self.declare_parameter('confidence', 0.45)
        self.declare_parameter('iou', 0.45)
        self.declare_parameter('image_size', 640)
        self.declare_parameter('max_det', 50)
        self.declare_parameter('class_ids', DEFAULT_CLASS_IDS)
        self.declare_parameter('publish_annotated_image', True)
        self.declare_parameter('process_every_n', 1)

        self.image_topic = self.get_parameter('image_topic').value
        self.annotated_image_topic = self.get_parameter('annotated_image_topic').value
        self.detections_topic = self.get_parameter('detections_topic').value
        self.confidence = float(self.get_parameter('confidence').value)
        self.iou = float(self.get_parameter('iou').value)
        self.image_size = int(self.get_parameter('image_size').value)
        self.max_det = int(self.get_parameter('max_det').value)
        self.class_ids = [int(item) for item in self.get_parameter('class_ids').value]
        self.publish_annotated_image = bool(
            self.get_parameter('publish_annotated_image').value)
        self.process_every_n = max(1, int(self.get_parameter('process_every_n').value))

        model_name = self.get_parameter('model').value
        self.model = self._load_model(model_name)
        self.bridge = CvBridge()
        self.frame_count = 0

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.image_sub = self.create_subscription(
            Image, self.image_topic, self.image_callback, qos)
        self.detections_pub = self.create_publisher(String, self.detections_topic, 10)
        self.image_pub = None
        if self.publish_annotated_image:
            self.image_pub = self.create_publisher(Image, self.annotated_image_topic, 10)

        self.get_logger().info(
            f'YOLO detector ready: model={model_name}, image_topic={self.image_topic}, '
            f'classes={self.class_ids}')

    def _load_model(self, model_name):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                'ultralytics is not installed. Install it with: '
                'python3 -m pip install ultralytics') from exc

        return YOLO(model_name)

    def image_callback(self, msg):
        self.frame_count += 1
        if self.frame_count % self.process_every_n != 0:
            return

        started = time.time()
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'Failed to convert image: {exc}')
            return

        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence,
                iou=self.iou,
                imgsz=self.image_size,
                classes=self.class_ids,
                max_det=self.max_det,
                verbose=False,
            )
        except Exception as exc:
            self.get_logger().error(f'YOLO inference failed: {exc}')
            return

        result = results[0]
        detections = self._to_detection_list(result)
        payload = {
            'header': {
                'stamp': {
                    'sec': int(msg.header.stamp.sec),
                    'nanosec': int(msg.header.stamp.nanosec),
                },
                'frame_id': msg.header.frame_id,
            },
            'model': str(self.get_parameter('model').value),
            'inference_ms': round((time.time() - started) * 1000.0, 2),
            'detections': detections,
        }
        self.detections_pub.publish(String(data=json.dumps(payload)))

        if self.image_pub is not None:
            annotated = self._draw_detections(frame.copy(), detections)
            annotated_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            annotated_msg.header = msg.header
            self.image_pub.publish(annotated_msg)

    def _to_detection_list(self, result):
        detections = []
        names = result.names

        if result.boxes is None:
            return detections

        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            detections.append({
                'class_id': cls_id,
                'class_name': names.get(cls_id, str(cls_id)),
                'category': self._category_for_class(cls_id),
                'confidence': round(confidence, 4),
                'bbox': {
                    'xmin': round(x1, 2),
                    'ymin': round(y1, 2),
                    'xmax': round(x2, 2),
                    'ymax': round(y2, 2),
                    'width': round(x2 - x1, 2),
                    'height': round(y2 - y1, 2),
                    'center_x': round((x1 + x2) / 2.0, 2),
                    'center_y': round((y1 + y2) / 2.0, 2),
                },
            })

        return detections

    def _category_for_class(self, cls_id):
        if cls_id in PERSON_CLASS_IDS:
            return 'person'
        if cls_id in VEHICLE_CLASS_IDS:
            return 'vehicle'
        return 'other'

    def _draw_detections(self, image, detections):
        for det in detections:
            bbox = det['bbox']
            x1 = int(bbox['xmin'])
            y1 = int(bbox['ymin'])
            x2 = int(bbox['xmax'])
            y2 = int(bbox['ymax'])
            category = det.get('category', 'other')
            color = CLASS_COLORS.get(category, (20, 220, 20))
            label = f"{category}:{det['class_name']} {det['confidence']:.2f}"

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                image,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )

        return image


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = YoloDetectorNode()
        rclpy.spin(node)
    except RuntimeError as exc:
        if node is not None:
            node.get_logger().fatal(str(exc))
        else:
            print(str(exc))
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
