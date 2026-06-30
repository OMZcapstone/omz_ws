import os

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image


class CameraPreviewNode(Node):
    def __init__(self):
        super().__init__('camera_preview_node')

        self.declare_parameter('color_topic', '/camera/color/image_raw')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')
        self.declare_parameter('yolo_topic', '/yolo/image')
        self.declare_parameter('depth_max_m', 5.0)

        self._bridge = CvBridge()
        self._color = None
        self._depth = None
        self._yolo = None
        self._depth_max_m = max(0.1, float(self.get_parameter('depth_max_m').value))
        self._has_display = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.create_subscription(
            Image,
            self.get_parameter('color_topic').value,
            self._color_cb,
            qos,
        )
        self.create_subscription(
            Image,
            self.get_parameter('depth_topic').value,
            self._depth_cb,
            qos,
        )
        self.create_subscription(
            Image,
            self.get_parameter('yolo_topic').value,
            self._yolo_cb,
            qos,
        )
        self.create_timer(0.05, self._show)

        if self._has_display:
            self.get_logger().info('Camera preview ready. Press q in the preview window to close it.')
        else:
            self.get_logger().warn(
                'No GUI display found. Use rqt_image_view on a desktop, or enable X/Wayland forwarding.'
            )

    def _color_cb(self, msg):
        self._color = self._image_to_bgr(msg)

    def _depth_cb(self, msg):
        self._depth = self._depth_to_bgr(msg)

    def _yolo_cb(self, msg):
        self._yolo = self._image_to_bgr(msg)

    def _image_to_bgr(self, msg):
        try:
            return self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().warning(f'Image conversion failed: {exc}')
            return None

    def _depth_to_bgr(self, msg):
        try:
            depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        except Exception as exc:
            self.get_logger().warning(f'Depth conversion failed: {exc}')
            return None

        depth = np.asarray(depth)
        if depth.dtype == np.uint16:
            depth_m = depth.astype(np.float32) / 1000.0
        elif depth.dtype == np.float32 or depth.dtype == np.float64:
            depth_m = depth.astype(np.float32)
        else:
            depth_m = depth.astype(np.float32)

        valid = np.isfinite(depth_m) & (depth_m > 0.0)
        clipped = np.zeros_like(depth_m, dtype=np.float32)
        clipped[valid] = np.clip(depth_m[valid], 0.0, self._depth_max_m)
        normalized = (255.0 - (clipped / self._depth_max_m * 255.0)).astype(np.uint8)
        normalized[~valid] = 0
        return cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)

    def _show(self):
        if not self._has_display:
            return

        panels = []
        if self._color is not None:
            panels.append(self._with_label(self._resize(self._color), 'color'))
        if self._depth is not None:
            panels.append(self._with_label(self._resize(self._depth), 'depth'))
        if self._yolo is not None:
            panels.append(self._with_label(self._resize(self._yolo), 'yolo person / vehicle'))

        if not panels:
            return

        canvas = np.hstack(panels)
        cv2.imshow('depth camera + YOLOv8n preview', canvas)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            rclpy.shutdown()

    def _resize(self, image):
        return cv2.resize(image, (426, 240), interpolation=cv2.INTER_AREA)

    def _with_label(self, image, label):
        out = image.copy()
        cv2.rectangle(out, (0, 0), (out.shape[1], 28), (0, 0, 0), -1)
        cv2.putText(
            out,
            label,
            (8, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        return out


def main(args=None):
    rclpy.init(args=args)
    node = CameraPreviewNode()
    try:
        rclpy.spin(node)
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
