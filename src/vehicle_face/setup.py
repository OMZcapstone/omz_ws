from setuptools import find_packages, setup

package_name = 'vehicle_face'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yoon',
    maintainer_email='yoon@todo.todo',
    description='자율주행 차량 감정 표현 디스플레이 (도트 매트릭스 표정)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'face_display = vehicle_face.face_display:main',
            'emotion_node = vehicle_face.emotion_node:main',
        ],
    },
)
