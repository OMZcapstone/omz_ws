from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'joystick_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omz',
    maintainer_email='rmsgh0621@gmail.com',
    description='Logitech F710 joystick teleop for differential drive robots',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'joystick_teleop = joystick_teleop.joystick_teleop_node:main',
        ],
    },
)
