"""
Bus Markers Node — /bus_markers 토픽으로 각 버스 위치에 색상 MarkerArray 발행
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray

# 버스 정보: (이름, 중심 x, 중심 y, yaw_rad, 가로, 세로, R, G, B)
# 시외버스 터미널 배치:
#   - 모든 버스가 yaw=π (서쪽/-x 방향)를 향해 정면이 로봇 출발점 쪽을 바라봄
#   - 홈 간격 5.0 m (버스 폭 2.0 m + 여유 3.0 m)
#   - 버스 정면 x=3.0, 로봇 출발점 (0,0) yaw=0 → 서로 마주봄
_BUSES = [
    ('red',    5.0, -7.5, math.pi, 4.0, 2.0, 1.0, 0.1, 0.1),  # 1번 홈
    ('blue',   5.0, -2.5, math.pi, 4.0, 2.0, 0.1, 0.3, 1.0),  # 2번 홈
    ('green',  5.0,  2.5, math.pi, 4.0, 2.0, 0.1, 0.8, 0.1),  # 3번 홈
    ('yellow', 5.0,  7.5, math.pi, 4.0, 2.0, 1.0, 0.9, 0.0),  # 4번 홈
]

_BUS_HEIGHT = 2.0
_Z_CENTER   = _BUS_HEIGHT / 2.0
_ALPHA      = 0.75


class BusMarkersNode(Node):
    def __init__(self):
        super().__init__('bus_markers_node')

        # Transient Local: RViz가 나중에 구독해도 최신 메시지를 받음
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._pub = self.create_publisher(MarkerArray, '/bus_markers', qos)

        self._publish()
        self.get_logger().info('BusMarkersNode 시작 — /bus_markers 발행 완료')

    def _publish(self):
        array = MarkerArray()
        stamp = self.get_clock().now().to_msg()

        for i, (name, cx, cy, yaw, sx, sy, r, g, b) in enumerate(_BUSES):
            m = Marker()
            m.header.frame_id = 'map'
            m.header.stamp    = stamp
            m.ns              = 'buses'
            m.id              = i
            m.type            = Marker.CUBE
            m.action          = Marker.ADD

            m.pose.position.x = cx
            m.pose.position.y = cy
            m.pose.position.z = _Z_CENTER
            m.pose.orientation.z = math.sin(yaw / 2.0)
            m.pose.orientation.w = math.cos(yaw / 2.0)

            m.scale.x = sx
            m.scale.y = sy
            m.scale.z = _BUS_HEIGHT

            m.color.r = r
            m.color.g = g
            m.color.b = b
            m.color.a = _ALPHA

            m.lifetime.sec = 0   # 영구 표시

            # 버스 이름 텍스트 마커
            t = Marker()
            t.header   = m.header
            t.ns       = 'bus_labels'
            t.id       = i
            t.type     = Marker.TEXT_VIEW_FACING
            t.action   = Marker.ADD
            t.pose.position.x = cx
            t.pose.position.y = cy
            t.pose.position.z = _BUS_HEIGHT + 0.5
            t.pose.orientation.w = 1.0
            t.scale.z  = 0.6
            t.color.r  = r
            t.color.g  = g
            t.color.b  = b
            t.color.a  = 1.0
            t.text     = f'#{i + 1} {name.upper()}'
            t.lifetime.sec = 0

            array.markers.append(m)
            array.markers.append(t)

        self._pub.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = BusMarkersNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
