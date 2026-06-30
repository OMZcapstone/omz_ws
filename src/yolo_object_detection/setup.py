from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'yolo_object_detection'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'rviz'),
         glob(os.path.join('rviz', '*.rviz'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omz',
    maintainer_email='omz@example.com',
    description='YOLO object detection node for RGB camera images.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_preview_node = yolo_object_detection.camera_preview_node:main',
            'depth_yolo_detector_node = yolo_object_detection.depth_yolo_detector_node:main',
            'openni_astra_camera_node = yolo_object_detection.openni_astra_camera_node:main',
            'yolo_detector_node = yolo_object_detection.yolo_detector_node:main',
        ],
    },
)
