"""
Perception Node — 카메라 영상에서 버스 색상을 HSV 분석으로 인식하여 /bus_color 토픽 발행
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np


# HSV 범위: (lower, upper, 표시 이름)
BUS_COLOR_RANGES = {
    'red': [
        (np.array([0,   120,  70]), np.array([10,  255, 255])),
        (np.array([170, 120,  70]), np.array([180, 255, 255])),
    ],
    'blue': [
        (np.array([100, 100,  50]), np.array([130, 255, 255])),
    ],
    'green': [
        (np.array([40,  60,  50]),  np.array([80,  255, 255])),
    ],
    'yellow': [
        (np.array([20,  100, 100]), np.array([35,  255, 255])),
    ],
}

MIN_AREA = 3000  # 인식할 최소 픽셀 면적


class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')

        self.bridge = CvBridge()

        self.sub_image = self.create_subscription(
            Image, '/camera/image_raw', self._image_cb, 10)

        self.pub_bus_color = self.create_publisher(String, '/bus_color', 10)
        self.pub_debug_image = self.create_publisher(Image, '/bus_detection_image', 10)

        self._last_color = 'none'
        self.get_logger().info('PerceptionNode 시작 — /camera/image_raw 구독 중')

    def _image_cb(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        detected = self._detect_bus_color(hsv)

        if detected != self._last_color:
            self._last_color = detected
            self.get_logger().info(f'버스 색상 감지: {detected}')

        out = String()
        out.data = detected
        self.pub_bus_color.publish(out)

        debug = self._draw_debug(frame, hsv, detected)
        self.pub_debug_image.publish(
            self.bridge.cv2_to_imgmsg(debug, encoding='bgr8'))

    def _detect_bus_color(self, hsv: np.ndarray) -> str:
        best_color = 'none'
        best_area = MIN_AREA

        for color_name, ranges in BUS_COLOR_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                mask |= cv2.inRange(hsv, lower, upper)

            # 노이즈 제거
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            area = int(np.sum(mask > 0))
            if area > best_area:
                best_area = area
                best_color = color_name

        return best_color

    def _draw_debug(self, frame: np.ndarray, hsv: np.ndarray, detected: str) -> np.ndarray:
        out = frame.copy()
        label_colors = {
            'red': (0, 0, 255), 'blue': (255, 0, 0),
            'green': (0, 200, 0), 'yellow': (0, 220, 220), 'none': (180, 180, 180),
        }
        color = label_colors.get(detected, (180, 180, 180))
        cv2.putText(out, f'Bus: {detected}', (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 2)
        return out


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
