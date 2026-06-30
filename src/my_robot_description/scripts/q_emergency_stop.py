#!/usr/bin/env python3
import select
import sys
import termios
import tty

import rclpy
from geometry_msgs.msg import Twist


def zero_twist():
    msg = Twist()
    msg.linear.x = 0.0
    msg.linear.y = 0.0
    msg.linear.z = 0.0
    msg.angular.x = 0.0
    msg.angular.y = 0.0
    msg.angular.z = 0.0
    return msg


def main():
    if not sys.stdin.isatty():
        raise SystemExit('q_emergency_stop must be run in an interactive terminal.')

    rclpy.init()
    node = rclpy.create_node('q_emergency_stop')
    publisher = node.create_publisher(Twist, '/cmd_vel', 10)
    stop_msg = zero_twist()
    stopping = False
    old_settings = termios.tcgetattr(sys.stdin)

    print('q emergency stop is armed. Press q to publish zero /cmd_vel continuously. Ctrl+C exits.')
    try:
        tty.setcbreak(sys.stdin.fileno())
        rate = node.create_rate(20)
        while rclpy.ok():
            readable, _, _ = select.select([sys.stdin], [], [], 0.0)
            if readable:
                key = sys.stdin.read(1)
                if key.lower() == 'q':
                    if not stopping:
                        print('EMERGENCY STOP: publishing zero /cmd_vel. Press Ctrl+C to exit.')
                    stopping = True

            if stopping:
                publisher.publish(stop_msg)

            rclpy.spin_once(node, timeout_sec=0.0)
            rate.sleep()
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        for _ in range(10):
            publisher.publish(stop_msg)
            rclpy.spin_once(node, timeout_sec=0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
