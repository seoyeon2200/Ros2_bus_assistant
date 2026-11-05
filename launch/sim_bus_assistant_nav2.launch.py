import os
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share          = get_package_share_directory('bus_assistant')
    ros_gz_sim_share   = get_package_share_directory('ros_gz_sim')
    bt_navigator_share = get_package_share_directory('nav2_bt_navigator')

    urdf_path   = os.path.join(pkg_share, 'urdf',   'bus_assistant_robot.urdf')
    world_path  = os.path.join(pkg_share, 'worlds', 'bus_stop.sdf')
    bridge_yaml = os.path.join(pkg_share, 'config', 'bridge.yaml')
    nav2_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    rviz_config = os.path.join(pkg_share, 'config', 'bus_assistant.rviz')
    bt_xml      = os.path.join(bt_navigator_share, 'behavior_trees',
                               'navigate_w_replanning_only_if_goal_is_updated.xml')
    default_map = os.path.join(pkg_share, 'maps', 'bus_stop.yaml')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([

        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Path to the map YAML file (created via slam_bus_assistant.launch.py)',
        ),

        # ── Gazebo Fortress (server only) ─────────────────────────────────────
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments=[('gz_args', f'-s -r {world_path}')],
        ),

        # ── ROS ↔ Gazebo bridge ───────────────────────────────────────────────
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            parameters=[{'config_file': bridge_yaml}],
            output='screen',
        ),

        # ── Robot state publisher ─────────────────────────────────────────────
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
            output='screen',
        ),

        # ── odom → base_link TF broadcaster ──────────────────────────────────
        Node(
            package='bus_assistant',
            executable='odom_tf_broadcaster',
            name='odom_tf_broadcaster',
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),

        # ── Spawn robot between red and blue bus ─────────────────────────────
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-topic', 'robot_description',
                '-name',  'bus_assistant_robot',
                '-x', '0.0', '-y', '0.0', '-z', '0.11', '-Y', '0.0',
            ],
            output='screen',
        ),

        # ── Nav2: Map server ──────────────────────────────────────────────────
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            parameters=[nav2_params,
                        {'yaml_filename': LaunchConfiguration('map'),
                         'use_sim_time': True}],
            output='screen',
        ),

        # ── Nav2: AMCL localization ───────────────────────────────────────────
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            parameters=[nav2_params,
                        {'use_sim_time': True,
                         'initial_pose.x':   0.0,
                         'initial_pose.y':   0.0,
                         'initial_pose.yaw': 0.0}],
            output='screen',
        ),

        # ── Nav2: Lifecycle manager — localization ────────────────────────────
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_localization',
            parameters=[{'use_sim_time': True,
                         'autostart':    True,
                         'node_names':   ['map_server', 'amcl']}],
            output='screen',
        ),

        # ── Nav2: Planner server ──────────────────────────────────────────────
        Node(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            parameters=[nav2_params, {'use_sim_time': True}],
            output='screen',
        ),

        # ── Nav2: Controller server ───────────────────────────────────────────
        Node(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            parameters=[nav2_params, {'use_sim_time': True}],
            output='screen',
        ),

        # ── Nav2: Behavior server ─────────────────────────────────────────────
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            parameters=[nav2_params, {'use_sim_time': True}],
            output='screen',
        ),

        # ── Nav2: BT navigator ────────────────────────────────────────────────
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            name='bt_navigator',
            parameters=[nav2_params,
                        {'use_sim_time': True,
                         'default_nav_to_pose_bt_xml': bt_xml}],
            output='screen',
        ),

        # ── Nav2: Lifecycle manager — navigation ──────────────────────────────
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            parameters=[{'use_sim_time': True,
                         'autostart':    True,
                         'node_names':   ['planner_server', 'controller_server',
                                          'behavior_server', 'bt_navigator']}],
            output='screen',
        ),

        # ── RViz ─────────────────────────────────────────────────────────────
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),

        # ── Bus markers (즉시 시작 — Transient Local QoS) ────────────────────
        Node(
            package='bus_assistant',
            executable='bus_markers_node',
            name='bus_markers_node',
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),

        # ── Bus assistant nodes (15초 지연 — Nav2 lifecycle 활성화 후 시작) ─────
        TimerAction(period=15.0, actions=[
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
