from fairino import Robot
import time
import math
import threading
import queue
import inspect
import sys

# Independent experiment: .50 DC + .51 backward motion only.
# .50 approaches its work pose first. No .51 approach/return; no .52/MG90S commands.
# Any command-line argument is rejected: --dry-run is NOT supported.

# Copy the CURRENT start pose from .51 webpage in tool=1 / user=2.
# Below is the previously calibrated start; verify it physically before START.
LEFT_START_POSE = [13.33, 15.12, 38.0, 0.0, 0.0, 0.0]
YARN_WORK_POSE = [10.95, 22.4, 30.0, 0.0, 0.0, 0.0]
YARN_APPROACH_VEL = 5.0  # existing percentage-speed approach
TOOL_ID = 1
USER_ID = 2
BACKWARD_AXIS = 0       # 0=X, 1=Y, 2=Z in user=2 frame
BACKWARD_SIGN = -1     # previous backward direction: negative X
RETRACT_DISTANCE_MM = 72.0
EXTRA_PULL_MM = 0.0    # optional small extra distance; not tension feedback
TARGET_TIME_S = 5.0
ACCEL_MM_S2 = 100.0
SPEED_CORRECTION = 1.0 # empirical tuning after measuring actual travel duration

GRIPPER_OPEN = 13.0
GRIPPER_SETTLE_S = 0.5
DC_MOTOR_ID = 2
SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000

robotyarn = None
robotleft = None


def check(result, action):
    if result != 0:
        raise RuntimeError(f'{action}: return={result}')


def open_gripper(arm):
    check(arm.SetAO(0, GRIPPER_OPEN), 'left gripper open')
    time.sleep(GRIPPER_SETTLE_S)


def dc_command(value):
    # block=1 allows STOP after 5 s without waiting for firmware's cycle timer.
    check(robotyarn.MoveGripper(
        DC_MOTOR_ID, value, SPEED, FORCE, MAX_TIME_MS, 1, 0, 0, 0, 0
    ), f'DC command {value}')


def stop_left_best_effort():
    # Separate RPC object: do not share the blocking MoveL transport across threads.
    stop_robot = None
    try:
        stop_robot = Robot.RPC('192.168.0.51')
        check(stop_robot.StopMotion(), 'left StopMotion')
    except Exception as exc:
        print(f'STOP FAILED: {exc}. Use physical emergency stop if needed.', flush=True)
    finally:
        if stop_robot is not None:
            try:
                stop_robot.CloseRPC()
            except Exception:
                pass


def main():
    global robotyarn, robotleft
    if len(sys.argv) != 1:
        raise SystemExit('No arguments supported. Aborted BEFORE connecting. --dry-run is not implemented.')
    distance = RETRACT_DISTANCE_MM + EXTRA_PULL_MM
    if (distance <= 0 or EXTRA_PULL_MM < 0 or TARGET_TIME_S <= 0
            or ACCEL_MM_S2 <= 0 or SPEED_CORRECTION <= 0
            or BACKWARD_AXIS not in (0, 1, 2) or BACKWARD_SIGN not in (-1, 1)):
        raise ValueError('Invalid movement parameters')
    # Ideal symmetric trapezoid: distance = v*T - v*v/a.
    discriminant = TARGET_TIME_S ** 2 - 4.0 * distance / ACCEL_MM_S2
    if discriminant < 0:
        raise ValueError('Requested time is too short for the configured acceleration')
    velocity = (2.0 * distance / (TARGET_TIME_S + math.sqrt(discriminant))) * SPEED_CORRECTION
    target = LEFT_START_POSE.copy()
    target[BACKWARD_AXIS] += BACKWARD_SIGN * distance
    print('REAL HARDWARE TEST: .50 will approach its work pose; then DC and .51 run.')
    print(f'.50 approach target: {YARN_WORK_POSE}; tool={TOOL_ID}, user={USER_ID}')
    print(f'tool={TOOL_ID}, user={USER_ID}; start={LEFT_START_POSE}; target={target}')
    print(f'distance={distance:.3f} mm; target duration={TARGET_TIME_S:.3f} s')
    print(f'average={distance / TARGET_TIME_S:.3f} mm/s; commanded cruise={velocity:.3f} mm/s')
    print('Timing is approximate; neither yarn tension nor DC rotation count is measured.')
    print('Manually place .51 at the stated start pose; verify coordinate frames and entire path.')
    print('13% opening must still provide yarn contact/friction for any pulling force.')
    if input('Type START only after checking the above (anything else cancels): ').strip() != 'START':
        print('Cancelled; no connection or motion.')
        return

    gate = threading.Barrier(3)
    abort = threading.Event()
    left_done = threading.Event()
    failures = queue.Queue()
    times = {}
    workers = []

    def move_left():
        try:
            gate.wait(timeout=10)
            if abort.is_set():
                return
            times['left_start'] = time.monotonic()
            check(robotleft.MoveL(
                target, tool=TOOL_ID, user=USER_ID,
                vel=velocity, acc=0.0, ovl=100.0,
                blendR=-1.0, oacc=ACCEL_MM_S2, velAccParamMode=1
            ), 'left backward MoveL')
            times['left_end'] = time.monotonic()
        except BaseException as exc:
            failures.put(('left', str(exc)))
            abort.set()
            gate.abort()
        finally:
            left_done.set()

    def feed_yarn():
        attempted = False
        try:
            gate.wait(timeout=10)
            if abort.is_set():
                return
            times['dc_start'] = time.monotonic()
            attempted = True
            dc_command(1)
            # Stop on nominal deadline or peer failure. Firmware may stop earlier.
            abort.wait(max(0.0, TARGET_TIME_S - (time.monotonic() - times['dc_start'])))
        except BaseException as exc:
            failures.put(('dc', str(exc)))
            abort.set()
            gate.abort()
        finally:
            if attempted:
                try:
                    dc_command(0)
                    times['dc_stop'] = time.monotonic()
                except BaseException as exc:
                    failures.put(('dc_stop', str(exc)))
                    abort.set()

    try:
        robotyarn = Robot.RPC('192.168.0.50')
        robotleft = Robot.RPC('192.168.0.51')
        # Do not silently fall back to percentage velocity with an older SDK.
        parameters = inspect.signature(robotleft.MoveL).parameters
        if 'velAccParamMode' not in parameters or 'oacc' not in parameters:
            raise RuntimeError('Cannot verify physical-speed MoveL support. Check installed SDK; no movement sent.')
        # BREAKPOINT: inspect .50 approach path before executing this call.
        check(robotyarn.MoveL(
            YARN_WORK_POSE, tool=TOOL_ID, user=USER_ID,
            vel=YARN_APPROACH_VEL, blendR=-1.0
        ), 'yarn approach work pose')
        open_gripper(robotleft)
        workers = [threading.Thread(target=move_left), threading.Thread(target=feed_yarn)]
        for worker in workers:
            worker.start()
        gate.wait(timeout=10)
        stop_requested = False
        while any(worker.is_alive() for worker in workers):
            if abort.is_set() and not left_done.is_set() and not stop_requested:
                stop_left_best_effort()
                stop_requested = True
            for worker in workers:
                worker.join(timeout=0.05)
        if not failures.empty():
            raise RuntimeError(list(failures.queue))
        elapsed = times['left_end'] - times['left_start']
        skew = abs(times['dc_start'] - times['left_start'])
        print(f'Host command launch separation: {skew * 1000:.1f} ms (not physical start synchronization)')
        print(f'MoveL call elapsed: {elapsed:.3f} s; nominal distance/call-time: {distance / elapsed:.3f} mm/s')
        print('Done. .51 remains at endpoint with AO=13%; no automatic return.')
    except BaseException:
        abort.set()
        gate.abort()
        if workers and not left_done.is_set():
            stop_left_best_effort()
        raise
    finally:
        abort.set()
        gate.abort()
        for worker in workers:
            if worker.ident is not None:
                worker.join()
        for arm in (robotyarn, robotleft):
            if arm is not None:
                try:
                    arm.CloseRPC()
                except Exception as exc:
                    print(f'CloseRPC failed: {exc}')


if __name__ == '__main__':
    main()

