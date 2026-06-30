#!/usr/bin/env python3
import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

import yaml


DEFAULT_MAP = Path('/home/omz/omz_ws/src/my_robot_description/maps/current/omz_map.yaml')


def read_pgm(path):
    data = path.read_bytes()
    pos = 0

    def next_token():
        nonlocal pos
        while pos < len(data) and chr(data[pos]).isspace():
            pos += 1
        if pos < len(data) and data[pos] == ord('#'):
            while pos < len(data) and data[pos] not in (ord('\n'), ord('\r')):
                pos += 1
            return next_token()
        start = pos
        while pos < len(data) and not chr(data[pos]).isspace():
            pos += 1
        return data[start:pos].decode('ascii')

    magic = next_token()
    if magic not in ('P5', 'P2'):
        raise ValueError(f'Unsupported PGM format {magic}; expected P5 or P2')

    width = int(next_token())
    height = int(next_token())
    max_value = int(next_token())

    while pos < len(data) and chr(data[pos]).isspace():
        pos += 1

    if max_value > 255:
        raise ValueError('Only 8-bit PGM files are supported')

    if magic == 'P5':
        pixels = bytearray(data[pos:pos + width * height])
        if len(pixels) != width * height:
            raise ValueError('PGM pixel data is shorter than expected')
    else:
        values = data[pos:].split()
        if len(values) != width * height:
            raise ValueError('PGM pixel data length does not match image size')
        pixels = bytearray(int(value) for value in values)

    return width, height, max_value, pixels


def write_pgm(path, width, height, max_value, pixels):
    header = f'P5\n# Edited by paint_keepout_rect.py\n{width} {height}\n{max_value}\n'.encode('ascii')
    path.write_bytes(header + bytes(pixels))


def clamp_rect(x0, y0, x1, y1, width, height):
    left = max(0, min(width - 1, min(x0, x1)))
    right = max(0, min(width - 1, max(x0, x1)))
    top = max(0, min(height - 1, min(y0, y1)))
    bottom = max(0, min(height - 1, max(y0, y1)))
    return left, top, right, bottom


def world_to_pixel(x, y, origin, resolution, height):
    col = round((x - origin[0]) / resolution)
    row = round(height - 1 - ((y - origin[1]) / resolution))
    return int(col), int(row)


def paint_rect(pixels, width, left, top, right, bottom, value):
    for row in range(top, bottom + 1):
        start = row * width + left
        end = row * width + right + 1
        pixels[start:end] = bytes([value]) * (end - start)


def backup_file(path, old_dir):
    old_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    destination = old_dir / f'{path.stem}_{timestamp}{path.suffix}'
    counter = 1
    while destination.exists():
        destination = old_dir / f'{path.stem}_{timestamp}_{counter}{path.suffix}'
        counter += 1
    shutil.copy2(path, destination)
    return destination


def parse_args():
    parser = argparse.ArgumentParser(
        description='Paint rectangular keepout zones into a ROS occupancy map PGM.'
    )
    parser.add_argument(
        '--map',
        default=str(DEFAULT_MAP),
        help='Path to map yaml. Default: current omz_map.yaml',
    )
    parser.add_argument(
        '--rect-pixel',
        nargs=4,
        type=int,
        action='append',
        metavar=('X0', 'Y0', 'X1', 'Y1'),
        help='Pixel rectangle to paint. Origin is top-left of the image.',
    )
    parser.add_argument(
        '--rect-map',
        nargs=4,
        type=float,
        action='append',
        metavar=('X0', 'Y0', 'X1', 'Y1'),
        help='Map-coordinate rectangle in meters.',
    )
    parser.add_argument(
        '--value',
        type=int,
        default=0,
        help='Pixel value to paint. 0=occupied/black, 254=free/white. Default: 0',
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not copy the old PGM to maps/old before editing.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print the rectangles that would be painted without modifying the PGM.',
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Print map image size, resolution, and origin.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.rect_pixel and not args.rect_map and not args.info:
        raise SystemExit('Use --rect-pixel, --rect-map, or --info')

    map_yaml_path = Path(args.map).expanduser().resolve()
    with map_yaml_path.open('r', encoding='utf-8') as stream:
        map_info = yaml.safe_load(stream)

    image_path = Path(map_info['image'])
    if not image_path.is_absolute():
        image_path = map_yaml_path.parent / image_path
    image_path = image_path.resolve()

    width, height, max_value, pixels = read_pgm(image_path)
    resolution = float(map_info['resolution'])
    origin = map_info['origin']

    if args.info:
        print(f'map yaml: {map_yaml_path}')
        print(f'image: {image_path}')
        print(f'size: {width} x {height} px')
        print(f'resolution: {resolution} m/px')
        print(f'origin: {origin}')

    rectangles = []
    for rect in args.rect_pixel or []:
        rectangles.append(clamp_rect(*rect, width, height))

    for rect in args.rect_map or []:
        x0, y0 = world_to_pixel(rect[0], rect[1], origin, resolution, height)
        x1, y1 = world_to_pixel(rect[2], rect[3], origin, resolution, height)
        rectangles.append(clamp_rect(x0, y0, x1, y1, width, height))

    if not rectangles:
        return

    if args.value < 0 or args.value > max_value:
        raise SystemExit(f'--value must be between 0 and {max_value}')

    for left, top, right, bottom in rectangles:
        print(f'painting pixels: x={left}..{right}, y={top}..{bottom}, value={args.value}')
        if not args.dry_run:
            paint_rect(pixels, width, left, top, right, bottom, args.value)

    if args.dry_run:
        print('dry run: map image was not modified')
        return

    if not args.no_backup:
        old_dir = map_yaml_path.parent.parent / 'old'
        backup_path = backup_file(image_path, old_dir)
        print(f'backup: {backup_path}')

    write_pgm(image_path, width, height, max_value, pixels)
    print(f'updated: {image_path}')


if __name__ == '__main__':
    main()
