import os
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share        = get_package_share_directory('bus_assistant')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    stb_share        = get_package_share_directory('slam_toolbox')

    urdf_path   = os.path.join(pkg_share, 'urdf',   'bus_assistant_robot.urdf')
    world_path  = os.path.join(pkg_share, 'worlds', 'bus_stop.sdf')
    bridge_yaml = os.path.join(pkg_share, 'config', 'bridge.yaml')
    slam_params = os.path.join(pkg_share, 'config', 'slam_params.yaml')
    rviz_config = os.path.join(pkg_share, 'config', 'bus_assistant.rviz')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([

        # Gazebo Fortress (server only — avoids ogre2 GUI crash on WSL2)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments=[('gz_args', f'-s -r {world_path}')],
        ),

        # ROS ↔ Gazebo bridge
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            parameters=[{'config_file': bridge_yaml}],
            output='screen',
        ),

        # Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
            output='screen',
        ),

        # Spawn robot at origin
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-topic', 'robot_description',
                '-name',  'bus_assistant_robot',
                '-x', '0', '-y', '0', '-z', '0.11', '-Y', '0',
            ],
            output='screen',
        ),

        # SLAM Toolbox (online async mapping)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(stb_share, 'launch', 'online_async_launch.py')
            ),
            launch_arguments={
                'slam_params_file': slam_params,
                'use_sim_time':     'true',
            }.items(),
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
    ])
