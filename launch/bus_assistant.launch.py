"""
bus_assistant.launch.py — 실제 로봇용: 4개 노드 동시 실행
  ros2 launch bus_assistant bus_assistant.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    perception = Node(
        package='bus_assistant',
        executable='perception_node',
        name='perception_node',
        output='screen',
    )

    navigation = Node(
        package='bus_assistant',
        executable='navigation_node',
        name='navigation_node',
        output='screen',
    )

    safety = Node(
        package='bus_assistant',
        executable='safety_node',
        name='safety_node',
        output='screen',
        parameters=[{
            'obstacle_dist': 0.8,
            'fov_deg': 30.0,
        }],
    )

    display = Node(
        package='bus_assistant',
        executable='display_node',
        name='display_node',
        output='screen',
    )

    return LaunchDescription([perception, navigation, safety, display])
