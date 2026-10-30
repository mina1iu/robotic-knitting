# from fairino import Robot
# import time
# import sys

# # Only .50. One RPC connection, no worker threads.
# TOOL_ID = 1
# USER_ID = 2
# START_POSE = [7, 23.425, 30, 0.003, -0.001, 0.0]
# LIFT_DISTANCE_MM = 36
# velocity = 10.64  # Percentage; calibrate experimentally for approximately 5 seconds.
# MOVE_TIME_S = 2.5  # Target duration, NOT a motion-duration command.
# DC_DELAY_S = 0.5  # From MoveL dispatch, not measured physical motion onset.
# MOTION_TIMEOUT_S = 8.0
# POLL_INTERVAL_S = 0.02
# DC_MOTOR_ID = 2
# SPEED = 50
# FORCE = 0
# MAX_TIME_MS = 10000
# robotyarn = None


# def log(message):
#     print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


# def check(result, action):
#     if result != 0:
#         raise RuntimeError(f'{action} failed: {result}')


# def read_status(result, action):
#     if not isinstance(result, (tuple, list)) or len(result) != 2:
#         raise RuntimeError(f'{action}: unexpected result {result}')
#     check(result[0], action)
#     return result[1]


# def motion_done():
#     state = read_status(robotyarn.GetRobotMotionDone(), 'GetRobotMotionDone')
#     if state not in (0, 1):
#         raise RuntimeError(f'Invalid motion state: {state}')
#     return state


# def check_robot_error():
#     codes = read_status(robotyarn.GetRobotErrorCode(), 'GetRobotErrorCode')
#     if not isinstance(codes, (tuple, list)) or len(codes) != 2:
#         raise RuntimeError(f'Unexpected robot error state: {codes}')
#     if any(code != 0 for code in codes):
#         raise RuntimeError(f'Controller fault: {codes}')


# def dc_command(value):
#     # block=1: nonblocking for both START and STOP.
#     check(robotyarn.MoveGripper(
#         DC_MOTOR_ID, value, SPEED, FORCE, MAX_TIME_MS, 1, 0, 0, 0, 0
#     ), f'DC {value}')
#     log(f'DC {value}: command accepted (not physical-state confirmation)')


# def main():
#     global robotyarn
#     if len(sys.argv) != 1:
#         raise SystemExit('No command-line arguments supported. No --dry-run mode.')
#     if not (0 < velocity <= 100 and LIFT_DISTANCE_MM > 0
#             and 0 <= DC_DELAY_S < MOVE_TIME_S < MOTION_TIMEOUT_S):
#         raise ValueError('Invalid settings')
#     target = START_POSE.copy()
#     target[2] = round(target[2] + LIFT_DISTANCE_MM, 6)
#     print('REAL .50 MOTION TEST: one RPC connection')
#     print(f'Tool={TOOL_ID}, Wobj={USER_ID}')
#     print(f'Manually verify current start: {START_POSE}')
#     print(f'Target: {target}; velocity={velocity}%')
#     print('No automatic approach or return. Verify the entire +Z path.')
#     print(f'Target time={MOVE_TIME_S}s; requires speed calibration.')
#     print(f'DC starts ~{DC_DELAY_S}s after MoveL dispatch; stops on completion status.')
#     if input('Type START to connect and execute: ').strip() != 'START':
#         print('Cancelled without connection.')
#         return

#     move_attempted = False
#     completed = False
#     dc_attempted = False
#     stop_errors = []
#     try:
#         robotyarn = Robot.RPC('192.168.0.50')
#         if not getattr(robotyarn, 'is_connect', False):
#             raise RuntimeError('.50 RPC connection failed; no motion sent')
#         check_robot_error()
#         if motion_done() != 1:
#             raise RuntimeError('Robot already moving; aborted')
#         log('Ready. Last pre-motion breakpoint: move_attempted = True')

#         move_attempted = True  # BREAKPOINT 1: before motion. Continue with F5.
#         started = time.monotonic()
#         check(robotyarn.MoveL(
#             target, tool=TOOL_ID, user=USER_ID, vel=velocity, blendR=0.0
#         ), '.50 lift MoveL')
#         # No breakpoints until cleanup has finished.
#         log('MoveL accepted; movement is NOT yet confirmed complete')
#         seen_moving = False
#         while True:
#             check_robot_error()
#             state = motion_done()
#             now = time.monotonic()
#             elapsed = now - started
#             if elapsed >= MOTION_TIMEOUT_S:
#                 raise RuntimeError('Motion/status wait exceeded timeout')
#             if state == 0:
#                 seen_moving = True
#             elif seen_moving:
#                 # Require 0 -> 1 so stale initial idle state is not completion.
#                 completed = True
#                 if not dc_attempted:
#                     raise RuntimeError('Movement ended before DC start; DC not started')
#                 break
#             if not dc_attempted and elapsed >= DC_DELAY_S:
#                 if not seen_moving or state != 0:
#                     raise RuntimeError('Motion not confirmed at DC delay; DC not started')
#                 dc_attempted = True  # Set before call, in case response fails.
#                 dc_started = time.monotonic()
#                 dc_command(1)
#             time.sleep(POLL_INTERVAL_S)
#     finally:
#         # Best-effort network stop; Python pause/crash is not an emergency stop.
#         if robotyarn is not None:
#             if move_attempted and not completed:
#                 try:
#                     check(robotyarn.StopMotion(), 'StopMotion')
#                     log('Motion STOP request accepted')
#                 except Exception as exc:
#                     stop_errors.append(str(exc))
#                     log(f'MOTION STOP FAILED: {exc}; verify hardware/use emergency stop')
#             if dc_attempted:
#                 try:
#                     dc_command(0)
#                 except Exception as exc:
#                     stop_errors.append(str(exc))
#                     log(f'DC STOP FAILED: {exc}; verify hardware/use emergency stop')
#             try:
#                 robotyarn.CloseRPC()
#             except Exception as exc:
#                 log(f'CloseRPC failed: {exc}')
#     if stop_errors:
#         raise RuntimeError(f'Stop requests failed: {stop_errors}')
#     log(f'Completed status observed after {elapsed:.3f}s')  # BREAKPOINT 2
#     log(f'DC dispatch delay={dc_started - started:.3f}s (host timing)')
#     log('DC STOP was sent; verify physical stop. Robot remains at upper endpoint.')


# if __name__ == '__main__':
#     main()

from fairino import Robot
import time
import sys
import math

# Only .50. One RPC connection, no worker threads.
TOOL_ID = 1
USER_ID = 2  # Live TCP pose was verified against the Wobj 2 display on this setup.
LIFT_DISTANCE_MM = 36
velocity = 10.64  # Percentage; calibrate experimentally for approximately 5 seconds.
MOVE_TIME_S = 2.5  # Target duration, NOT a motion-duration command.
DC_DELAY_S = 0.5  # From MoveL dispatch, not measured physical motion onset.
MOTION_TIMEOUT_S = 8.0
POLL_INTERVAL_S = 0.02
DC_MOTOR_ID = 2
SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000
robotyarn = None


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def check(result, action):
    if result != 0:
        raise RuntimeError(f'{action} failed: {result}')


def read_status(result, action):
    if not isinstance(result, (tuple, list)) or len(result) != 2:
        raise RuntimeError(f'{action}: unexpected result {result}')
    check(result[0], action)
    return result[1]


def motion_done():
    state = read_status(robotyarn.GetRobotMotionDone(), 'GetRobotMotionDone')
    if state not in (0, 1):
        raise RuntimeError(f'Invalid motion state: {state}')
    return state


def check_robot_error():
    codes = read_status(robotyarn.GetRobotErrorCode(), 'GetRobotErrorCode')
    if not isinstance(codes, (tuple, list)) or len(codes) != 2:
        raise RuntimeError(f'Unexpected robot error state: {codes}')
    if any(code != 0 for code in codes):
        raise RuntimeError(f'Controller fault: {codes}')


def dc_command(value):
    # block=1: nonblocking START. Firmware owns the 2-second DC cycle.
    check(robotyarn.MoveGripper(
        DC_MOTOR_ID, value, SPEED, FORCE, MAX_TIME_MS, 1, 0, 0, 0, 0
    ), f'DC {value}')
    log(f'DC {value}: command accepted (not physical-state confirmation)')


def main():
    global robotyarn
    if len(sys.argv) != 1:
        raise SystemExit('No command-line arguments supported. No --dry-run mode.')
    if not (0 < velocity <= 100 and LIFT_DISTANCE_MM > 0
            and 0 <= DC_DELAY_S < MOVE_TIME_S < MOTION_TIMEOUT_S):
        raise ValueError('Invalid settings')
    print('REAL .50 MOTION TEST: one RPC connection')
    print(f'Tool={TOOL_ID}, Wobj={USER_ID}')
    print(f'Lift from live TCP pose: Wobj 2 +Z {LIFT_DISTANCE_MM} mm; velocity={velocity}%')
    print('Keep tool 1 / Wobj 2 selected. Lift follows Wobj 2 +Z.')
    print('No automatic approach or return. Verify the entire +Z path.')
    print(f'Target time={MOVE_TIME_S}s; requires speed calibration.')
    print(f'DC starts ~{DC_DELAY_S}s after MoveL dispatch; firmware must stop it after 2s.')
    if input('Type START to connect and execute: ').strip() != 'START':
        print('Cancelled without connection.')
        return

    move_attempted = False
    completed = False
    dc_attempted = False
    stop_errors = []
    try:
        robotyarn = Robot.RPC('192.168.0.50')
        if not getattr(robotyarn, 'is_connect', False):
            raise RuntimeError('.50 RPC connection failed; no motion sent')
        check_robot_error()
        if motion_done() != 1:
            raise RuntimeError('Robot already moving; aborted')
        log('Ready. Breakpoint 1 is the next line; pose is read after resuming.')
        tool_id = read_status(robotyarn.GetActualTCPNum(), 'GetActualTCPNum')  # BREAKPOINT 1
        user_id = read_status(robotyarn.GetActualWObjNum(), 'GetActualWObjNum')
        if tool_id != TOOL_ID or user_id != USER_ID:
            raise RuntimeError(
                f'Frame mismatch: current tool={tool_id}, Wobj={user_id}; '
                f'select tool={TOOL_ID}, Wobj={USER_ID} before running')
        # Verified on this controller: this read matches the active Wobj 2 display.
        current_pose = read_status(robotyarn.GetActualTCPPose(), 'GetActualTCPPose')
        if (not isinstance(current_pose, (tuple, list)) or len(current_pose) != 6
                or not all(isinstance(v, (int, float)) and math.isfinite(v)
                           for v in current_pose)):
            raise RuntimeError(f'Invalid current TCP pose: {current_pose}')
        target = list(current_pose)
        target[2] = round(target[2] + LIFT_DISTANCE_MM, 6)
        log(f'Current TCP pose: {current_pose}')
        log(f'Target TCP pose: {target}')
        check_robot_error()
        if motion_done() != 1:
            raise RuntimeError('Robot started moving during pose capture; aborted')
        move_attempted = True
        started = time.monotonic()
        check(robotyarn.MoveL(
            target, tool=TOOL_ID, user=USER_ID, vel=velocity, blendR=0.0
        ), '.50 lift MoveL')
        # No breakpoints until cleanup has finished.
        log('MoveL accepted; movement is NOT yet confirmed complete')
        seen_moving = False
        while True:
            check_robot_error()
            state = motion_done()
            now = time.monotonic()
            elapsed = now - started
            if elapsed >= MOTION_TIMEOUT_S:
                raise RuntimeError('Motion/status wait exceeded timeout')
            if state == 0:
                seen_moving = True
            elif seen_moving:
                # Require 0 -> 1 so stale initial idle state is not completion.
                completed = True
                if not dc_attempted:
                    raise RuntimeError('Movement ended before DC start; DC not started')
                break
            if not dc_attempted and elapsed >= DC_DELAY_S:
                if not seen_moving or state != 0:
                    raise RuntimeError('Motion not confirmed at DC delay; DC not started')
                dc_attempted = True  # Set before call, in case response fails.
                dc_started = time.monotonic()
                dc_command(1)
            time.sleep(POLL_INTERVAL_S)
    finally:
        # Best-effort network stop; Python pause/crash is not an emergency stop.
        if robotyarn is not None:
            if move_attempted and not completed:
                try:
                    check(robotyarn.StopMotion(), 'StopMotion')
                    log('Motion STOP request accepted')
                except Exception as exc:
                    stop_errors.append(str(exc))
                    log(f'MOTION STOP FAILED: {exc}; verify hardware/use emergency stop')
            try:
                robotyarn.CloseRPC()
            except Exception as exc:
                log(f'CloseRPC failed: {exc}')
    if stop_errors:
        raise RuntimeError(f'Stop requests failed: {stop_errors}')
    log(f'Completed status observed after {elapsed:.3f}s')  # BREAKPOINT 2
    log(f'DC dispatch delay={dc_started - started:.3f}s (host timing)')
    log('DC STOP is not sent; the firmware controls its 2-second cycle. Robot remains at upper endpoint.')


if __name__ == '__main__':
    main()

