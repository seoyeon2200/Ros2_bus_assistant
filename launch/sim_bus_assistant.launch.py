import os
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share       = get_package_share_directory('bus_assistant')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    urdf_path   = os.path.join(pkg_share, 'urdf',   'bus_assistant_robot.urdf')
    world_path  = os.path.join(pkg_share, 'worlds', 'bus_stop.sdf')
    rviz_config = os.path.join(pkg_share, 'config', 'bus_assistant.rviz')
    bridge_yaml = os.path.join(pkg_share, 'config', 'bridge.yaml')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([

        # ── Gazebo Fortress ──────────────────────────────────────────
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments=[('gz_args', f'-s -r {world_path}')],
        ),

        # ── ROS ↔ Gazebo 브리지 ──────────────────────────────────────
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            parameters=[{'config_file': bridge_yaml}],
            output='screen',
        ),

        # ── robot_state_publisher ─────────────────────────────────────
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description,
                         'use_sim_time': True}],
            output='screen',
        ),

        # ── 로봇 스폰 ────────────────────────────────────────────────
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-topic', 'robot_description',
                '-name',  'bus_assistant_robot',
                '-z',     '0.11',
            ],
            output='screen',
        ),

        # ── RViz ─────────────────────────────────────────────────────
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),

        # ── 애플리케이션 노드 (Gazebo 안정화 후 3초 지연) ─────────────
        TimerAction(period=3.0, actions=[
            Node(package='bus_assistant', executable='perception_node',
                 name='perception_node', output='screen',
                 parameters=[{'use_sim_time': True}]),
            Node(package='bus_assistant', executable='navigation_node',
                 name='navigation_node', output='screen',
                 parameters=[{'use_sim_time': True}]),
            Node(package='bus_assistant', executable='safety_node',
                 name='safety_node', output='screen',
                 parameters=[{'use_sim_time': True,
                               'obstacle_dist': 0.8,
                               'fov_deg': 30.0}]),
            Node(package='bus_assistant', executable='display_node',
                 name='display_node', output='screen'),
        ]),
    ])
