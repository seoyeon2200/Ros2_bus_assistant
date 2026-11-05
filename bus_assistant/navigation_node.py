"""
Navigation Node — /bus_color 구독 → 해당 버스 정류장 waypoint로 Nav2 자율주행,
                  상태를 /robot_state 및 /display_text 토픽으로 발행,
                  /goal_marker 로 RViz 목적지 마커 표시
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String
from visualization_msgs.msg import Marker


BUS_STOP_WAYPOINTS = {
    # 각 버스 정면 앞 승강장 (x=1.5: 버스 정면 x=3.0 기준 1.5m 앞)
    # yaw=0° : 동쪽(버스 방향) 정면
    'red':    (1.5, -7.5, 0.0),   # 1번 홈 (bus y=-7.5) 정면
    'blue':   (1.5, -2.5, 0.0),   # 2번 홈 (bus y=-2.5) 정면
    'green':  (1.5,  2.5, 0.0),   # 3번 홈 (bus y= 2.5) 정면
    'yellow': (1.5,  7.5, 0.0),   # 4번 홈 (bus y= 7.5) 정면
}

_BUS_COLORS_RGBA = {
    'red':    (1.0, 0.1, 0.1),
    'blue':   (0.1, 0.3, 1.0),
    'green':  (0.1, 0.8, 0.1),
    'yellow': (1.0, 0.9, 0.0),
}

STATE_IDLE       = 'idle'
STATE_NAVIGATING = 'navigating'
STATE_ARRIVED    = 'arrived'


def _make_pose(x, y, yaw_deg, clock):
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.header.stamp = clock.now().to_msg()
    p.pose.position.x = x
    p.pose.position.y = y
    # yaw_goal_tolerance=π 이므로 orientation은 identity로 설정해도 무방
    p.pose.orientation.w = 1.0
    return p


class NavigationNode(Node):
    def __init__(self):
        super().__init__('navigation_node')

        self._state = STATE_IDLE
        self._target_color = 'none'

        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # GUI 버튼: IDLE·ARRIVED 모두 수락
        self.create_subscription(String, '/selected_bus', self._selected_bus_cb, 10)
        # perception: IDLE 상태에서만 수락
        self.create_subscription(String, '/bus_color', self._bus_color_cb, 10)
        self.create_subscription(String, '/obstacle_detected', self._obstacle_cb, 10)

        self.pub_state   = self.create_publisher(String, '/robot_state', 10)
        self.pub_display = self.create_publisher(String, '/display_text', 10)

        qos_tl = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_goal_marker = self.create_publisher(Marker, '/goal_marker', qos_tl)

        self._publish_display('안내 로봇 준비 완료\n목적지 버스를 선택해 주세요')
        self.get_logger().info('NavigationNode 시작')

    # ── 콜백 ──────────────────────────────────────────────────────────

    def _selected_bus_cb(self, msg: String):
        """GUI 버튼: IDLE·ARRIVED 상태에서 수락"""
        color = msg.data
        if color not in BUS_STOP_WAYPOINTS:
            return
        if self._state == STATE_NAVIGATING:
            self.get_logger().info(f'이동 중 — GUI 입력 무시 ({color})')
            return
        self._target_color = color
        self._navigate_to(color)

    def _bus_color_cb(self, msg: String):
        """perception: 감지된 버스 색상을 화면에 안내만 함 — 자동 이동 없음"""
        color = msg.data
        if self._state != STATE_IDLE or color == 'none' or color not in BUS_STOP_WAYPOINTS:
            return
        color_kr = {'red': '빨간', 'blue': '파란', 'green': '초록', 'yellow': '노란'}.get(color, color)
        self._publish_display(f'{color_kr} 버스가 감지되었습니다\n버튼을 눌러 이동을 시작하세요')

    def _obstacle_cb(self, msg: String):
        if msg.data == 'detected' and self._state == STATE_NAVIGATING:
            self._publish_display('⚠ 장애물 감지\n잠시 멈춥니다...')

    # ── 내비게이션 ────────────────────────────────────────────────────

    def _navigate_to(self, color: str):
        x, y, yaw = BUS_STOP_WAYPOINTS[color]
        self.get_logger().info(f'목적지: {color} 버스 정류장 ({x:.1f}, {y:.1f})')

        self._state = STATE_NAVIGATING
        self._publish_state(STATE_NAVIGATING)
        self._publish_display(
            f'{color.upper()} 버스 정류장으로\n이동 중입니다\n뒤를 따라와 주세요')
        self._publish_goal_marker(color, x, y)

        self.get_logger().info('navigate_to_pose 서버 대기 중...')
        if not self._nav_client.wait_for_server(timeout_sec=30.0):
            self.get_logger().error('navigate_to_pose 서버에 연결 실패 (30초 초과)')
            self._state = STATE_IDLE
            self._target_color = 'none'
            self._clear_goal_marker()
            self._publish_display('Nav2 서버 연결 실패\n내비게이션 스택을 확인해 주세요')
            return

        goal = NavigateToPose.Goal()
        goal.pose = _make_pose(x, y, yaw, self.get_clock())
        self._nav_client.send_goal_async(goal).add_done_callback(
            self._goal_response_cb)

    def _goal_response_cb(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn('목표 거부됨')
            self._state = STATE_IDLE
            self._target_color = 'none'
            self._clear_goal_marker()
            return
        handle.get_result_async().add_done_callback(self._result_cb)

    def _result_cb(self, future):
        status = future.result().status
        color  = self._target_color
        self._target_color = 'none'
        self._clear_goal_marker()

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('목적지 도착!')
            self._state = STATE_ARRIVED
            self._publish_state(STATE_ARRIVED)
            self._publish_display(
                f'[{color.upper()} 버스]\n승차 위치에 도착했습니다\n안전하게 탑승하세요')
        else:
            self.get_logger().warn(f'내비게이션 실패 (status={status})')
            self._state = STATE_IDLE
            self._publish_state(STATE_IDLE)
            self._publish_display('경로 이동 실패\n버스를 다시 선택해 주세요')

    # ── 목적지 마커 ───────────────────────────────────────────────────

    def _publish_goal_marker(self, color, x, y):
        r, g, b = _BUS_COLORS_RGBA.get(color, (1.0, 1.0, 1.0))
        m = Marker()
        m.header.frame_id = 'map'
        m.header.stamp    = self.get_clock().now().to_msg()
        m.ns = 'goal'; m.id = 0
        m.type   = Marker.CYLINDER
        m.action = Marker.ADD
        m.pose.position.x = x
        m.pose.position.y = y
        m.pose.position.z = 0.5
        m.pose.orientation.w = 1.0
        m.scale.x = 0.4; m.scale.y = 0.4; m.scale.z = 1.0
        m.color.r = r; m.color.g = g; m.color.b = b; m.color.a = 0.9
        m.lifetime.sec = 0
        self.pub_goal_marker.publish(m)

    def _clear_goal_marker(self):
        m = Marker()
        m.header.frame_id = 'map'
        m.header.stamp    = self.get_clock().now().to_msg()
        m.ns = 'goal'; m.id = 0
        m.action = Marker.DELETE
        self.pub_goal_marker.publish(m)

    # ── 헬퍼 ──────────────────────────────────────────────────────────

    def _publish_state(self, state):
        msg = String(); msg.data = state
        self.pub_state.publish(msg)

    def _publish_display(self, text):
        msg = String(); msg.data = text
        self.pub_display.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = NavigationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
