#!/usr/bin/env python3
import math

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PointStamped
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose
from nav2_msgs.action import ComputePathThroughPoses
from nav2_msgs.action import NavigateToPose
from nav2_msgs.action import NavigateThroughPoses
from nav_msgs.msg import Path
from rclpy.action import ActionClient
from rclpy.node import Node
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray


def yaw_to_quaternion(yaw):
    half_yaw = yaw * 0.5
    return {
        'z': math.sin(half_yaw),
        'w': math.cos(half_yaw),
    }


class RvizWaypointGoal(Node):
    def __init__(self):
        super().__init__('rviz_waypoint_goal')

        self.declare_parameter('waypoint_topic', '/clicked_point')
        self.declare_parameter('goal_topic', '/waypoint_goal_pose')
        self.declare_parameter('fallback_goal_topic', '')
        self.declare_parameter('navigate_to_pose_action_name', '/navigate_to_pose')
        self.declare_parameter('navigate_action_name', '/navigate_through_poses')
        self.declare_parameter('planner_to_pose_action_name', '/compute_path_to_pose')
        self.declare_parameter('planner_action_name', '/compute_path_through_poses')
        self.declare_parameter('preview_path_topic', '/waypoint_global_plan')
        self.declare_parameter('marker_topic', '/waypoint_markers')
        self.declare_parameter('planner_id', 'GridBased')
        self.declare_parameter('waypoint_yaw', 0.0)
        self.declare_parameter('min_waypoint_distance', 0.35)
        self.declare_parameter('clear_after_send', False)
        self.declare_parameter('clear_after_result', True)
        self.declare_parameter('server_timeout_sec', 10.0)

        waypoint_topic = self.get_parameter('waypoint_topic').value
        goal_topic = self.get_parameter('goal_topic').value
        fallback_goal_topic = self.get_parameter('fallback_goal_topic').value
        navigate_to_pose_action_name = self.get_parameter(
            'navigate_to_pose_action_name'
        ).value
        navigate_action_name = self.get_parameter('navigate_action_name').value
        planner_to_pose_action_name = self.get_parameter(
            'planner_to_pose_action_name'
        ).value
        planner_action_name = self.get_parameter('planner_action_name').value
        preview_path_topic = self.get_parameter('preview_path_topic').value
        marker_topic = self.get_parameter('marker_topic').value

        self._waypoints = []
        self._goal_handle = None
        self._active_route_uses_waypoints = False
        self._active_route = []
        
        self._navigate_to_pose_client = ActionClient(
            self,
            NavigateToPose,
            navigate_to_pose_action_name,
        )
        self._navigate_client = ActionClient(
            self,
            NavigateThroughPoses,
            navigate_action_name,
        )
        self._planner_to_pose_client = ActionClient(
            self,
            ComputePathToPose,
            planner_to_pose_action_name,
        )
        self._planner_client = ActionClient(
            self,
            ComputePathThroughPoses,
            planner_action_name,
        )
        self._path_publisher = self.create_publisher(Path, preview_path_topic, 1)
        self._marker_publisher = self.create_publisher(MarkerArray, marker_topic, 1)

        self.create_subscription(PointStamped, waypoint_topic, self._on_waypoint, 10)
        self.create_subscription(PoseStamped, goal_topic, self._on_goal, 10)
        if fallback_goal_topic and fallback_goal_topic != goal_topic:
            self.create_subscription(PoseStamped, fallback_goal_topic, self._on_goal, 10)

        
        self.get_logger().info(
            f'RViz waypoint mode ready: Publish Point -> {waypoint_topic}, '
            f'2D Goal Pose -> {goal_topic} or {fallback_goal_topic}'
        )

    def _on_waypoint(self, msg):
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose.position.x = msg.point.x
        pose.pose.position.y = msg.point.y
        pose.pose.position.z = 0.0

        quat = yaw_to_quaternion(float(self.get_parameter('waypoint_yaw').value))
        pose.pose.orientation.z = quat['z']
        pose.pose.orientation.w = quat['w']

        self._waypoints.append(pose)
        self.get_logger().info(
            f'waypoint #{len(self._waypoints)} added: '
            f'x={pose.pose.position.x:.3f}, y={pose.pose.position.y:.3f}'
        )
        self._publish_waypoint_markers()
        self._request_preview_path(self._waypoints)

    def _on_goal(self, msg):
        self.get_logger().info(
            f'final goal clicked with {len(self._waypoints)} queued waypoint(s).'
        )

        if self._waypoints:
            self._send_route_through_waypoints(msg)
        else:
            self._send_direct_goal(msg)

    def _send_route_through_waypoints(self, final_goal):
        poses = self._route_targets_with_short_hops_removed([*self._waypoints, final_goal])
        if len(poses) <= 1:
            self.get_logger().warn('no valid waypoint remains; sending final goal directly.')
            self._send_direct_goal(final_goal)
            return

        timeout = float(self.get_parameter('server_timeout_sec').value)
        if not self._navigate_client.wait_for_server(timeout_sec=timeout):
            self.get_logger().error(
                f'NavigateThroughPoses action server is not available after {timeout:.1f}s.'
            )
            return

        self._request_preview_path(poses)
        self._active_route_uses_waypoints = True
        self._active_route = poses
        self.get_logger().info(
            f'sending NavigateThroughPoses route: {len(poses) - 1} waypoint(s) + final goal '
            f'x={final_goal.pose.position.x:.3f}, y={final_goal.pose.position.y:.3f}'
        )

        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = poses
        send_future = self._navigate_client.send_goal_async(
            goal_msg,
            feedback_callback=self._on_feedback,
        )
        send_future.add_done_callback(self._on_goal_response)

        if bool(self.get_parameter('clear_after_send').value):
            self._waypoints.clear()
            self._publish_waypoint_markers()
            self.get_logger().info('waypoint list cleared after sending route.')

    def _send_direct_goal(self, final_goal):
        timeout = float(self.get_parameter('server_timeout_sec').value)
        if not self._navigate_to_pose_client.wait_for_server(timeout_sec=timeout):
            self.get_logger().error(
                f'NavigateToPose action server is not available after {timeout:.1f}s.'
            )
            return

        self._request_direct_preview_path(final_goal)
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = final_goal

        self.get_logger().info(
            f'sending direct goal: '
            f'x={final_goal.pose.position.x:.3f}, y={final_goal.pose.position.y:.3f}'
        )

        self._active_route_uses_waypoints = False
        self._active_route = []
        send_future = self._navigate_to_pose_client.send_goal_async(
            goal_msg,
            feedback_callback=self._on_feedback,
        )
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('route was rejected by Nav2.')
            return

        self._goal_handle = goal_handle
        self.get_logger().info('route accepted by Nav2.')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        feedback = feedback_msg.feedback
        if hasattr(feedback, 'number_of_poses_remaining'):
            self.get_logger().info(
                f'poses remaining: {feedback.number_of_poses_remaining}',
                throttle_duration_sec=2.0,
            )

    def _on_result(self, future):
        result = future.result()
        self.get_logger().info(f'route finished with status={result.status}.')

        if self._active_route_uses_waypoints and self._active_route:
            if result.status == GoalStatus.STATUS_SUCCEEDED:
                self.get_logger().info('NavigateThroughPoses route reached final goal.')
            else:
                self.get_logger().warn('NavigateThroughPoses route did not succeed.')

        if (
            self._active_route_uses_waypoints
            and bool(self.get_parameter('clear_after_result').value)
        ):
            self._waypoints.clear()
            self._active_route = []
            self._publish_waypoint_markers()
            self.get_logger().info('waypoint list cleared after route finished.')

    def _route_targets_with_short_hops_removed(self, poses):
        if len(poses) <= 1:
            return poses

        min_distance = float(self.get_parameter('min_waypoint_distance').value)
        filtered = []
        previous = None
        for pose in poses:
            if previous is None:
                filtered.append(pose)
                previous = pose
                continue

            distance = math.hypot(
                pose.pose.position.x - previous.pose.position.x,
                pose.pose.position.y - previous.pose.position.y,
            )
            if distance < min_distance and pose is not poses[-1]:
                self.get_logger().warn(
                    f'skipping waypoint too close to previous target: '
                    f'distance={distance:.2f}m < {min_distance:.2f}m'
                )
                continue

            filtered.append(pose)
            previous = pose

        return filtered

    def _request_preview_path(self, poses):
        if not poses:
            self._path_publisher.publish(Path())
            return

        if not self._planner_client.server_is_ready():
            timeout = float(self.get_parameter('server_timeout_sec').value)
            if not self._planner_client.wait_for_server(timeout_sec=timeout):
                self.get_logger().warn(
                    f'ComputePathThroughPoses action server is not available after {timeout:.1f}s.'
                )
                return

        goal_msg = ComputePathThroughPoses.Goal()
        goal_msg.goals = poses
        goal_msg.planner_id = self.get_parameter('planner_id').value
        goal_msg.use_start = False

        future = self._planner_client.send_goal_async(goal_msg)
        future.add_done_callback(self._on_preview_goal_response)

    def _request_direct_preview_path(self, pose):
        if not self._planner_to_pose_client.server_is_ready():
            timeout = float(self.get_parameter('server_timeout_sec').value)
            if not self._planner_to_pose_client.wait_for_server(timeout_sec=timeout):
                self.get_logger().warn(
                    f'ComputePathToPose action server is not available after {timeout:.1f}s.'
                )
                return

        goal_msg = ComputePathToPose.Goal()
        goal_msg.goal = pose
        goal_msg.planner_id = self.get_parameter('planner_id').value
        goal_msg.use_start = False

        future = self._planner_to_pose_client.send_goal_async(goal_msg)
        future.add_done_callback(self._on_preview_goal_response)

    def _on_preview_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('preview path request was rejected by Nav2 planner.')
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_preview_result)

    def _on_preview_result(self, future):
        result = future.result()
        path = result.result.path
        self._path_publisher.publish(path)
        self.get_logger().info(
            f'preview global path updated: {len(path.poses)} pose(s)',
            throttle_duration_sec=1.0,
        )

    def _publish_waypoint_markers(self):
        markers = MarkerArray()

        delete_marker = Marker()
        delete_marker.header.frame_id = 'map'
        delete_marker.header.stamp = self.get_clock().now().to_msg()
        delete_marker.ns = 'rviz_waypoints'
        delete_marker.action = Marker.DELETEALL
        markers.markers.append(delete_marker)

        for index, pose in enumerate(self._waypoints, start=1):
            stamp = self.get_clock().now().to_msg()

            sphere = Marker()
            sphere.header = pose.header
            sphere.header.stamp = stamp
            sphere.ns = 'rviz_waypoints'
            sphere.id = index
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose = pose.pose
            sphere.pose.position.z = 0.08
            sphere.scale.x = 0.22
            sphere.scale.y = 0.22
            sphere.scale.z = 0.12
            sphere.color.r = 1.0
            sphere.color.g = 0.72
            sphere.color.b = 0.12
            sphere.color.a = 0.95
            markers.markers.append(sphere)

            label = Marker()
            label.header = pose.header
            label.header.stamp = stamp
            label.ns = 'rviz_waypoint_labels'
            label.id = index
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose = pose.pose
            label.pose.position.z = 0.35
            label.scale.z = 0.24
            label.color.r = 1.0
            label.color.g = 1.0
            label.color.b = 1.0
            label.color.a = 1.0
            label.text = str(index)
            markers.markers.append(label)

        self._marker_publisher.publish(markers)


def main():
    rclpy.init()
    node = RvizWaypointGoal()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
