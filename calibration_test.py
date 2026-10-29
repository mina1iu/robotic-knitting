"""Preview the calibration sequence. This script does not connect to robots."""
import argparse

from calibration import ARM_NAMES, build_calibration_path, load_calibration


def main():
    """Print one needle's up/down/up poses, or the full grid in row order."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=ARM_NAMES, help='Arm whose X/Y positions to use')
    parser.add_argument('--needle', nargs=2, type=int, metavar=('COLUMN', 'ROW'),
                        help='Preview only this needle; otherwise preview all 36')
    args = parser.parse_args()
    data = load_calibration()
    needles = [args.needle] if args.needle else [(x, y) for y in range(6) for x in range(6)]
    try:
        # Build the complete plan first, so missing points cannot produce a partial run.
        path = build_calibration_path(args.arm, needles, data=data)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    arm = data['arms'][args.arm]
    print(f"PREVIEW ONLY: {args.arm}, IP {arm['ip']}, tool {arm['tool']}, user {arm['user']}")
    for step in path:
        print(f"Needle {step['needle']} {step['stage']:5}: {step['pose']}")


if __name__ == '__main__':
    main()
