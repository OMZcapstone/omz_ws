import importlib.util
from pathlib import Path


EXTERNAL_NODE = Path('/home/omz/omz_ws/external/car_license_plate/illegal_parking_node.py')


def main():
    if not EXTERNAL_NODE.exists():
        raise FileNotFoundError(f'Illegal parking node not found: {EXTERNAL_NODE}')

    spec = importlib.util.spec_from_file_location(
        'external_illegal_parking_node',
        EXTERNAL_NODE,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
