from fairino import Robot
import time
import math
import sys

TOOL_ID = 1
USER_ID = 2

RIGHT_MOVE_DISTANCE_MM = 36.0
right_velocity = 10.64       # 速度百分比，不是 mm/s

RIGHT_AO_CHANNEL = 0
RIGHT_OPEN_PERCENT = 13.0
GRIPPER_SETTLE_S = 0.5

DC_MOTOR_ID = 2
SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000

DC_RUN_TIME_S = 2.0          # 与固件保持一致；不会修改固件运行时间
MOTION_TIMEOUT_S = 8.0
POLL_INTERVAL_S = 0.02

POSITION_TOLERANCE_MM = 0.3
ANGLE_TOLERANCE_DEG = 0.3

robotyarn = None
robotright = None


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def check(result, action):
    if result != 0:
        raise RuntimeError(f'{action} failed: return={result}')


def read_status(result, action):
    if not isinstance(result, (tuple, list)) or len(result) != 2:
        raise RuntimeError(f'{action}: unexpected result {result}')

    check(result[0], action)
    return result[1]


def check_robot_error(robot, name):
    codes = read_status(
        robot.GetRobotErrorCode(),
        f'{name} GetRobotErrorCode'
    )

    if not isinstance(codes, (tuple, list)) or len(codes) != 2:
        raise RuntimeError(f'{name}: unexpected error state {codes}')

    if any(code != 0 for code in codes):
        raise RuntimeError(f'{name}: controller fault {codes}')


def motion_done(robot, name):
    state = read_status(
        robot.GetRobotMotionDone(),
        f'{name} GetRobotMotionDone'
    )

    if state not in (0, 1):
        raise RuntimeError(f'{name}: invalid motion state {state}')

    return state


def read_pose(robot, name):
    pose = read_status(
        robot.GetActualTCPPose(),
        f'{name} GetActualTCPPose'
    )

    if (
        not isinstance(pose, (tuple, list))
        or len(pose) != 6
        or not all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for value in pose
        )
    ):
        raise RuntimeError(f'{name}: invalid TCP pose {pose}')

    return list(pose)


def at_target(pose, target):
    position_error = math.sqrt(
        sum((pose[i] - target[i]) ** 2 for i in range(3))
    )

    angles_ok = all(
        abs((pose[i] - target[i] + 180.0) % 360.0 - 180.0)
        <= ANGLE_TOLERANCE_DEG
        for i in range(3, 6)
    )

    return position_error <= POSITION_TOLERANCE_MM and angles_ok


def check_ready():
    for name, robot in (
        ('.50', robotyarn),
        ('.52', robotright),
    ):
        check_robot_error(robot, name)

        if motion_done(robot, name) != 1:
            raise RuntimeError(f'{name}: already moving; aborted')

    # 只有 .52 会移动，因此检查 .52 的工具和工件坐标系。
    tool_id = read_status(
        robotright.GetActualTCPNum(), '.52 GetActualTCPNum'
    )
    user_id = read_status(
        robotright.GetActualWObjNum(), '.52 GetActualWObjNum'
    )

    if tool_id != TOOL_ID or user_id != USER_ID:
        raise RuntimeError(
            f'.52 frame mismatch: tool={tool_id}, Wobj={user_id}; '
            f'required tool={TOOL_ID}, Wobj={USER_ID}'
        )


def dc_start():
    # block=1：非阻塞。
    # 只发送 START；DC 运行时长由 ESP32 固件控制。
    check(robotyarn.MoveGripper(
        DC_MOTOR_ID,
        1,
        SPEED,
        FORCE,
        MAX_TIME_MS,
        1, 0, 0, 0, 0
    ), '.50 DC START')


def main():
    global robotyarn, robotright

    if len(sys.argv) != 1:
        raise SystemExit(
            'No command-line arguments supported. No --dry-run mode.'
        )

    settings = (
        RIGHT_MOVE_DISTANCE_MM,
        right_velocity,
        DC_RUN_TIME_S,
        MOTION_TIMEOUT_S,
    )
    if not all(math.isfinite(value) for value in settings):
        raise ValueError('Settings must be finite')

    if not (
        RIGHT_MOVE_DISTANCE_MM > 0
        and 0 < right_velocity <= 100
        and 0 < DC_RUN_TIME_S < MOTION_TIMEOUT_S
    ):
        raise ValueError('Invalid settings')

    print('REAL .50 DC + .52 MOTION TEST')
    print('.50: stays at its current position; DC START only.')
    print(
        f'.52: AO={RIGHT_OPEN_PERCENT}%, '
        f'current X + {RIGHT_MOVE_DISTANCE_MM} mm.'
    )
    print(f'.52: tool={TOOL_ID}, Wobj={USER_ID}')
    print(f'.52 velocity={right_velocity}%')
    print('No automatic return. No DC STOP.')
    print('Verify .52 current coordinates and its entire +X path.')

    if input('Type START to connect and execute: ').strip() != 'START':
        print('Cancelled without connection.')
        return

    connected = []
    right_move_attempted = False
    sequence_completed = False

    try:
        robotyarn = Robot.RPC('192.168.0.50')
        connected.append(('.50', robotyarn))

        if not getattr(robotyarn, 'is_connect', False):
            raise RuntimeError('.50 RPC connection failed')

        robotright = Robot.RPC('192.168.0.52')
        connected.append(('.52', robotright))

        if not getattr(robotright, 'is_connect', False):
            raise RuntimeError('.52 RPC connection failed')

        check_ready()

        # 断点 1：停在下面 SetAO 这一行，抓夹指令尚未发送。
        check(robotright.SetAO(
            RIGHT_AO_CHANNEL, RIGHT_OPEN_PERCENT
        ), '.52 open gripper 13%')

        time.sleep(GRIPPER_SETTLE_S)

        # 断点 2：停在下面这一行。
        # 检查抓夹已打开、路径无障碍，然后 F5。
        # 恢复后才读取当前位置。
        check_ready()

        current_pose = read_pose(robotright, '.52')
        target = current_pose.copy()
        target[0] = round(target[0] + RIGHT_MOVE_DISTANCE_MM, 6)

        log(f'.52 current: {current_pose}')
        log(f'.52 target:  {target}')

        # 断点 3：可在下面 check_ready() 行检查 target。
        # 从这里恢复后，不要在 DC START 和运动完成之间暂停。
        check_ready()

        # 如果断点暂停期间手动移动了 .52，终止并重新运行，
        # 避免沿用暂停前计算的目标。
        if not at_target(read_pose(robotright, '.52'), current_pose):
            raise RuntimeError(
                '.52 position changed after capture; restart the program'
            )

        # .50 只启动 DC，不发送任何 MoveL。
        dc_started = time.monotonic()
        dc_start()

        # DC 指令返回后，立即发送 .52 非阻塞运动指令。
        # 两条指令有通信间隔，并非硬件同步启动。
        right_move_attempted = True
        right_started = time.monotonic()

        check(robotright.MoveL(
            target,
            tool=TOOL_ID,
            user=USER_ID,
            vel=right_velocity,
            blendR=0.0
        ), '.52 +X MoveL')

        log('DC START and .52 MoveL accepted')
        log(
            f'.52 dispatch followed DC dispatch by '
            f'{right_started - dc_started:.3f}s'
        )

        right_completed = False

        while True:
            check_robot_error(robotyarn, '.50')
            check_robot_error(robotright, '.52')

            if not right_completed:
                state = motion_done(robotright, '.52')
                pose = read_pose(robotright, '.52')
                now = time.monotonic()

                # 同时检查完成状态和实际终点，
                # 避免把初始 idle 状态误判为运动完成。
                if state == 1 and at_target(pose, target):
                    right_completed = True
                    log(
                        f'.52 arrived after '
                        f'{now - right_started:.3f}s'
                    )
                elif now - right_started >= MOTION_TIMEOUT_S:
                    raise RuntimeError('.52 motion timeout')

            # 等待 .52 到达，并等待固件预设的 DC 周期经过。
            # 时间经过并不等于读取到了 DC 实际停止反馈。
            if (
                right_completed
                and time.monotonic() - dc_started >= DC_RUN_TIME_S
            ):
                sequence_completed = True
                break

            time.sleep(POLL_INTERVAL_S)

    finally:
        # 异常时仅请求 .52 停止运动。
        # 不发送 DC STOP，也不改变抓夹开度。
        if right_move_attempted and not sequence_completed:
            try:
                check(robotright.StopMotion(), '.52 StopMotion')
                log('.52 motion STOP request accepted')
            except Exception as exc:
                log(f'.52 STOP FAILED: {exc}; verify physical state')

        for name, robot in reversed(connected):
            try:
                robot.CloseRPC()
            except Exception as exc:
                log(f'{name} CloseRPC failed: {exc}')

    # 断点 4：运动已完成，连接已关闭。
    log('Completed.')
    log('.50 stayed in place; .52 remains at the +X endpoint.')
    log('.52 gripper remains open at 13%. No DC STOP was sent.')


if __name__ == '__main__':
    main()