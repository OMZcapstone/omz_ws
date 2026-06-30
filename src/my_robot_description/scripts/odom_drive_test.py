#!/usr/bin/env python3
import math
import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


def yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def main():
    rclpy.init()
    node = rclpy.create_node('odom_drive_test')

    node.declare_parameter('speed', 0.05)
    node.declare_parameter('duration', 20.0)
    node.declare_parameter('target_distance', 1.0)
    node.declare_parameter('stop_on_odom_distance', True)

    speed = float(node.get_parameter('speed').value)
    duration = float(node.get_parameter('duration').value)
    target_distance = float(node.get_parameter('target_distance').value)
    stop_on_odom_distance = bool(node.get_parameter('stop_on_odom_distance').value)

    pub = node.create_publisher(Twist, '/cmd_vel', 10)
    last_odom = {'msg': None}

    def odom_cb(msg):
        last_odom['msg'] = msg

    node.create_subscription(Odometry, '/odom', odom_cb, 10)

    print('Waiting for /odom...')
    start_wait = time.monotonic()
    while rclpy.ok() and last_odom['msg'] is None and time.monotonic() - start_wait < 5.0:
        rclpy.spin_once(node, timeout_sec=0.1)

    if last_odom['msg'] is None:
        node.destroy_node()
        rclpy.shutdown()
        raise SystemExit('No /odom received. Start robot_bringup first.')

    start = last_odom['msg']
    start_x = start.pose.pose.position.x
    start_y = start.pose.pose.position.y
    start_yaw = yaw_from_quaternion(start.pose.pose.orientation)

    cmd = Twist()
    cmd.linear.x = speed

    print(
        f'Start odom: x={start_x:.3f}, y={start_y:.3f}, yaw={start_yaw:.3f} rad\n'
        f'Driving straight: speed={speed:.3f} m/s, duration_limit={duration:.1f}s, '
        f'target_odom_distance={target_distance:.3f}m'
    )
    print('Press q to stop at a measured floor mark and print the odom distance.')

    start_time = time.monotonic()
    stopped_by_key = False
    old_settings = None
    if sys.stdin.isatty():
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    try:
        while rclpy.ok():
            if old_settings is not None:
                readable, _, _ = select.select([sys.stdin], [], [], 0.0)
                if readable and sys.stdin.read(1).lower() == 'q':
                    stopped_by_key = True
                    print('Stopped by q.')
                    break

            elapsed = time.monotonic() - start_time
            current = last_odom['msg']
            dx = current.pose.pose.position.x - start_x
            dy = current.pose.pose.position.y - start_y
            distance = math.hypot(dx, dy)

            if elapsed >= duration:
                print('Duration limit reached.')
                break
            if stop_on_odom_distance and distance >= target_distance:
                print('Target odom distance reached.')
                break

            pub.publish(cmd)
            rclpy.spin_once(node, timeout_sec=0.0)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print('Ctrl+C received. Stopping, but q is preferred for calibration.')
    finally:
        if old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        stop = Twist()
        for _ in range(20):
            if rclpy.ok():
                pub.publish(stop)
                rclpy.spin_once(node, timeout_sec=0.0)
                time.sleep(0.02)

    end = last_odom['msg']
    end_x = end.pose.pose.position.x
    end_y = end.pose.pose.position.y
    end_yaw = yaw_from_quaternion(end.pose.pose.orientation)
    dx = end_x - start_x
    dy = end_y - start_y
    distance = math.hypot(dx, dy)

    print(
        f'End odom:   x={end_x:.3f}, y={end_y:.3f}, yaw={end_yaw:.3f} rad\n'
        f'Odom delta: dx={dx:.3f}, dy={dy:.3f}, distance={distance:.3f}m, '
        f'dyaw={end_yaw - start_yaw:.3f} rad\n'
        'Measure the real traveled distance and compare it to odom distance.'
    )
    if stopped_by_key:
        print('Use this odom distance for calibration if you stopped at a measured floor mark.')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
