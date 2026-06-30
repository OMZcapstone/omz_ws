#!/usr/bin/env python3
import math
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def wrap_deg(angle):
    return (angle + 180.0) % 360.0 - 180.0


class YawCompare(Node):
    def __init__(self):
        super().__init__("yaw_compare")
        self.samples = {
            "wheel": None,
            "imu": None,
            "ekf": None,
        }
        self.zero = {}
        self.last_print = 0.0

        self.create_subscription(Odometry, "/odom", self.odom_cb, 20)
        self.create_subscription(Imu, "/imu/data_raw", self.imu_cb, 20)
        self.create_subscription(Odometry, "/odometry/filtered", self.ekf_cb, 20)
        self.timer = self.create_timer(0.25, self.print_table)

    def odom_cb(self, msg):
        self.set_sample("wheel", yaw_from_quat(msg.pose.pose.orientation), msg.header.stamp)

    def imu_cb(self, msg):
        self.set_sample("imu", yaw_from_quat(msg.orientation), msg.header.stamp)

    def ekf_cb(self, msg):
        self.set_sample("ekf", yaw_from_quat(msg.pose.pose.orientation), msg.header.stamp)

    def set_sample(self, name, yaw_rad, stamp):
        yaw_deg = math.degrees(yaw_rad)
        if name not in self.zero:
            self.zero[name] = yaw_deg
        stamp_sec = stamp.sec + stamp.nanosec * 1e-9
        self.samples[name] = {
            "yaw": wrap_deg(yaw_deg),
            "delta": wrap_deg(yaw_deg - self.zero[name]),
            "stamp": stamp_sec,
            "updated": time.monotonic(),
        }

    def print_table(self):
        now = time.monotonic()
        rows = []
        for name, label in (
            ("wheel", "wheel /odom"),
            ("imu", "imu   /imu/data_raw"),
            ("ekf", "ekf   /odometry/filtered"),
        ):
            sample = self.samples[name]
            if sample is None:
                rows.append((label, "waiting", "waiting", "-"))
                continue
            age = now - sample["updated"]
            rows.append((
                label,
                f"{sample['yaw']:8.2f} deg",
                f"{sample['delta']:8.2f} deg",
                f"{age:4.1f}s",
            ))

        print("\033[2J\033[H", end="")
        print("Yaw compare. delta is change since this script started.")
        print("Press Ctrl-C to stop.\n")
        print(f"{'source':25} {'yaw':>12} {'delta':>12} {'age':>7}")
        print("-" * 60)
        for label, yaw, delta, age in rows:
            print(f"{label:25} {yaw:>12} {delta:>12} {age:>7}")


def main():
    rclpy.init()
    node = YawCompare()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
