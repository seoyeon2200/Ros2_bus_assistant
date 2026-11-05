"""
Safety Node — /scan(LiDAR) 구독 → 전방 장애물 감지 시 /obstacle_detected 발행
              임계 거리 이내 물체가 있으면 NavigationNode에 알림
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

# 전방 ±FOV_DEG 범위, 이 거리 이내면 장애물로 판정
OBSTACLE_DIST_M = 0.8
FOV_DEG = 30.0


class SafetyNode(Node):
    def __init__(self):
        super().__init__('safety_node')

        self.declare_parameter('obstacle_dist', OBSTACLE_DIST_M)
        self.declare_parameter('fov_deg', FOV_DEG)

        self._threshold = self.get_parameter('obstacle_dist').value
        self._fov = self.get_parameter('fov_deg').value
        self._robot_state = 'idle'

        self.sub_scan = self.create_subscription(
            LaserScan, '/scan', self._scan_cb, 10)
        self.create_subscription(String, '/robot_state', self._state_cb, 10)

        self.pub_obstacle = self.create_publisher(String, '/obstacle_detected', 10)
        self.pub_display = self.create_publisher(String, '/display_text', 10)

        self._obstacle_active = False
        self.get_logger().info(
            f'SafetyNode 시작 — 임계거리 {self._threshold}m, FOV ±{self._fov}°')

    def _state_cb(self, msg: String):
        self._robot_state = msg.data
        # 이동 중이 아닐 때는 obstacle 추적 초기화 → 도착 후 "경로 안전" 메시지 방지
        if msg.data != 'navigating':
            self._obstacle_active = False

    def _scan_cb(self, msg: LaserScan):
        import math
        angle_min = msg.angle_min
        angle_inc = msg.angle_increment
        fov_rad = math.radians(self._fov)

        detected = False
        for i, dist in enumerate(msg.ranges):
            if not (msg.range_min < dist < msg.range_max):
                continue
            angle = angle_min + i * angle_inc
            # 전방 ±FOV 범위만 검사
            if abs(angle) <= fov_rad and dist < self._threshold:
                detected = True
                break

        # 이동 중일 때만 display_text 발행 (도착 후 메시지 덮어쓰기 방지)
        navigating = (self._robot_state == 'navigating')

        if detected and not self._obstacle_active:
            self._obstacle_active = True
            self.get_logger().warn(f'장애물 감지 (전방 {self._threshold}m 이내)')
            self._publish('detected')
            if navigating:
                self._publish_display(f'⚠ 전방 장애물 감지\n{self._threshold}m 이내 접근')

        elif not detected and self._obstacle_active:
            self._obstacle_active = False
            self.get_logger().info('장애물 해소')
            self._publish('clear')
            if navigating:
                self._publish_display('경로 안전\n이동을 재개합니다')

    def _publish(self, status: str):
        msg = String()
        msg.data = status
        self.pub_obstacle.publish(msg)

    def _publish_display(self, text: str):
        msg = String()
        msg.data = text
        self.pub_display.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
