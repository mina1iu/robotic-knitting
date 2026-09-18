"""One requested nominal servo angle; never commands FR5 joint motion.
Run after protocol installation and WebApp activation/initialization.
Values returned by the controller are cached, commanded/estimated, not measured.
"""
import argparse
import time
from fairino import Robot

MIN_ANGLE, MAX_ANGLE = 45.0, 135.0  # must match ESP32 configuration

def pair(result, name):
    # 兼容两种 SDK 返回格式：
    # (error, fault, value)
    # (error, [fault, value])

    if not isinstance(result, (tuple, list)) or not result:
        raise RuntimeError(f"{name}: 无法识别返回结果 {result!r}")

    error = result[0]

    if error != 0:
        raise RuntimeError(f"{name}: SDK 返回错误 {result!r}")

    if len(result) == 3:
        fault = result[1]
        value = result[2]

    elif (
        len(result) == 2
        and isinstance(result[1], (tuple, list))
        and len(result[1]) == 2
    ):
        fault, value = result[1]

    else:
        raise RuntimeError(f"{name}: 无法识别返回格式 {result!r}")

    if fault != 0:
        raise RuntimeError(f"{name}: 设备故障标志 {fault}")

    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ip', required=True)
    parser.add_argument('--angle', type=float, required=True)
    parser.add_argument('--speed', type=int, default=30)
    args = parser.parse_args()
    if not MIN_ANGLE <= args.angle <= MAX_ANGLE:
        parser.error(f'angle must be {MIN_ANGLE}..{MAX_ANGLE}; calibrate before changing range')
    if not 0 <= args.speed <= 100:
        parser.error('speed must be 0..100 (trajectory setting, not measured speed)')
    percent = round((args.angle-MIN_ANGLE)*100/(MAX_ANGLE-MIN_ANGLE))
    nominal = MIN_ANGLE+percent*(MAX_ANGLE-MIN_ANGLE)/100
    robot = Robot.RPC(args.ip)
    try:
        print(f'Target nominal angle {nominal:.1f} deg = {percent}%')
        # 0 = blocking; 0 = parallel-gripper interface reused for this servo.
        # Force 0 is ignored by this protocol. No rotary-gripper mode is used.
        rc = robot.MoveGripper(1, percent, args.speed, 0, 15000, 0, 0, 0, 0, 0)
        if rc != 0:
            raise RuntimeError(f'MoveGripper failed: {rc}; inspect ESP32 serial log')
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            done=pair(robot.GetGripperMotionDone(), 'GetGripperMotionDone')
            pos=pair(robot.GetGripperCurPosition(), 'GetGripperCurPosition')
            angle=MIN_ANGLE+pos*(MAX_ANGLE-MIN_ANGLE)/100
            print(f'controller cache: commanded={angle:.1f} deg, estimated_done={done}')
            if done==1 and abs(pos-percent)<=1:
                print('ESTIMATED completion reported; physical arrival is NOT verified.')
                return
            time.sleep(0.2)
        raise TimeoutError('No matching completion/position feedback; check query configuration and logs')
    finally:
        robot.CloseRPC()

if __name__=='__main__':
    main()