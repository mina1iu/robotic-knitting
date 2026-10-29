"""Read manually measured needle X/Y positions and build calibration-test poses.

No robot connections happen here. Edit calibration.json to enter your values.
"""
import json
import math
from pathlib import Path

CALIBRATION_FILE = Path(__file__).with_name('calibration.json')
ARM_NAMES = ('left', 'middle', 'right')


def load_calibration(path=CALIBRATION_FILE):
    """Read the position file beside this module, regardless of the current folder."""
    with open(path) as file:
        data = json.load(file)
    if data.get('schema_version') != 2:
        raise ValueError('Expected schema_version 2: per-needle xy and shared test_heights')
    return data


def check_numbers(values, count):
    """Reject missing values, wrong-length lists, and non-finite numbers."""
    if not isinstance(values, list) or len(values) != count or any(
        type(value) not in (int, float) or not math.isfinite(value)
        for value in values
    ):
        raise ValueError(f'Expected {count} finite numbers; replace null with your measurements')


def get_needle_calibration(arm_name, grid_x, grid_y, *, data=None):
    """Read one arm's independent X/Y pair for a needle ID (column, row).

    A shared row or column ID never forces physical X or Y values to match.
    """
    if arm_name not in ARM_NAMES:
        raise ValueError('Arm must be left, middle, or right')
    if any(type(value) is not int or not 0 <= value <= 5 for value in (grid_x, grid_y)):
        raise ValueError('Needle IDs must be integers from 0 through 5')
    if data is None:
        data = load_calibration()
    key = f'{grid_x},{grid_y}'
    try:
        record = data['arms'][arm_name]['needles'][key]
        if record['status'] != 'measured':
            raise ValueError(f'{arm_name} needle ({key}) has not been measured yet')
        check_numbers(record['xy'], 2)
    except (KeyError, TypeError) as error:
        raise ValueError(f'Missing position data for {arm_name} needle ({key})') from error
    return record


def build_calibration_path(arm_name, needles, *, data=None):
    """Build upper → lower → upper for each needle, in the requested order.

    Both Z heights are stored ONCE in JSON and apply to all needles and arms.
    X/Y and orientation stay identical during each down/up movement.
    Each next needle is approached at upper_z, never at lower_z.
    This returns poses only; it does not send movement commands.
    """
    if data is None:
        data = load_calibration()
    if arm_name not in ARM_NAMES:
        raise ValueError('Arm must be left, middle, or right')
    upper = data['test_heights']['upper_z']
    lower = data['test_heights']['lower_z']
    check_numbers([upper, lower], 2)
    if upper <= lower:
        raise ValueError('upper_z must be greater than lower_z')
    orientation = data['arms'][arm_name]['orientation']
    check_numbers(orientation, 3)
    path = []
    for grid_x, grid_y in needles:
        xy = get_needle_calibration(arm_name, grid_x, grid_y, data=data)['xy']
        for stage, z in [('upper', upper), ('lower', lower), ('upper', upper)]:
            path.append({'needle': [grid_x, grid_y], 'stage': stage,
                         'pose': xy + [z] + orientation})
    return path
