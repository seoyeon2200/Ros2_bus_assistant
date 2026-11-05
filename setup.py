from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'bus_assistant'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'config'), glob('config/*.rviz')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.urdf')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lee Seoyeon',
    maintainer_email='yellow917330@gmail.com',
    description='대중교통 승하차 보조 로봇 시스템',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'perception_node      = bus_assistant.perception_node:main',
            'navigation_node      = bus_assistant.navigation_node:main',
            'safety_node          = bus_assistant.safety_node:main',
            'display_node         = bus_assistant.display_node:main',
            'odom_tf_broadcaster  = bus_assistant.odom_tf_broadcaster:main',
            'bus_markers_node     = bus_assistant.bus_markers_node:main',
        ],
    },
)
