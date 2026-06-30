#include "md_controller/com.hpp"
#include "md_controller/kinematics.hpp"

#include <chrono>
#include <cmath>
#include <thread>

#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "std_msgs/msg/int32_multi_array.hpp"

Communication Com;
MotorVar Motor;

BYTE SendCmdRpm = OFF;
int left_rpm_ = 0;
int right_rpm_ = 0;
int sent_left_rpm_ = 0;
int sent_right_rpm_ = 0;
double motor_cmd_scale = 1.0;
double left_motor_cmd_scale = 1.0;
double right_motor_cmd_scale = 1.0;
std::chrono::steady_clock::time_point last_cmd_time;
bool received_cmd_vel = false;

double odom_x = 0.0;
double odom_y = 0.0;
double odom_yaw = 0.0;
double left_wheel_position = 0.0;
double right_wheel_position = 0.0;
int last_left_motor_tick = 0;
int last_right_motor_tick = 0;
int last_single_motor_tick = 0;
int invalid_pnt_delta_count = 0;
int invalid_single_delta_count = 0;
int pending_invalid_left_motor_tick = 0;
int pending_invalid_right_motor_tick = 0;
int pending_invalid_single_motor_tick = 0;
bool pending_invalid_pnt_tick = false;
bool pending_invalid_single_tick = false;
bool odom_initialized = false;
rclcpp::Time last_odom_time;

constexpr int kInvalidDeltaResyncCount = 2;

void CmdVelCallBack(const geometry_msgs::msg::Twist::SharedPtr msg)
{
    cmdVelToRpm(msg->linear.x, msg->angular.z, left_rpm_, right_rpm_);
    last_cmd_time = std::chrono::steady_clock::now();
    received_cmd_vel = true;
    SendCmdRpm = ON;
}

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("md_controller_node");

    auto cmd_vel_sub = node->create_subscription<geometry_msgs::msg::Twist>(
        "/cmd_vel", 10, CmdVelCallBack);
    auto motor_feedback_pub = node->create_publisher<std_msgs::msg::Int32MultiArray>(
        "/md/motor_feedback", 10);
    auto odom_pub = node->create_publisher<nav_msgs::msg::Odometry>("/odom", 10);
    auto joint_state_pub = node->create_publisher<sensor_msgs::msg::JointState>(
        "/joint_states", 10);
    tf2_ros::TransformBroadcaster tf_broadcaster(node);

    node->declare_parameter("MDUI", 184);
    node->declare_parameter("MDT", 183);
    node->declare_parameter("Port", "/dev/ttyUSB0");
    node->declare_parameter("Baudrate", 19200);
    node->declare_parameter("ID", 1);
    node->declare_parameter("GearRatio", 15);
    node->declare_parameter("poles", 10);
    node->declare_parameter("odom_encoder_ppr", 0);
    node->declare_parameter("wheel_radius", 0.033);
    node->declare_parameter("wheel_base", 0.16);
    node->declare_parameter("angular_cmd_scale", 0.6);
    node->declare_parameter("cmd_vel_timeout", 0.5);
    node->declare_parameter("debug_serial", false);
    node->declare_parameter("publish_tf", true);
    node->declare_parameter("odom_publish_rate", 20.0);
    node->declare_parameter("odom_tf_time_offset", 0.0);
    node->declare_parameter("max_wheel_delta_per_update", 0.5);
    node->declare_parameter("motor_cmd_scale", 1.0);
    node->declare_parameter("left_motor_cmd_scale", 1.0);
    node->declare_parameter("right_motor_cmd_scale", 1.0);
    node->declare_parameter("use_rpm_odom_fallback", false);
    node->declare_parameter("rpm_odom_min_abs", 1.0);

    node->get_parameter("MDUI", Com.nIDMDUI);
    node->get_parameter("MDT", Com.nIDMDT);
    node->get_parameter("Port", Com.nPort);
    node->get_parameter("Baudrate", Com.nBaudrate);
    node->get_parameter("ID", Motor.ID);
    node->get_parameter("GearRatio", Motor.GearRatio);
    node->get_parameter("poles", Motor.poles);
    node->get_parameter("odom_encoder_ppr", Motor.OdomEncoderPPR);
    SetSerialDebug(node->get_parameter("debug_serial").as_bool());

    float wheel_radius_param = node->get_parameter("wheel_radius").as_double();
    float wheel_base_param = node->get_parameter("wheel_base").as_double();
    const float angular_cmd_scale_param = node->get_parameter("angular_cmd_scale").as_double();
    const double cmd_vel_timeout = node->get_parameter("cmd_vel_timeout").as_double();
    const bool publish_tf = node->get_parameter("publish_tf").as_bool();
    const double odom_publish_rate = node->get_parameter("odom_publish_rate").as_double();
    const double odom_tf_time_offset = node->get_parameter("odom_tf_time_offset").as_double();
    const double max_wheel_delta_per_update =
        node->get_parameter("max_wheel_delta_per_update").as_double();
    motor_cmd_scale = node->get_parameter("motor_cmd_scale").as_double();
    left_motor_cmd_scale = node->get_parameter("left_motor_cmd_scale").as_double();
    right_motor_cmd_scale = node->get_parameter("right_motor_cmd_scale").as_double();
    const bool use_rpm_odom_fallback =
        node->get_parameter("use_rpm_odom_fallback").as_bool();
    const double rpm_odom_min_abs = node->get_parameter("rpm_odom_min_abs").as_double();

    setRobotParams(wheel_radius_param, wheel_base_param);
    setAngularCmdScale(angular_cmd_scale_param);

    if (Motor.OdomEncoderPPR <= 0) {
        Motor.OdomEncoderPPR = Motor.poles * 3 * Motor.GearRatio;
    }
    Motor.PPR = Motor.OdomEncoderPPR;
    Motor.Tick2RAD = (2.0 * PI) / Motor.PPR;

    RCLCPP_INFO(node->get_logger(),
                "MD params: port=%s baud=%d id=%d wheel_radius=%.4f wheel_base=%.4f odom_ppr=%d tick2rad=%.6f",
                Com.nPort.c_str(), Com.nBaudrate, Motor.ID, wheel_radius_param,
                wheel_base_param, Motor.OdomEncoderPPR, Motor.Tick2RAD);

    if (InitSerial() != 0) {
        rclcpp::shutdown();
        return 1;
    }

    int nArray[20] = {0};
    rclcpp::Rate loop_rate(400.0);
    auto last_feedback_request = std::chrono::steady_clock::now();
    auto last_odom_publish = std::chrono::steady_clock::now();
    const auto feedback_period = std::chrono::milliseconds(50);
    const auto odom_period = std::chrono::duration<double>(
        1.0 / std::max(1.0, odom_publish_rate));

    Motor.InitMotor = ON;
    Motor.InitError = 0;

    while (rclcpp::ok() && Motor.InitMotor == ON) {
        nArray[0] = PID_MAIN_DATA;
        PutMdData(PID_REQ_PID_DATA, Com.nIDMDT, Motor.ID, nArray);

        auto wait_until = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
        while (rclcpp::ok() && Motor.InitMotor == ON &&
               std::chrono::steady_clock::now() < wait_until) {
            ReceiveDataFromController(Motor.InitMotor);
            rclcpp::spin_some(node);
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }

        if (Motor.InitMotor == ON && ++Motor.InitError > 10) {
            RCLCPP_ERROR(node->get_logger(), "ID %d MOTOR INIT ERROR", Motor.ID);
            rclcpp::shutdown();
            return 1;
        }
    }

    nArray[0] = 0;
    nArray[1] = 0;
    PutMdData(PID_VEL_CMD, Com.nIDMDT, Motor.ID, nArray);

    nArray[0] = 0;
    PutMdData(PID_POSI_RESET, Com.nIDMDT, Motor.ID, nArray);
    RCLCPP_INFO(node->get_logger(), "MOTOR INIT END");

    while (rclcpp::ok()) {
        ReceiveDataFromController(OFF);

        if (received_cmd_vel) {
            const double age = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - last_cmd_time).count();
            if (age > cmd_vel_timeout &&
                (left_rpm_ != 0 || right_rpm_ != 0 ||
                 sent_left_rpm_ != 0 || sent_right_rpm_ != 0)) {
                left_rpm_ = 0;
                right_rpm_ = 0;
                SendCmdRpm = ON;
            }
        }

        const auto now_steady = std::chrono::steady_clock::now();
        if (SendCmdRpm || now_steady - last_feedback_request >= feedback_period) {
            if (SendCmdRpm) {
                sent_left_rpm_ = static_cast<int>(
                    std::round(-left_rpm_ * motor_cmd_scale * left_motor_cmd_scale));
                sent_right_rpm_ = static_cast<int>(
                    std::round(right_rpm_ * motor_cmd_scale * right_motor_cmd_scale));
                IByte left_iData = Short2Byte(sent_left_rpm_);
                IByte right_iData = Short2Byte(sent_right_rpm_);

                nArray[0] = 1;
                nArray[1] = left_iData.byLow;
                nArray[2] = left_iData.byHigh;
                nArray[3] = 1;
                nArray[4] = right_iData.byLow;
                nArray[5] = right_iData.byHigh;
                nArray[6] = REQUEST_PNT_MAIN_DATA;
                PutMdData(PID_PNT_VEL_CMD, Com.nIDMDT, Motor.ID, nArray);
                SendCmdRpm = OFF;
            } else {
                nArray[0] = PID_PNT_MAIN_DATA;
                PutMdData(PID_REQ_PID_DATA, Com.nIDMDT, Motor.ID, nArray);
            }
            last_feedback_request = now_steady;
        }

        if (now_steady - last_odom_publish >= odom_period) {
            const rclcpp::Time now = node->now();
            const int left_motor_tick = Com.pnt_position[0];
            const int right_motor_tick = Com.pnt_position[1];
            const int single_motor_tick = Com.position_by_id[Motor.ID];
            const bool has_pnt_feedback = Com.pnt_feedback_seen != 0;
            const bool has_single_feedback = Com.feedback_seen_by_id[Motor.ID] != 0;
            double linear_velocity = 0.0;
            double angular_velocity = 0.0;

            if (has_pnt_feedback || has_single_feedback) {
                if (!odom_initialized) {
                    last_left_motor_tick = left_motor_tick;
                    last_right_motor_tick = right_motor_tick;
                    last_single_motor_tick = single_motor_tick;
                    last_odom_time = now;
                    odom_initialized = true;
                } else {
                    const double dt = std::max(1e-6, (now - last_odom_time).seconds());
                    double distance = 0.0;
                    double delta_yaw = 0.0;
                    bool odom_delta_valid = true;

                    if (has_pnt_feedback) {
                        const int delta_left_tick = left_motor_tick - last_left_motor_tick;
                        const int delta_right_tick = right_motor_tick - last_right_motor_tick;
                        const double left_rad = -static_cast<double>(delta_left_tick) * Motor.Tick2RAD;
                        const double right_rad = static_cast<double>(delta_right_tick) * Motor.Tick2RAD;
                        const double left_distance = left_rad * wheel_radius_param;
                        const double right_distance = right_rad * wheel_radius_param;

                        if (std::fabs(left_distance) > max_wheel_delta_per_update ||
                            std::fabs(right_distance) > max_wheel_delta_per_update) {
                            invalid_pnt_delta_count++;
                            RCLCPP_WARN_THROTTLE(
                                node->get_logger(), *node->get_clock(), 2000,
                                "Ignoring encoder jump: left=%.3f m right=%.3f m count=%d",
                                left_distance, right_distance, invalid_pnt_delta_count);
                            odom_delta_valid = false;
                            bool invalid_ticks_are_stable = false;
                            if (pending_invalid_pnt_tick) {
                                const double pending_left_distance =
                                    -static_cast<double>(left_motor_tick - pending_invalid_left_motor_tick) *
                                    Motor.Tick2RAD * wheel_radius_param;
                                const double pending_right_distance =
                                    static_cast<double>(right_motor_tick - pending_invalid_right_motor_tick) *
                                    Motor.Tick2RAD * wheel_radius_param;
                                invalid_ticks_are_stable =
                                    std::fabs(pending_left_distance) <= max_wheel_delta_per_update &&
                                    std::fabs(pending_right_distance) <= max_wheel_delta_per_update;
                            }
                            pending_invalid_left_motor_tick = left_motor_tick;
                            pending_invalid_right_motor_tick = right_motor_tick;
                            pending_invalid_pnt_tick = true;

                            if (invalid_ticks_are_stable &&
                                invalid_pnt_delta_count >= kInvalidDeltaResyncCount) {
                                RCLCPP_WARN(
                                    node->get_logger(),
                                    "Resyncing encoder baseline after stable repeated jumps: left_tick=%d right_tick=%d",
                                    left_motor_tick, right_motor_tick);
                                last_left_motor_tick = left_motor_tick;
                                last_right_motor_tick = right_motor_tick;
                                last_odom_time = now;
                                invalid_pnt_delta_count = 0;
                                pending_invalid_pnt_tick = false;
                            }
                        } else {
                            invalid_pnt_delta_count = 0;
                            pending_invalid_pnt_tick = false;
                            left_wheel_position += left_rad;
                            right_wheel_position += right_rad;
                            distance = (left_distance + right_distance) * 0.5;
                            delta_yaw = (right_distance - left_distance) / wheel_base_param;

                            if (use_rpm_odom_fallback &&
                                delta_left_tick == 0 && delta_right_tick == 0 &&
                                (std::fabs(Com.pnt_rpm[0]) >= rpm_odom_min_abs ||
                                 std::fabs(Com.pnt_rpm[1]) >= rpm_odom_min_abs)) {
                                const double left_rpm_rad =
                                    -static_cast<double>(Com.pnt_rpm[0]) * 2.0 * PI / 60.0;
                                const double right_rpm_rad =
                                    static_cast<double>(Com.pnt_rpm[1]) * 2.0 * PI / 60.0;
                                const double left_rpm_distance =
                                    left_rpm_rad * wheel_radius_param * dt;
                                const double right_rpm_distance =
                                    right_rpm_rad * wheel_radius_param * dt;

                                left_wheel_position += left_rpm_rad * dt;
                                right_wheel_position += right_rpm_rad * dt;
                                distance = (left_rpm_distance + right_rpm_distance) * 0.5;
                                delta_yaw =
                                    (right_rpm_distance - left_rpm_distance) / wheel_base_param;
                            }
                            last_left_motor_tick = left_motor_tick;
                            last_right_motor_tick = right_motor_tick;
                        }
                    } else {
                        const int delta_single_tick = single_motor_tick - last_single_motor_tick;
                        const double wheel_rad = -static_cast<double>(delta_single_tick) * Motor.Tick2RAD;
                        distance = wheel_rad * wheel_radius_param;
                        if (std::fabs(distance) > max_wheel_delta_per_update) {
                            invalid_single_delta_count++;
                            RCLCPP_WARN_THROTTLE(
                                node->get_logger(), *node->get_clock(), 2000,
                                "Ignoring encoder jump: distance=%.3f m count=%d",
                                distance, invalid_single_delta_count);
                            odom_delta_valid = false;
                            bool invalid_tick_is_stable = false;
                            if (pending_invalid_single_tick) {
                                const double pending_distance =
                                    -static_cast<double>(single_motor_tick - pending_invalid_single_motor_tick) *
                                    Motor.Tick2RAD * wheel_radius_param;
                                invalid_tick_is_stable =
                                    std::fabs(pending_distance) <= max_wheel_delta_per_update;
                            }
                            pending_invalid_single_motor_tick = single_motor_tick;
                            pending_invalid_single_tick = true;

                            if (invalid_tick_is_stable &&
                                invalid_single_delta_count >= kInvalidDeltaResyncCount) {
                                RCLCPP_WARN(
                                    node->get_logger(),
                                    "Resyncing single encoder baseline after stable repeated jumps: tick=%d",
                                    single_motor_tick);
                                last_single_motor_tick = single_motor_tick;
                                last_odom_time = now;
                                invalid_single_delta_count = 0;
                                pending_invalid_single_tick = false;
                            }
                        } else {
                            invalid_single_delta_count = 0;
                            pending_invalid_single_tick = false;
                            last_single_motor_tick = single_motor_tick;
                        }
                    }

                    if (odom_delta_valid) {
                        const double heading = odom_yaw + delta_yaw * 0.5;
                        odom_x += distance * std::cos(heading);
                        odom_y += distance * std::sin(heading);
                        odom_yaw += delta_yaw;
                        linear_velocity = distance / dt;
                        angular_velocity = delta_yaw / dt;
                        last_odom_time = now;
                    }
                }
            }

            tf2::Quaternion odom_q;
            odom_q.setRPY(0.0, 0.0, odom_yaw);

            const rclcpp::Time tf_stamp =
                now + rclcpp::Duration::from_seconds(odom_tf_time_offset);

            if (publish_tf) {
                geometry_msgs::msg::TransformStamped odom_tf_msg;
                odom_tf_msg.header.stamp = tf_stamp;
                odom_tf_msg.header.frame_id = "odom";
                odom_tf_msg.child_frame_id = "base_footprint";
                odom_tf_msg.transform.translation.x = odom_x;
                odom_tf_msg.transform.translation.y = odom_y;
                odom_tf_msg.transform.translation.z = 0.0;
                odom_tf_msg.transform.rotation.x = odom_q.x();
                odom_tf_msg.transform.rotation.y = odom_q.y();
                odom_tf_msg.transform.rotation.z = odom_q.z();
                odom_tf_msg.transform.rotation.w = odom_q.w();
                tf_broadcaster.sendTransform(odom_tf_msg);
            }

            nav_msgs::msg::Odometry odom_msg;
            odom_msg.header.stamp = now;
            odom_msg.header.frame_id = "odom";
            odom_msg.child_frame_id = "base_footprint";
            odom_msg.pose.pose.position.x = odom_x;
            odom_msg.pose.pose.position.y = odom_y;
            odom_msg.pose.pose.orientation.x = odom_q.x();
            odom_msg.pose.pose.orientation.y = odom_q.y();
            odom_msg.pose.pose.orientation.z = odom_q.z();
            odom_msg.pose.pose.orientation.w = odom_q.w();
            odom_msg.twist.twist.linear.x = linear_velocity;
            odom_msg.twist.twist.angular.z = angular_velocity;
            odom_msg.pose.covariance[0] = 0.03;
            odom_msg.pose.covariance[7] = 0.03;
            odom_msg.pose.covariance[14] = 99999.0;
            odom_msg.pose.covariance[21] = 99999.0;
            odom_msg.pose.covariance[28] = 99999.0;
            odom_msg.pose.covariance[35] = 0.20;
            odom_msg.twist.covariance[0] = 0.02;
            odom_msg.twist.covariance[7] = 0.10;
            odom_msg.twist.covariance[14] = 99999.0;
            odom_msg.twist.covariance[21] = 99999.0;
            odom_msg.twist.covariance[28] = 99999.0;
            odom_msg.twist.covariance[35] = 0.08;
            odom_pub->publish(odom_msg);

            if (has_pnt_feedback || has_single_feedback) {
                sensor_msgs::msg::JointState joint_msg;
                joint_msg.header.stamp = now;
                joint_msg.name = {"front_left_wheel_joint", "front_right_wheel_joint"};
                joint_msg.position = {left_wheel_position, right_wheel_position};
                joint_msg.velocity = {
                    -static_cast<double>(Com.pnt_rpm[0]) * 2.0 * PI / 60.0,
                    static_cast<double>(Com.pnt_rpm[1]) * 2.0 * PI / 60.0};
                joint_state_pub->publish(joint_msg);
            }

            std_msgs::msg::Int32MultiArray feedback_msg;
            feedback_msg.data = {
                Com.pnt_feedback_seen,
                Com.pnt_rpm[0],
                Com.pnt_position[0],
                Com.pnt_rpm[1],
                Com.pnt_position[1],
                Com.rpm_by_id[1],
                Com.position_by_id[1],
                Com.feedback_seen_by_id[1],
                Com.rpm_by_id[2],
                Com.position_by_id[2],
                Com.feedback_seen_by_id[2],
                Com.last_rcv_id,
                Com.last_rcv_pid,
                Com.last_rcv_data_size,
                left_rpm_,
                right_rpm_,
                sent_left_rpm_,
                sent_right_rpm_,
                Com.last_main_data[0],
                Com.last_main_data[1],
                Com.last_main_data[2],
                Com.last_main_data[3],
                Com.last_main_data[4],
                Com.last_main_data[5],
                Com.last_main_data[6],
                Com.last_main_data[7],
                Com.last_main_data[8],
                Com.last_main_data[9],
                Com.last_main_data[10],
                Com.last_main_data[11],
                Com.last_main_data[12],
                Com.last_main_data[13],
                Com.last_main_data[14],
                Com.last_main_data[15],
                Com.last_main_data[16],
                Com.last_main_data[17]};
            motor_feedback_pub->publish(feedback_msg);
            last_odom_publish = now_steady;
        }

        rclcpp::spin_some(node);
        loop_rate.sleep();
    }

    rclcpp::shutdown();
    return 0;
}
