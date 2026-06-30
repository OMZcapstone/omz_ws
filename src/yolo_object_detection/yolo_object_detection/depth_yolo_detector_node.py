import json
import math
import time

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Header, String
from visualization_msgs.msg import Marker, MarkerArray


PERSON_CLASS_IDS = {0}
VEHICLE_CLASS_IDS = {2, 3, 5, 7}
DEFAULT_CLASS_IDS = sorted(PERSON_CLASS_IDS | VEHICLE_CLASS_IDS)
CLASS_COLORS = {
    'person': (40, 210, 255),
    'vehicle': (20, 220, 20),
    'other': (200, 200, 200),
}


class DepthYoloDetectorNode(Node):
    def __init__(self):
        super().__init__('depth_yolo_detector_node')

        self.declare_parameter('image_topic', '/camera/color/image_raw')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/color/camera_info')
        self.declare_parameter('annotated_image_topic', '/yolo_depth/image')
        self.declare_parameter('detections_topic', '/yolo_depth/detections')
        self.declare_parameter('marker_topic', '/yolo_depth/markers')
        self.declare_parameter('model', 'models/yolov8n.pt')
        self.declare_parameter('confidence', 0.45)
        self.declare_parameter('iou', 0.45)
        self.declare_parameter('image_size', 640)
        self.declare_parameter('max_det', 50)
        self.declare_parameter('class_ids', DEFAULT_CLASS_IDS)
        self.declare_parameter('publish_annotated_image', True)
        self.declare_parameter('process_every_n', 1)
        self.declare_parameter('depth_window', 7)
        self.declare_parameter('depth_scale', 0.001)
        self.declare_parameter('max_depth_age_sec', 0.5)
        self.declare_parameter('min_depth_m', 0.2)
        self.declare_parameter('max_depth_m', 8.0)

        self.image_topic = self.get_parameter('image_topic').value
        self.depth_topic = self.get_parameter('depth_topic').value
        self.camera_info_topic = self.get_parameter('camera_info_topic').value
        self.annotated_image_topic = self.get_parameter('annotated_image_topic').value
        self.detections_topic = self.get_parameter('detections_topic').value
        self.marker_topic = self.get_parameter('marker_topic').value
        self.confidence = float(self.get_parameter('confidence').value)
        self.iou = float(self.get_parameter('iou').value)
        self.image_size = int(self.get_parameter('image_size').value)
        self.max_det = int(self.get_parameter('max_det').value)
        self.class_ids = [int(item) for item in self.get_parameter('class_ids').value]
        self.publish_annotated_image = bool(
            self.get_parameter('publish_annotated_image').value)
        self.process_every_n = max(1, int(self.get_parameter('process_every_n').value))
        self.depth_window = max(1, int(self.get_parameter('depth_window').value))
        self.depth_scale = float(self.get_parameter('depth_scale').value)
        self.max_depth_age_sec = float(self.get_parameter('max_depth_age_sec').value)
        self.min_depth_m = float(self.get_parameter('min_depth_m').value)
        self.max_depth_m = float(self.get_parameter('max_depth_m').value)

        model_name = self.get_parameter('model').value
        self.model = self._load_model(model_name)
        self.bridge = CvBridge()
        self.frame_count = 0
        self.latest_depth = None
        self.latest_depth_header = None
        self.latest_depth_time = None
        self.camera_info = None

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.depth_sub = self.create_subscription(
            Image, self.depth_topic, self.depth_callback, qos)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, self.camera_info_topic, self.camera_info_callback, qos)
        self.image_sub = self.create_subscription(
            Image, self.image_topic, self.image_callback, qos)
        self.detections_pub = self.create_publisher(String, self.detections_topic, 10)
        self.markers_pub = self.create_publisher(MarkerArray, self.marker_topic, 10)
        self.image_pub = None
        if self.publish_annotated_image:
            self.image_pub = self.create_publisher(Image, self.annotated_image_topic, 10)

        self.get_logger().info(
            f'Depth YOLO detector ready: model={model_name}, '
            f'image_topic={self.image_topic}, depth_topic={self.depth_topic}, '
            f'camera_info_topic={self.camera_info_topic}, '
            f'classes={self.class_ids}')

    def _load_model(self, model_name):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                'ultralytics is not installed. Install it with: '
                'python3 -m pip install ultralytics') from exc

        return YOLO(model_name)

    def depth_callback(self, msg):
        try:
            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        except Exception as exc:
            self.get_logger().error(f'Failed to convert depth image: {exc}')
            return

        self.latest_depth = np.asarray(depth)
        self.latest_depth_header = msg.header
        self.latest_depth_time = self._stamp_to_float(msg.header.stamp)

    def camera_info_callback(self, msg):
        self.camera_info = msg

    def image_callback(self, msg):
        self.frame_count += 1
        if self.frame_count % self.process_every_n != 0:
            return

        started = time.time()
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'Failed to convert color image: {exc}')
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

        image_time = self._stamp_to_float(msg.header.stamp)
        depth_age = None
        if self.latest_depth_time is not None:
            depth_age = abs(image_time - self.latest_depth_time)

        detections = self._to_detection_list(results[0], frame.shape, depth_age)
        payload = {
            'header': {
                'stamp': {
                    'sec': int(msg.header.stamp.sec),
                    'nanosec': int(msg.header.stamp.nanosec),
                },
                'frame_id': msg.header.frame_id,
            },
            'depth_header': self._header_to_dict(self.latest_depth_header),
            'model': str(self.get_parameter('model').value),
            'inference_ms': round((time.time() - started) * 1000.0, 2),
            'depth_age_sec': None if depth_age is None else round(depth_age, 4),
            'detections': detections,
        }
        self.detections_pub.publish(String(data=json.dumps(payload)))
        self.markers_pub.publish(self._to_marker_array(msg.header, detections))

        if self.image_pub is not None:
            annotated = self._draw_detections(frame.copy(), detections)
            annotated_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            annotated_msg.header = msg.header
            self.image_pub.publish(annotated_msg)

    def _to_detection_list(self, result, image_shape, depth_age):
        detections = []
        names = result.names

        if result.boxes is None:
            return detections

        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            depth_m = self._depth_at(center_x, center_y, image_shape, depth_age)
            position = self._project_to_3d(center_x, center_y, depth_m)

            detections.append({
                'class_id': cls_id,
                'class_name': names.get(cls_id, str(cls_id)),
                'category': self._category_for_class(cls_id),
                'confidence': round(confidence, 4),
                'depth_m': None if depth_m is None else round(depth_m, 3),
                'position': position,
                'bbox': {
                    'xmin': round(x1, 2),
                    'ymin': round(y1, 2),
                    'xmax': round(x2, 2),
                    'ymax': round(y2, 2),
                    'width': round(x2 - x1, 2),
                    'height': round(y2 - y1, 2),
                    'center_x': round(center_x, 2),
                    'center_y': round(center_y, 2),
                },
            })

        return detections

    def _depth_at(self, center_x, center_y, image_shape, depth_age):
        if self.latest_depth is None:
            return None
        if depth_age is None or depth_age > self.max_depth_age_sec:
            return None

        depth = self.latest_depth
        image_h, image_w = image_shape[:2]
        depth_h, depth_w = depth.shape[:2]

        depth_x = int(round(center_x * depth_w / image_w))
        depth_y = int(round(center_y * depth_h / image_h))
        half = self.depth_window // 2

        x1 = max(0, depth_x - half)
        y1 = max(0, depth_y - half)
        x2 = min(depth_w, depth_x + half + 1)
        y2 = min(depth_h, depth_y + half + 1)
        patch = depth[y1:y2, x1:x2].astype(np.float32)

        if patch.size == 0:
            return None

        if np.issubdtype(depth.dtype, np.floating):
            values_m = patch
        else:
            values_m = patch * self.depth_scale

        valid = values_m[np.isfinite(values_m)]
        valid = valid[(valid >= self.min_depth_m) & (valid <= self.max_depth_m)]
        if valid.size == 0:
            return None

        depth_m = float(np.median(valid))
        if not math.isfinite(depth_m):
            return None
        return depth_m

    def _project_to_3d(self, center_x, center_y, depth_m):
        if depth_m is None or self.camera_info is None:
            return None

        fx = float(self.camera_info.k[0])
        fy = float(self.camera_info.k[4])
        cx = float(self.camera_info.k[2])
        cy = float(self.camera_info.k[5])
        if fx == 0.0 or fy == 0.0:
            return None

        x = (center_x - cx) * depth_m / fx
        y = (center_y - cy) * depth_m / fy
        z = depth_m
        return {
            'frame_id': self.camera_info.header.frame_id,
            'x': round(x, 3),
            'y': round(y, 3),
            'z': round(z, 3),
        }

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
            color = CLASS_COLORS.get(category, CLASS_COLORS['other'])
            depth_text = 'depth:--'
            if det.get('depth_m') is not None:
                depth_text = f"{det['depth_m']:.2f}m"
            label = (
                f"{category}:{det['class_name']} "
                f"{det['confidence']:.2f} {depth_text}"
            )

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

    def _to_marker_array(self, image_header, detections):
        markers = MarkerArray()

        clear = Marker()
        clear.header = image_header
        clear.ns = 'yolo_depth'
        clear.action = Marker.DELETEALL
        markers.markers.append(clear)

        marker_id = 0
        for det in detections:
            position = det.get('position')
            if position is None:
                continue

            header = Header()
            header.stamp = image_header.stamp
            header.frame_id = position['frame_id']
            color = self._marker_color(det.get('category', 'other'))

            sphere = Marker()
            sphere.header = header
            sphere.ns = 'yolo_depth_objects'
            sphere.id = marker_id
            marker_id += 1
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = float(position['x'])
            sphere.pose.position.y = float(position['y'])
            sphere.pose.position.z = float(position['z'])
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = 0.18
            sphere.scale.y = 0.18
            sphere.scale.z = 0.18
            sphere.color.r = color[0]
            sphere.color.g = color[1]
            sphere.color.b = color[2]
            sphere.color.a = 0.9
            sphere.lifetime.sec = 1
            markers.markers.append(sphere)

            text = Marker()
            text.header = header
            text.ns = 'yolo_depth_labels'
            text.id = marker_id
            marker_id += 1
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position.x = float(position['x'])
            text.pose.position.y = float(position['y'])
            text.pose.position.z = float(position['z']) + 0.25
            text.pose.orientation.w = 1.0
            text.scale.z = 0.18
            text.color.r = color[0]
            text.color.g = color[1]
            text.color.b = color[2]
            text.color.a = 1.0
            text.text = (
                f"{det['class_name']} {det['confidence']:.2f} "
                f"{det['depth_m']:.2f}m"
            )
            text.lifetime.sec = 1
            markers.markers.append(text)

        return markers

    def _marker_color(self, category):
        if category == 'person':
            return (1.0, 0.82, 0.1)
        if category == 'vehicle':
            return (0.1, 0.9, 0.2)
        return (0.75, 0.75, 0.75)

    def _stamp_to_float(self, stamp):
        return float(stamp.sec) + float(stamp.nanosec) * 1e-9

    def _header_to_dict(self, header):
        if header is None:
            return None
        return {
            'stamp': {
                'sec': int(header.stamp.sec),
                'nanosec': int(header.stamp.nanosec),
            },
            'frame_id': header.frame_id,
        }


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = DepthYoloDetectorNode()
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
