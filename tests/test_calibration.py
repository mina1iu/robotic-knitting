"""Offline checks: independent X/Y positions and the upper/lower/upper sequence."""
import copy
import subprocess
import sys
import unittest

from calibration import build_calibration_path, check_numbers, get_needle_calibration, load_calibration


class PositionTests(unittest.TestCase):
    def test_position_file_has_all_108_entries(self):
        """Every arm has a place to enter all 36 needle measurements."""
        data = load_calibration()
        keys = {f'{x},{y}' for x in range(6) for y in range(6)}
        self.assertEqual(set(data['arms']), {'left', 'middle', 'right'})
        for arm in data['arms'].values():
            self.assertEqual(set(arm['needles']), keys)

    def test_independent_arms_and_irregular_rows_and_columns(self):
        """Keep different X/Y values even within the same row or column."""
        data = copy.deepcopy(load_calibration())
        positions = {('left', 2, 1): [31.2, 18.4], ('left', 2, 2): [32.7, 34.8],
                     ('left', 3, 1): [47.1, 19.3], ('middle', 2, 1): [122, -48],
                     ('right', 2, 1): [-65, 84]}
        for (arm, x, y), xy in positions.items():
            data['arms'][arm]['needles'][f'{x},{y}'] = {'xy': xy, 'status': 'measured'}
        for (arm, x, y), xy in positions.items():
            self.assertEqual(get_needle_calibration(arm, x, y, data=data)['xy'], xy)

    def test_path_changes_xy_only_at_upper_z(self):
        """Two needles use the same heights, with vertical down/up at each point."""
        data = copy.deepcopy(load_calibration())
        data['test_heights'] = {'upper_z': 66, 'lower_z': 36}
        for arm in data['arms'].values():
            arm['needles']['0,0'] = {'xy': [1.2, 3.4], 'status': 'measured'}
            arm['needles']['1,0'] = {'xy': [16.7, 3.9], 'status': 'measured'}
        for name in data['arms']:
            path = build_calibration_path(name, [(0,0), (1,0)], data=data)
            self.assertEqual([step['pose'][2] for step in path], [66,36,66,66,36,66])
            self.assertEqual([step['pose'][:2] for step in path], [[1.2,3.4]]*3 + [[16.7,3.9]]*3)
            for previous, current in zip(path, path[1:]):
                if previous['pose'][:2] != current['pose'][:2]:
                    self.assertEqual(previous['pose'][2], 66)
                    self.assertEqual(current['pose'][2], 66)

    def test_reject_unfinished_and_invalid_values(self):
        """Reject unknown coordinates and missing/inverted shared heights."""
        data = copy.deepcopy(load_calibration())
        data['arms']['left']['needles']['0,0']['status'] = 'uncalibrated'
        with self.assertRaises(ValueError):
            get_needle_calibration('left', 0, 0, data=data)
        for arm, x, y in [('unknown',0,0), ('left',6,0), ('left',-1,0)]:
            with self.assertRaises(ValueError):
                get_needle_calibration(arm, x, y, data=data)
        for values in (None, [1], [0,float('nan')], [0,True]):
            with self.assertRaises(ValueError):
                check_numbers(values, 2)
        for heights in ({'upper_z': None, 'lower_z': None}, {'upper_z': 36, 'lower_z': 66}):
            data['test_heights'] = heights
            with self.assertRaises(ValueError):
                build_calibration_path('left', [(0,0)], data=data)

    def test_imports_do_not_connect_to_hardware(self):
        """The preview and stitch modules can be imported without loading the SDK."""
        result = subprocess.run([sys.executable, '-c',
            "import calibration_test, stitch_demo, sys; assert 'fairino' not in sys.modules"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
