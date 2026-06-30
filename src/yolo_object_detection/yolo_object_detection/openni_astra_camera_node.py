from pathlib import Path

from cv_bridge import CvBridge
import numpy as np
from openni import openni2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


DEFAULT_OPENNI2_PATH = (
    '/home/omz/omz_ws/external/depth_camera/AstraSDK-v2.1.3-Linux-arm/'
    'AstraSDK-v2.1.3-94bca0f52e-20210611T023312Z-Linux-aarch64/'
    'lib/Plugins/openni2'
)


class OpenniAstraCameraNode(Node):
    def __init__(self):
        super().__init__('openni_astra_camera_node')

        self.declare_parameter('openni2_path', DEFAULT_OPENNI2_PATH)
        self.declare_parameter('camera_name', 'camera')
        self.declare_parameter('frame_id', 'camera_color_optical_frame')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('fx', 525.0)
        self.declare_parameter('fy', 525.0)
        self.declare_parameter('cx', 319.5)
        self.declare_parameter('cy', 239.5)

        self.openni2_path = Path(self.get_parameter('openni2_path').value)
        self.camera_name = self.get_parameter('camera_name').value
        self.frame_id = self.get_parameter('frame_id').value
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = float(self.get_parameter('fps').value)
        self.fx = float(self.get_parameter('fx').value)
        self.fy = float(self.get_parameter('fy').value)
        self.cx = float(self.get_parameter('cx').value)
        self.cy = float(self.get_parameter('cy').value)

        self.bridge = CvBridge()
        self.device = None
        self.color_stream = None
        self.depth_stream = None

        prefix = f'/{self.camera_name}'
        self.color_pub = self.create_publisher(Image, f'{prefix}/color/image_raw', 10)
        self.depth_pub = self.create_publisher(Image, f'{prefix}/depth/image_raw', 10)
        self.color_info_pub = self.create_publisher(
            CameraInfo, f'{prefix}/color/camera_info', 10)
        self.depth_info_pub = self.create_publisher(
            CameraInfo, f'{prefix}/depth/camera_info', 10)

        self._open_device()
        period = 1.0 / max(self.fps, 1.0)
        self.timer = self.create_timer(period, self.publish_frames)

        self.get_logger().info(
            f'OpenNI Astra camera ready: color={prefix}/color/image_raw, '
            f'depth={prefix}/depth/image_raw, frame_id={self.frame_id}')

    def _open_device(self):
        if not self.openni2_path.exists():
            raise RuntimeError(f'OpenNI2 path does not exist: {self.openni2_path}')

        openni2.initialize(str(self.openni2_path))
        self.device = openni2.Device.open_any()
        self.color_stream = self.device.create_color_stream()
        self.depth_stream = self.device.create_depth_stream()
        self.color_stream.start()
        self.depth_stream.start()

    def publish_frames(self):
        try:
            color_frame = self.color_stream.read_frame()
            depth_frame = self.depth_stream.read_frame()
        except Exception as exc:
            self.get_logger().error(f'Failed to read Astra frame: {exc}')
            return

        stamp = self.get_clock().now().to_msg()

        color = np.frombuffer(
            color_frame.get_buffer_as_uint8(), dtype=np.uint8)
        color = color.reshape((self.height, self.width, 3))

        depth = np.frombuffer(
            depth_frame.get_buffer_as_uint16(), dtype=np.uint16)
        depth = depth.reshape((self.height, self.width))

        color_msg = self.bridge.cv2_to_imgmsg(color, encoding='rgb8')
        color_msg.header.stamp = stamp
        color_msg.header.frame_id = self.frame_id

        depth_msg = self.bridge.cv2_to_imgmsg(depth, encoding='16UC1')
        depth_msg.header.stamp = stamp
        depth_msg.header.frame_id = self.frame_id

        info_msg = self._camera_info(stamp)

        self.color_pub.publish(color_msg)
        self.depth_pub.publish(depth_msg)
        self.color_info_pub.publish(info_msg)
        self.depth_info_pub.publish(info_msg)

    def _camera_info(self, stamp):
        msg = CameraInfo()
        msg.header.stamp = stamp
        msg.header.frame_id = self.frame_id
        msg.width = self.width
        msg.height = self.height
        msg.distortion_model = 'plumb_bob'
        msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        msg.k = [
            self.fx, 0.0, self.cx,
            0.0, self.fy, self.cy,
            0.0, 0.0, 1.0,
        ]
        msg.r = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        ]
        msg.p = [
            self.fx, 0.0, self.cx, 0.0,
            0.0, self.fy, self.cy, 0.0,
            0.0, 0.0, 1.0, 0.0,
        ]
        return msg

    def destroy_node(self):
        for stream in (self.color_stream, self.depth_stream):
            if stream is not None:
                try:
                    stream.stop()
                except Exception:
                    pass
        try:
            openni2.unload()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = OpenniAstraCameraNode()
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
