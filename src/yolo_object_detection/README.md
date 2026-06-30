# YOLO Object Detection for ROS 2

This package runs Ultralytics YOLO on an RGB camera image topic and publishes:

- `/yolo/detections`: JSON detections as `std_msgs/String`
- `/yolo/image`: annotated image as `sensor_msgs/Image`
- `/yolo_depth/detections`: JSON detections with `depth_m`
- `/yolo_depth/image`: annotated image with distance labels
- OpenCV preview window: color, depth, and YOLO annotated image

Default input topic:

```bash
/camera/color/image_raw
```

Default detected classes:

- `person`
- `car`
- `motorcycle`
- `bus`
- `truck`

Each detection includes a high-level `category` field:

- `person`: COCO class `person`
- `vehicle`: COCO classes `car`, `motorcycle`, `bus`, `truck`

## Install YOLO Runtime

```bash
python3 -m pip install ultralytics
```

## Build

```bash
cd /home/omz/omz_ws
colcon build --packages-select yolo_object_detection
source install/setup.bash
```

## Run With Existing Camera

Start the depth camera first, then run:

```bash
ros2 launch yolo_object_detection yolo_detector.launch.py
```

If the RGB topic is different:

```bash
ros2 launch yolo_object_detection yolo_detector.launch.py image_topic:=/camera/color/image_raw
```

## Run Orbbec Camera and YOLO Together

```bash
ros2 launch yolo_object_detection orbbec_yolo.launch.py
```

This opens a preview window with:

- color image
- depth colormap
- YOLOv8n person / vehicle image

Press `q` in the preview window to close it.

If you are running on a robot without a GUI:

```bash
ros2 launch yolo_object_detection orbbec_yolo.launch.py show_preview:=false
```

If your camera model is different:

```bash
ros2 launch yolo_object_detection orbbec_yolo.launch.py camera_model:=gemini2
```

## Run Orbbec Camera and Depth YOLO Together

This uses the RGB image for YOLO and samples the latest depth image around each
box center.

```bash
ros2 launch yolo_object_detection orbbec_depth_yolo.launch.py
```

For the older Orbbec Astra device exposed as USB ID `2bc5:0401`, use the
OpenNI launch instead:

```bash
ros2 launch yolo_object_detection astra_openni_depth_yolo.launch.py
```

Open RViz separately with the annotated image and 3D detection markers:

```bash
rviz2 -d /home/omz/omz_ws/install/yolo_object_detection/share/yolo_object_detection/rviz/yolo_depth.rviz
```

If the depth topic is different:

```bash
ros2 launch yolo_object_detection orbbec_depth_yolo.launch.py depth_topic:=/camera/depth/image_raw
```

If you are running on a robot without a GUI:

```bash
ros2 launch yolo_object_detection orbbec_depth_yolo.launch.py show_preview:=false
```

## Check Topics

```bash
ros2 topic echo /yolo/detections
ros2 topic echo /yolo_depth/detections
ros2 topic echo /yolo_depth/markers
ros2 run rqt_image_view rqt_image_view
```

In `rqt_image_view`, select:

- `/camera/color/image_raw`
- `/camera/depth/image_raw`
- `/yolo/image`
- `/yolo_depth/image`
