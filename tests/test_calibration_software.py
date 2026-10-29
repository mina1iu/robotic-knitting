"""AUTOMATED SOFTWARE CHECKS — not the robot calibration runner.

Run these only when checking code changes:
    python3 -m unittest discover -s tests -v

To move the left robot through the grid, run the separate root script:
    python3 calibration_test.py left --execute

Everything here uses fake robots or reads local data. No hardware is contacted.
"""
import ast
import contextlib
import copy
import io
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from calibration import build_calibration_path, check_numbers, get_needle_calibration, load_calibration
from calibration_test import execute_path, main


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


class ExecutionTests(unittest.TestCase):
    """Use fake robots only: no controller connections in these tests."""

    def make_data(self):
        """Create a complete artificial grid without changing saved measurements."""
        data = copy.deepcopy(load_calibration())
        data['test_heights'] = {'upper_z': 45, 'lower_z': 35}
        for arm in data['arms'].values():
            for key in arm['needles']:
                x, y = map(int, key.split(','))
                arm['needles'][key] = {'xy': [x * 15 + y * .1, y * 15 + x * .2], 'status': 'measured'}
        return data

    def test_execution_order_speed_and_blocking(self):
        data = self.make_data()
        path = build_calibration_path('left', [(x,y) for y in range(6) for x in range(6)], data=data)
        robot = Mock()
        robot.MoveL.return_value = 0
        with contextlib.redirect_stdout(io.StringIO()):
            execute_path(robot, path, data['arms']['left'])
        self.assertEqual(robot.MoveL.call_count, 108)
        for call, step in zip(robot.MoveL.call_args_list, path):
            self.assertEqual(call.args, (step['pose'],))
            self.assertEqual(call.kwargs, {'tool': 1, 'user': 2, 'vel': 10, 'blendR': -1.0, 'retry_on_socket_error': False})

    def test_errors_never_send_a_recovery_move(self):
        data = self.make_data()
        path = build_calibration_path('left', [(0,0), (1,0)], data=data)
        for failure in (42, OSError('connection lost')):
            robot = Mock()
            robot.MoveL.side_effect = [0, failure]
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises((RuntimeError, OSError)):
                execute_path(robot, path, data['arms']['left'])
            self.assertEqual(robot.MoveL.call_count, 2)

    def test_cli_preview_and_invalid_paths_do_not_connect(self):
        data = self.make_data()
        rpc = Mock()
        with patch.dict(sys.modules, {'fairino': SimpleNamespace(Robot=SimpleNamespace(RPC=rpc))}), patch('calibration_test.load_calibration', return_value=data), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            main(['left'])
            rpc.assert_not_called()
            data['arms']['left']['needles']['5,5']['status'] = 'provisional'
            with self.assertRaises(SystemExit):
                main(['left', '--execute'])
            rpc.assert_not_called()

    def test_cli_execute_selects_only_requested_arm(self):
        data = self.make_data()
        robot = Mock()
        robot.MoveL.return_value = 0
        rpc = Mock(return_value=robot)
        with patch.dict(sys.modules, {'fairino': SimpleNamespace(Robot=SimpleNamespace(RPC=rpc))}), patch('calibration_test.load_calibration', return_value=data), contextlib.redirect_stdout(io.StringIO()):
            main(['left', '--needle', '0', '0', '--execute'])
        rpc.assert_called_once_with('192.168.0.51')
        self.assertEqual(robot.MoveL.call_count, 3)
        transport = robot.robot.return_value
        self.assertEqual(transport.request, transport.single_request)

    def test_sdk_opt_out_surfaces_socket_failure_without_retry(self):
        # Extract only MoveL from SDK source: do not import SDK or construct RPC.
        tree = ast.parse(Path('fairino/Robot.py').read_text())
        rpc_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RPC')
        method = copy.deepcopy(next(n for n in rpc_class.body if isinstance(n, ast.FunctionDef) and n.name == 'MoveL'))
        method.decorator_list = []
        scope = {'socket': socket}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<SDK MoveL offline test>', 'exec'), scope)
        wire = Mock()
        wire.GetInverseKin.return_value = [0, 1, 2, 3, 4, 5, 6]
        wire.MoveL.side_effect = OSError('lost reply')
        robot = SimpleNamespace(reconnect_flag=False, GetSafetyCode=lambda: 0, robot=wire)
        with self.assertRaises(OSError):
            scope['MoveL'](robot, [0]*6, 1, 2, retry_on_socket_error=False)
        self.assertEqual(wire.MoveL.call_count, 1)
        robot.reconnect_flag = True
        with self.assertRaises(ConnectionError):
            scope['MoveL'](robot, [0]*6, 1, 2, retry_on_socket_error=False)
        self.assertEqual(wire.MoveL.call_count, 1)


if __name__ == '__main__':
    unittest.main()
