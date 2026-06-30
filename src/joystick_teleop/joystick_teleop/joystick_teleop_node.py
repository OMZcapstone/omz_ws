#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy

class JoystickTeleop(Node):
    def __init__(self):
        super().__init__('joystick_teleop')

        self.declare_parameter('max_lin_vel', 0.09)
        self.declare_parameter('max_ang_vel', 0.12)
        self.declare_parameter('cmd_vel_topic', 'cmd_vel')
        self.declare_parameter('axis_linear', 1)
        self.declare_parameter('axis_angular', 0)
        self.declare_parameter('button_speed_up', 3)
        self.declare_parameter('button_speed_down', 0)
        self.declare_parameter('button_deadman', 5)
        self.declare_parameter('button_stop', 1)
        self.declare_parameter('invert_linear', False)
        self.declare_parameter('invert_angular', False)
        self.declare_parameter('initial_linear_speed', 0.03)
        self.declare_parameter('initial_reverse_linear_speed', 0.03)
        self.declare_parameter('button_speed_step', 0.01)

        self.max_lin = self.get_parameter('max_lin_vel').value
        self.max_ang = self.get_parameter('max_ang_vel').value
        cmd_topic = self.get_parameter('cmd_vel_topic').value
        self.axis_linear = self.get_parameter('axis_linear').value
        self.axis_angular = self.get_parameter('axis_angular').value
        self.button_speed_up = self.get_parameter('button_speed_up').value
        self.button_speed_down = self.get_parameter('button_speed_down').value
        self.button_deadman = self.get_parameter('button_deadman').value
        self.button_stop = self.get_parameter('button_stop').value
        self.invert_linear = self.get_parameter('invert_linear').value
        self.invert_angular = self.get_parameter('invert_angular').value
        self.initial_linear_speed = self.get_parameter('initial_linear_speed').value
        self.initial_reverse_linear_speed = self.get_parameter(
            'initial_reverse_linear_speed'
        ).value
        self.button_speed_step = self.get_parameter('button_speed_step').value

        qos = QoSProfile(depth=10)
        self.pub = self.create_publisher(Twist, cmd_topic, qos)
        self.sub = self.create_subscription(Joy, 'joy', self._joy_callback, qos)

        self._stopped = False
        self._speed_up_was_pressed = False
        self._speed_down_was_pressed = False
        self._deadman_was_pressed = False
        self._forward_lin_speed = max(0.0, min(self.max_lin, self.initial_linear_speed))
        self._reverse_lin_speed = max(
            0.0,
            min(self.max_lin, self.initial_reverse_linear_speed),
        )
        self._last_linear_direction = 1.0
        self.get_logger().info(
            f'Joystick teleop ready (max_lin={self.max_lin}, max_ang={self.max_ang})\n'
            '  Hold RB (deadman) to move\n'
            '  Left stick: forward/back + turn\n'
            f'  Press Y/A to adjust selected direction by {self.button_speed_step:.3f} m/s\n'
            '  Press B for emergency stop\n'
            f'  mapping: axis_linear={self.axis_linear}, axis_angular={self.axis_angular}, '
            f'button_speed_up={self.button_speed_up}, '
            f'button_speed_down={self.button_speed_down}, '
            f'button_deadman={self.button_deadman}, '
            f'button_stop={self.button_stop}'
        )

    def _joy_callback(self, msg: Joy):
        twist = Twist()

        if len(msg.buttons) > self.button_stop and msg.buttons[self.button_stop]:
            self._stopped = True
            self._forward_lin_speed = max(0.0, min(self.max_lin, self.initial_linear_speed))
            self._reverse_lin_speed = max(
                0.0,
                min(self.max_lin, self.initial_reverse_linear_speed),
            )
            self.pub.publish(twist)
            self.get_logger().warn('Emergency stop!')
            return

        deadman = len(msg.buttons) > self.button_deadman and msg.buttons[self.button_deadman]
        if deadman:
            self._stopped = False

        if not deadman or self._stopped:
            if self._deadman_was_pressed or self._stopped:
                self.pub.publish(twist)
            self._deadman_was_pressed = deadman
            return

        self._deadman_was_pressed = True

        linear_axis = 0.0
        if len(msg.axes) > self.axis_linear:
            linear_axis = msg.axes[self.axis_linear]
            if self.invert_linear:
                linear_axis *= -1.0

        if abs(linear_axis) > 0.05:
            self._last_linear_direction = 1.0 if linear_axis > 0.0 else -1.0
        selected_direction = (
            1.0 if linear_axis > 0.05
            else -1.0 if linear_axis < -0.05
            else self._last_linear_direction
        )

        speed_up_pressed = (
            len(msg.buttons) > self.button_speed_up
            and msg.buttons[self.button_speed_up]
        )
        speed_down_pressed = (
            len(msg.buttons) > self.button_speed_down
            and msg.buttons[self.button_speed_down]
        )
        if speed_up_pressed and not self._speed_up_was_pressed:
            if selected_direction >= 0.0:
                self._forward_lin_speed += self.button_speed_step
                self._forward_lin_speed = max(0.0, min(self.max_lin, self._forward_lin_speed))
            else:
                self._reverse_lin_speed += self.button_speed_step
                self._reverse_lin_speed = max(0.0, min(self.max_lin, self._reverse_lin_speed))
            self.get_logger().info(
                f'speed: forward={self._forward_lin_speed:.3f}, '
                f'reverse={self._reverse_lin_speed:.3f}'
            )
        if speed_down_pressed and not self._speed_down_was_pressed:
            if selected_direction >= 0.0:
                self._forward_lin_speed -= self.button_speed_step
                self._forward_lin_speed = max(0.0, min(self.max_lin, self._forward_lin_speed))
            else:
                self._reverse_lin_speed -= self.button_speed_step
                self._reverse_lin_speed = max(0.0, min(self.max_lin, self._reverse_lin_speed))
            self.get_logger().info(
                f'speed: forward={self._forward_lin_speed:.3f}, '
                f'reverse={self._reverse_lin_speed:.3f}'
            )
        self._speed_up_was_pressed = speed_up_pressed
        self._speed_down_was_pressed = speed_down_pressed

        if linear_axis >= 0.0:
            twist.linear.x = linear_axis * self._forward_lin_speed
        else:
            twist.linear.x = linear_axis * self._reverse_lin_speed
        twist.linear.x = max(-self.max_lin, min(self.max_lin, twist.linear.x))

        if len(msg.axes) > self.axis_angular:
            angular_axis = msg.axes[self.axis_angular]
            if self.invert_angular:
                angular_axis *= -1.0
            twist.angular.z = angular_axis * self.max_ang
            twist.angular.z = max(-self.max_ang, min(self.max_ang, twist.angular.z))

        self.pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = JoystickTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # publish zero before exit
        node.pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
