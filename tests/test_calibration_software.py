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
import xmlrpc.client
from http.client import RemoteDisconnected
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from calibration import build_calibration_path, check_numbers, get_needle_calibration, load_calibration
from calibration_test import VELOCITY, build_alignment_path, disable_transport_retries, execute_path, main


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
        """The calibration and stitch modules can be imported without loading the SDK."""
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
            self.assertTrue(execute_path(robot, path, data['arms']['left']))
        self.assertEqual(robot.MoveL.call_count, 108)
        for call, step in zip(robot.MoveL.call_args_list, path):
            self.assertEqual(call.args, (step['pose'],))
            self.assertEqual(call.kwargs, {'tool': 1, 'user': 2, 'vel': VELOCITY, 'blendR': -1.0, 'retry_on_socket_error': False})

    def test_hover_wraps_unchanged_points_for_each_arm(self):
        data = self.make_data()
        original = copy.deepcopy(data)
        expected = {'left': [-63.254, 14.6, 70, 0, 0, 0],
                    'right': [92.546, 14.6, 70, 0, 0, 0],
                    'middle': [11.9, 69.95, 70, 0, 0, 0]}
        for name, hover in expected.items():
            path = build_alignment_path(name, [(0, 0), (5, 0)], data=data)
            self.assertEqual(path[1:-1], build_calibration_path(name, [(0, 0), (5, 0)], data=data))
            self.assertEqual(path[0]['pose'], path[-1]['pose'])
            for actual, value in zip(path[0]['pose'], hover):
                self.assertAlmostEqual(actual, value)
        self.assertEqual(data, original)
        data['arms']['left']['user'] = 3
        with self.assertRaises(ValueError):
            build_alignment_path('left', [(0, 0)], data=data)

    def test_hover_sequence_stops_at_every_failure(self):
        data = self.make_data()
        path = build_alignment_path('left', [(0, 0)], data=data)
        for index in range(len(path)):
            for failure in (42, OSError('connection lost')):
                robot = Mock()
                robot.MoveL.side_effect = [0] * index + [failure]
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertFalse(execute_path(robot, path, data['arms']['left']))
                self.assertEqual(robot.MoveL.call_count, index + 1)

    def test_errors_never_send_a_recovery_move(self):
        data = self.make_data()
        path = build_calibration_path('left', [(0,0), (1,0)], data=data)
        for failure in (42, OSError('connection lost')):
            robot = Mock()
            robot.MoveL.side_effect = [0, failure]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(execute_path(robot, path, data['arms']['left']))
            self.assertEqual(robot.MoveL.call_count, 2)

    def test_cli_invalid_paths_do_not_connect(self):
        data = self.make_data()
        rpc = Mock()
        with patch.dict(sys.modules, {'fairino': SimpleNamespace(Robot=SimpleNamespace(RPC=rpc))}), patch('calibration_test.load_calibration', return_value=data), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            data['arms']['left']['needles']['5,5']['status'] = 'provisional'
            with self.assertRaises(SystemExit):
                main(['left'])
            rpc.assert_not_called()

    def test_cli_execute_selects_only_requested_arm(self):
        data = self.make_data()
        robot = Mock()
        robot.MoveL.return_value = 0
        rpc = Mock(return_value=robot)
        with patch.dict(sys.modules, {'fairino': SimpleNamespace(Robot=SimpleNamespace(RPC=rpc))}), patch('calibration_test.load_calibration', return_value=data), contextlib.redirect_stdout(io.StringIO()):
            main(['left', '--needle', '0', '0'])
        rpc.assert_called_once_with('192.168.0.51')
        self.assertEqual(robot.MoveL.call_count, 5)
        expected = build_alignment_path('left', [(0, 0)], data=data)
        self.assertEqual([call.args[0] for call in robot.MoveL.call_args_list],
                         [step['pose'] for step in expected])
        transport = robot.robot.return_value
        self.assertNotEqual(transport.request, transport.single_request)

    def test_transport_discards_idle_connections_without_resending(self):
        # Real stdlib transport, but fake connections/requests: no network access.
        transport = xmlrpc.client.Transport()
        robot = SimpleNamespace(robot=Mock(return_value=transport))
        disable_transport_retries(robot)

        def reply(host, handler, body, verbose):
            self.assertEqual(transport._connection, (None, None))
            return (0,)

        transport.single_request = Mock(side_effect=reply)
        for _ in range(2):
            idle_connection = Mock()
            transport._connection = ('controller', idle_connection)
            self.assertEqual(transport.request('controller', '/RPC2', b'fake'), (0,))
            idle_connection.close.assert_called_once_with()
        self.assertEqual(transport.single_request.call_count, 2)

        transport.single_request.reset_mock()
        transport.single_request.side_effect = RemoteDisconnected('lost reply')
        with self.assertRaises(RemoteDisconnected):
            transport.request('controller', '/RPC2', b'fake')
        transport.single_request.assert_called_once_with('controller', '/RPC2', b'fake', False)

    def test_cli_failure_prints_and_returns_without_system_exit(self):
        data = self.make_data()
        for failure in (42, OSError('connection lost')):
            robot = Mock()
            robot.MoveL.side_effect = [0, failure]
            rpc = Mock(return_value=robot)
            output = io.StringIO()
            with patch.dict(sys.modules, {'fairino': SimpleNamespace(Robot=SimpleNamespace(RPC=rpc))}), patch('calibration_test.load_calibration', return_value=data), contextlib.redirect_stdout(output):
                main(['left', '--needle', '0', '0'])
            self.assertEqual(robot.MoveL.call_count, 2)
            self.assertIn('no further moves issued', output.getvalue().lower())
            self.assertNotIn('Complete:', output.getvalue())

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
