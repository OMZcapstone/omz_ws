#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanVisualFilter(Node):
    def __init__(self):
        super().__init__('scan_visual_filter')
        self.declare_parameter('input_topic', '/scan')
        self.declare_parameter('output_topic', '/scan_visual')
        self.declare_parameter('max_range_margin', 0.2)
        self.declare_parameter('max_display_range', 8.0)

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        self.max_range_margin = float(self.get_parameter('max_range_margin').value)
        self.max_display_range = float(self.get_parameter('max_display_range').value)

        self.publisher = self.create_publisher(LaserScan, output_topic, 10)
        self.subscription = self.create_subscription(LaserScan, input_topic, self.callback, 10)

    def callback(self, msg):
        filtered = LaserScan()
        filtered.header = msg.header
        filtered.angle_min = msg.angle_min
        filtered.angle_max = msg.angle_max
        filtered.angle_increment = msg.angle_increment
        filtered.time_increment = msg.time_increment
        filtered.scan_time = msg.scan_time
        filtered.range_min = msg.range_min
        filtered.range_max = min(msg.range_max, self.max_display_range)
        filtered.intensities = list(msg.intensities)

        cutoff = min(msg.range_max - self.max_range_margin, self.max_display_range)
        ranges = []
        for value in msg.ranges:
            if not math.isfinite(value) or value <= msg.range_min or value >= cutoff:
                ranges.append(float('inf'))
            else:
                ranges.append(value)
        filtered.ranges = ranges
        self.publisher.publish(filtered)


def main():
    rclpy.init()
    node = ScanVisualFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
