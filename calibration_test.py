"""ROBOT ALIGNMENT RUNNER — this is the file to run/debug.

Preview left grid: python3 calibration_test.py left
Move left robot:   python3 calibration_test.py left --execute

Reads calibration.json via calibration.py. Software tests in tests/ are separate.
"""
import argparse
import ipaddress

from calibration import ARM_NAMES, build_calibration_path, load_calibration

# FAIRINO MoveL uses speed percentage: 10 means 10%, not 10 mm/s.
VELOCITY = 10


def execute_path(robot, path, arm):
    """Run an already checked path, waiting for each move to finish.

    Any error ends the sequence immediately. Do not retreat or retry on failure:
    the robot's position may be unknown. No gripper commands are sent.
    """
    for index, step in enumerate(path):
        print(f"Moving: needle {step['needle']} {step['stage']}", flush=True)
        result = robot.MoveL(step['pose'], tool=arm['tool'], user=arm['user'],
                             vel=VELOCITY, blendR=-1.0, retry_on_socket_error=False)
        if type(result) is not int or result != 0:
            raise RuntimeError(f"MoveL failed at {step['pose']}: {result}; no further moves issued")
        # The third move rises back up; X=5 is the last needle in this row.
        if index % 3 == 2 and step['needle'][0] == 5:
            print(f"Row {step['needle'][1]} complete; arm is at upper_z.", flush=True)


def disable_transport_retries(robot):
    """Also disable Python XML-RPC's automatic resend after a broken connection.

    This configures the existing connection only; it sends no robot commands.
    The SDK's own MoveL retry is disabled separately by execute_path.
    """
    transport = robot.robot('transport')
    transport.request = transport.single_request


def main(argv=None):
    """Preview by default; connect only when --execute was explicitly provided."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=ARM_NAMES, help='Arm whose X/Y positions to use')
    parser.add_argument('--needle', nargs=2, type=int, metavar=('COLUMN', 'ROW'),
                        help='Test only this needle; otherwise test all 36, row by row')
    parser.add_argument('--execute', action='store_true', help='Connect and perform REAL robot motion')
    args = parser.parse_args(argv)
    try:
        data = load_calibration()
        needles = [args.needle] if args.needle else [(x, y) for y in range(6) for x in range(6)]
        # Check every requested point BEFORE connecting, not halfway through a run.
        path = build_calibration_path(args.arm, needles, data=data)
        arm = data['arms'][args.arm]
        ipaddress.ip_address(arm['ip'])
        for field in ('tool', 'user'):
            if type(arm[field]) is not int or not 0 <= arm[field] <= 14:
                raise ValueError(f'{field} must be an integer from 0 through 14')
        if not isinstance(arm['coordinate_frame'], str) or not arm['coordinate_frame'].strip():
            raise ValueError('An explicit coordinate-frame description is required')
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))

    mode = 'EXECUTION' if args.execute else 'PREVIEW ONLY'
    print(f"{mode}: {args.arm}, IP {arm['ip']}, tool {arm['tool']}, user {arm['user']}, velocity {VELOCITY}%")
    print(f"Frame: {arm['coordinate_frame']}")
    for step in path:
        print(f"Needle {step['needle']} {step['stage']:5}: {step['pose']}")
    print('Check the route from the CURRENT position to the first upper pose, and clearance between needles.', flush=True)
    if not args.execute:
        return

    # SDK import/connection occurs only in this explicit hardware execution branch.
    from fairino import Robot

    try:
        robot = Robot.RPC(arm['ip'])
        disable_transport_retries(robot)
        execute_path(robot, path, arm)
    except Exception as error:
        parser.exit(1, f'Execution stopped: {error}. No recovery movement attempted.\n')
    print('Complete: left at the final needle at upper_z. No home or park move.')


if __name__ == '__main__':
    main()
