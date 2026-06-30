from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'illegal_parking_detector'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omz',
    maintainer_email='omz@example.com',
    description='ROS2 wrapper for illegal parking detection using a keepout mask.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'illegal_parking_node = illegal_parking_detector.illegal_parking_node:main',
        ],
    },
)
