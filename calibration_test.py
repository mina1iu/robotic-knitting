"""ROBOT ALIGNMENT RUNNER — this is the file to run/debug.

Run left robot (REAL MOTION): python3 calibration_test.py left

Reads calibration.json via calibration.py. Software tests in tests/ are separate.
"""
import argparse
import ipaddress

from calibration import ARM_NAMES, build_calibration_path, load_calibration
from stitch_demo import Needle

# FAIRINO MoveL uses speed percentage: 10 means 10%, not 10 mm/s.
VELOCITY = 15


def build_alignment_path(arm_name, needles, *, data):
    """Wrap the unchanged calibration route in the demo's (1, 1) hovers.

    These are the demo's existing targets, not verified collision-free routes.
    The middle target is defined in the demo, though its parking move is disabled.
    """
    path = build_calibration_path(arm_name, needles, data=data)
    arm = data['arms'][arm_name]
    if arm['tool'] != 1 or arm['user'] != 2:
        raise ValueError('Demo hover positions require tool 1 and user frame 2')
    needle = Needle(1, 1)
    hovers = {
        'left': [needle.base_x_L - needle.offset_dist - needle.clearance_x,
                 needle.physical_y, needle.z_hover] + needle.rot_left,
        'right': [needle.physical_x + needle.offset_dist + needle.clearance_x,
                  needle.physical_y, needle.z_hover] + needle.rot_right,
        'middle': [needle.base_x_Y, needle.base_y_Y + needle.yarn_y_hover_offset,
                   needle.z_hover] + needle.rot_yarn,
    }
    return ([{'needle': None, 'stage': 'hover_start', 'pose': hovers[arm_name].copy()}]
            + path
            + [{'needle': None, 'stage': 'hover_end', 'pose': hovers[arm_name].copy()}])


def execute_path(robot, path, arm):
    """Run an already checked path, waiting for each move to finish.

    Any error ends the sequence immediately. Do not retreat or retry on failure:
    the robot's position may be unknown. No gripper commands are sent.
    Return True on completion, or print the failure and return False.
    """
    for index, step in enumerate(path):
        print(f"Moving: needle {step['needle']} {step['stage']}", flush=True)
        try:
            result = robot.MoveL(step['pose'], tool=arm['tool'], user=arm['user'],
                                vel=VELOCITY, blendR=-1.0, retry_on_socket_error=False)
        except Exception as error:
            print(f"Execution stopped at {step['pose']}: {error}. No further moves issued.", flush=True)
            return False
        if type(result) is not int or result != 0:
            print(f"MoveL failed at {step['pose']}: {result}; no further moves issued", flush=True)
            return False
        # A lower → upper move finishes a needle; X=5 ends the row.
        if (step['stage'] == 'upper' and index > 0
                and path[index - 1]['stage'] == 'lower' and step['needle'][0] == 5):
            print(f"Row {step['needle'][1]} complete; arm is at upper_z.", flush=True)
    return True


def disable_transport_retries(robot):
    """Use a fresh HTTP connection per request, without automatic resends.

    Debugger pauses can outlast the controller's HTTP keep-alive timeout.
    Discard the cached connection before sending, rather than retrying a command
    after a lost response (when its execution status could be unknown).
    This configures the transport only; it sends no robot commands.
    The SDK's own MoveL retry is disabled separately by execute_path.
    """
    transport = robot.robot('transport')

    def fresh_request(host, handler, request_body, verbose=False):
        transport.close()
        return transport.single_request(host, handler, request_body, verbose)

    transport.request = fresh_request


def main(argv=None):
    """Run real motion after validating the complete requested path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=ARM_NAMES, help='Arm whose X/Y positions to use')
    parser.add_argument('--needle', nargs=2, type=int, metavar=('COLUMN', 'ROW'),
                        help='Test only this needle; otherwise test all 36, row by row')
    # Keep older commands working; execution is now unconditional.
    parser.add_argument('--execute', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        data = load_calibration()
        needles = [args.needle] if args.needle else [(x, y) for y in range(6) for x in range(6)]
        # Check every requested point BEFORE connecting, not halfway through a run.
        path = build_alignment_path(args.arm, needles, data=data)
        arm = data['arms'][args.arm]
        ipaddress.ip_address(arm['ip'])
        for field in ('tool', 'user'):
            if type(arm[field]) is not int or not 0 <= arm[field] <= 14:
                raise ValueError(f'{field} must be an integer from 0 through 14')
        if not isinstance(arm['coordinate_frame'], str) or not arm['coordinate_frame'].strip():
            raise ValueError('An explicit coordinate-frame description is required')
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))

    print(f"EXECUTION: {args.arm}, IP {arm['ip']}, tool {arm['tool']}, user {arm['user']}, velocity {VELOCITY}%")
    print(f"Frame: {arm['coordinate_frame']}")
    for step in path:
        print(f"Needle {step['needle']} {step['stage']:5}: {step['pose']}")
    print('Check the route from the CURRENT position to the demo hover, both hover transitions, and clearance between needles.', flush=True)
    # SDK import/connection occurs only inside this explicit execution entry point.
    from fairino import Robot

    try:
        robot = Robot.RPC(arm['ip'])
        disable_transport_retries(robot)
        if not execute_path(robot, path, arm):
            return
    except Exception as error:
        print(f'Execution stopped: {error}. No recovery movement attempted.', flush=True)
        return
    print('Complete: returned to the stitch demo hover position.')


if __name__ == '__main__':
    main()
