import time
import math
import sys
from fairino import Robot

# ---------- 手动校准区：只填实测值，不按针距推算 Y ----------
# 每一行分别是 .51 / .52 / .50 的工作 Y；同一针内保持各自 Y 不变。
NEEDLE_CALIBRATION = {
    (1, 1): {'left_y': 15.37, 'right_y': 18.30, 'yarn_y': 22.92},
    (1, 2): {'left_y': 29.3,  'right_y': 33.3,  'yarn_y': 37.45},
    (1, 3): {'left_y': 45.3,  'right_y': 48.27,  'yarn_y': 53.45},
    (1, 4): {'left_y': 60.3,  'right_y': 63.76,  'yarn_y': 68.44},
    (1, 5): {'left_y': 74.3,  'right_y': 78.26,  'yarn_y': 83.43},
}
NEEDLE_ORDER = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5)]

# ---------- 固定坐标、固定相对位移 ----------
TOOL_ID = 1
USER_ID = 2
LEFT_WORK_X = 15.37
RIGHT_WORK_X = 11.3
YARN_WORK_X = 7.0
LEFT_PARKING_X = -60.0
RIGHT_INITIAL_PARKING_X = 92.0
PARKING_Z = 40.0
LEFT_DOWN_MM = 12.0              # 40 -> 28
RIGHT_DOWN_MM = 13.0             # 40 -> 27
YARN_WORK_Z = 30.0
YARN_PARK_LIFT_MM = 20.0         # 30 -> 50
YARN_TENSION_LIFT_MM = 36.0      # 当前位姿 Z +36，约30 ->66
RIGHT_DRAG_MM = 10.0
RIGHT_CLEARANCE_MM = 20.0
LEFT_CLEARANCE_MM = 20.0
GROOVE_SPACING_MM = 7.0         # 不沿用旧3.18
RIGHT_PARK_FROM_GROOVE_MM = 40.0 # (13.3+3)+40 = 56.3
LEFT_RELEASE_UP_MM = 4.0
LEFT_RELEASE_BACK_MM = 4.0
ROT_LEFT = [0.0, 0.0, 0.0]
ROT_RIGHT = [0.0, 0.0, 0.0]
ROT_YARN = [0.0, 0.0, 0.0]
VELOCITY = 5.0                   # 普通运动百分比
FEED_VELOCITY = 10.64            # 喂纱上升百分比：初步估算，需实测

# ---------- 抓夹、电机 ----------
GRIPPER_OPEN = 13.0
GRIPPER_CLOSE = 0.0
GRIPPER_RELEASE = 20.0
AO_SETTLE_S = 0.5               # 沿用旧代码的执行后等待；无夹爪反馈
SERVO_SETTLE_S = 0.5            # MG90S非阻塞后留执行时间；非位置确认
MG90S_ID = 1
DC_MOTOR_ID = 2
SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000
DC_DELAY_S = 0.5                # 从上升MoveL发出时开始计时
DC_FEED_SECONDS = 2.5           # 按本次附件；若固件实际是2秒，改为2.0
# 上项只用于等待固件周期结束，不会设置电机转动时长，也不发送DC STOP。
POLL_INTERVAL_S = 0.02
MOTION_TIMEOUT_S = 30.0
FEED_TIMEOUT_S = 10.0
POSITION_TOL_MM = 0.3
ANGLE_TOL_DEG = 0.3

robotyarn = None
robotleft = None
robotright = None


def check(result, action):
    if result != 0:
        raise RuntimeError(f'{action} failed: {result}; sequence aborted')


def read_status(result, action):
    if not isinstance(result, (tuple, list)) or len(result) != 2:
        raise RuntimeError(f'{action}: unexpected result {result}')
    check(result[0], action)
    return result[1]


def current_pose(arm):
    pose = read_status(arm.GetActualTCPPose(), 'GetActualTCPPose')
    if (not isinstance(pose, (tuple, list)) or len(pose) != 6
            or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in pose)):
        raise RuntimeError(f'Invalid TCP pose: {pose}')
    return list(pose)


def motion_done(arm):
    state = read_status(arm.GetRobotMotionDone(), 'GetRobotMotionDone')
    if state not in (0, 1):
        raise RuntimeError(f'Invalid motion state: {state}')
    return state


def check_robot(arm):
    codes = read_status(arm.GetRobotErrorCode(), 'GetRobotErrorCode')
    if not isinstance(codes, (tuple, list)) or len(codes) != 2 or any(codes):
        raise RuntimeError(f'Controller fault / invalid fault state: {codes}')


def at_target(pose, target):
    position_error = math.sqrt(sum((pose[i] - target[i]) ** 2 for i in range(3)))
    angle_errors = [abs((pose[i] - target[i] + 180) % 360 - 180) for i in range(3, 6)]
    return position_error <= POSITION_TOL_MM and max(angle_errors) <= ANGLE_TOL_DEG


def move_arm(arm, target, velocity, label, feed=False):
    """非阻塞MoveL + 软件等待到位；仅feed时在运动中发一次DC START。"""
    check_robot(arm)
    if motion_done(arm) != 1:
        raise RuntimeError(f'{label}: arm already moving')
    if at_target(current_pose(arm), target):
        if feed:
            raise RuntimeError('Feed target already reached; DC not started')
        return  # 跳过已在目标位置的无位移动作
    started = time.monotonic()
    check(arm.MoveL(target, tool=TOOL_ID, user=USER_ID,
                    vel=velocity, blendR=0.0), label)
    dc_started = None
    seen_moving = False
    timeout = FEED_TIMEOUT_S if feed else MOTION_TIMEOUT_S
    while True:
        check_robot(arm)
        state = motion_done(arm)
        pose = current_pose(arm)
        now = time.monotonic()
        elapsed = now - started
        if elapsed >= timeout:
            raise RuntimeError(f'{label}: motion/status timeout')
        if state == 0:
            seen_moving = True
        arrived = state == 1 and at_target(pose, target) and (seen_moving or elapsed >= 0.1)
        if feed and dc_started is None:
            if arrived:
                raise RuntimeError('Lift ended before DC START; feed aborted')
            if elapsed >= DC_DELAY_S:
                if not seen_moving or state != 0:
                    raise RuntimeError('Lift not confirmed at DC delay; DC not started')
                dc_started = time.monotonic()
                check(arm.MoveGripper(DC_MOTOR_ID, 1, SPEED, FORCE,
                                      MAX_TIME_MS, 1, 0, 0, 0, 0), 'DC START')
                print(f'    DC START once; host delay={dc_started-started:.3f}s', flush=True)
        if arrived:
            if not feed:
                return
            # 等待上升到位 AND 固件设定周期经过，才允许下降；不是电机反馈。
            if now - dc_started >= DC_FEED_SECONDS:
                print(f'    Feed lift + firmware wait finished: {elapsed:.3f}s', flush=True)
                return
        time.sleep(POLL_INTERVAL_S)


def close_gripper(arm):
    check(arm.SetAO(0, GRIPPER_CLOSE), 'Gripper close')
    time.sleep(AO_SETTLE_S)


def open_gripper(arm):
    check(arm.SetAO(0, GRIPPER_OPEN), 'Gripper open')
    time.sleep(AO_SETTLE_S)


def release_gripper(arm):
    check(arm.SetAO(0, GRIPPER_RELEASE), 'Gripper release')
    time.sleep(AO_SETTLE_S)


def close_yarn_swing(arm):
    check(arm.MoveGripper(MG90S_ID, 100, SPEED, FORCE, MAX_TIME_MS,
                          1, 0, 0, 0, 0), 'MG90S 100')
    time.sleep(SERVO_SETTLE_S)


def open_yarn_swing(arm):
    check(arm.MoveGripper(MG90S_ID, 0, SPEED, FORCE, MAX_TIME_MS,
                          1, 0, 0, 0, 0), 'MG90S 0')
    time.sleep(SERVO_SETTLE_S)


def feed_yarn(arm, expected_start):
    pose = current_pose(arm)
    if not at_target(pose, expected_start):
        raise RuntimeError('Yarn arm is not at this needle work point; feed aborted')
    target = pose.copy()  # 沿用当前位姿相对上移，不写死起点
    target[2] += YARN_TENSION_LIFT_MM
    move_arm(arm, target, FEED_VELOCITY, 'Yarn tension lift', feed=True)


# ---------- Calibration Databases：保留原来的映射/Needle形式 ----------
def generate_calibration_map():
    return {key: (RIGHT_WORK_X, row['right_y']) for key, row in NEEDLE_CALIBRATION.items()}


PHYSICAL_NEEDLE_MAP = generate_calibration_map()


def get_physical_location(grid_x, grid_y):
    return PHYSICAL_NEEDLE_MAP.get((grid_x, grid_y))


def get_yarn_physical_location(grid_x, grid_y):
    return YARN_WORK_X, NEEDLE_CALIBRATION[(grid_x, grid_y)]['yarn_y']


def validate_calibration():
    missing = []
    for key in NEEDLE_ORDER:
        for name in ('left_y', 'right_y', 'yarn_y'):
            value = NEEDLE_CALIBRATION.get(key, {}).get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                missing.append(f'{key}: {name}')
    if missing:
        raise ValueError('请先填写全部实测Y；未连接机器人：\n  ' + '\n  '.join(missing))
    if not (0 < VELOCITY <= 100 and 0 < FEED_VELOCITY <= 100
            and 0 <= DC_DELAY_S < FEED_TIMEOUT_S
            and DC_FEED_SECONDS > 0
            and DC_DELAY_S + DC_FEED_SECONDS < FEED_TIMEOUT_S):
        raise ValueError('Invalid speed or feed timing')


class Needle:
    def __init__(self, grid_x, grid_y):
        self.grid_x, self.grid_y = grid_x, grid_y
        self.physical_x, self.physical_y = get_physical_location(grid_x, grid_y)
        self.base_x_L = LEFT_WORK_X
        self.base_y_L = NEEDLE_CALIBRATION[(grid_x, grid_y)]['left_y']
        self.base_x_Y, self.base_y_Y = get_yarn_physical_location(grid_x, grid_y)
        self.velocity = VELOCITY
        self.left_parking_x = LEFT_PARKING_X
        self.right_parking_x = self.physical_x + GROOVE_SPACING_MM + RIGHT_PARK_FROM_GROOVE_MM
        self.z_above = PARKING_Z
        self.z_above_R = PARKING_Z
        self.z_push = PARKING_Z - LEFT_DOWN_MM
        self.z_push_R = PARKING_Z - RIGHT_DOWN_MM
        self.z_yarn = YARN_WORK_Z
        self.rot_left, self.rot_right, self.rot_yarn = ROT_LEFT, ROT_RIGHT, ROT_YARN

    def waypoints(self):
        lx, ly, rx, ry = self.base_x_L, self.base_y_L, self.physical_x, self.physical_y
        yx, yy, z = self.base_x_Y, self.base_y_Y, PARKING_Z
        hold_x = lx - LEFT_CLEARANCE_MM
        groove_x = rx + GROOVE_SPACING_MM
        return {
            'yarn_park': [yx, yy, self.z_yarn + YARN_PARK_LIFT_MM] + self.rot_yarn,
            'above_yarn': [yx, yy, self.z_yarn] + self.rot_yarn,
            'left_park': [self.left_parking_x, ly, z] + self.rot_left,
            'right_initial_park': [RIGHT_INITIAL_PARKING_X, ry, z] + self.rot_right,
            'right_park': [self.right_parking_x, ry, z] + self.rot_right,
            'above_east_L': [lx, ly, z] + self.rot_left,
            'push_east_L': [lx, ly, self.z_push] + self.rot_left,
            'hold_close_west_L': [hold_x, ly, z] + self.rot_left,
            'left_release_up': [hold_x, ly, z + LEFT_RELEASE_UP_MM] + self.rot_left,
            'left_release_back': [hold_x - LEFT_RELEASE_BACK_MM, ly, z + LEFT_RELEASE_UP_MM] + self.rot_left,
            'above_west_R': [rx, ry, z] + self.rot_right,
            'push_west_R': [rx, ry, self.z_push_R] + self.rot_right,
            'right_drag': [rx + RIGHT_DRAG_MM, ry, z] + self.rot_right,
            'right_clearance': [rx + RIGHT_CLEARANCE_MM, ry, z] + self.rot_right,
            'above_east_R': [groove_x, ry, z] + self.rot_right,
            'push_east_R': [groove_x, ry, self.z_push_R] + self.rot_right,
        }

    def preparation(self, previous=None):
        w = self.waypoints()
        if previous is None:
            return [
                ('move', 'yarn', w['yarn_park'], '1 yarn parking'),
                ('servo100', 'yarn', None, '1 MG90S 100'),
                ('move', 'left', w['left_park'], '2 left parking'),
                ('open', 'left', None, '2 left AO13'),
                ('move', 'right', w['right_initial_park'], '3 right initial parking'),
                ('open', 'right', None, '3 right AO13'),
            ]
        old = previous.waypoints()
        return [
            ('move', 'left', old['left_park'], 'transition: left retreat at old Y/Z40'),
            ('move', 'right', old['right_park'], 'transition: right parked at old Y/Z40'),
            ('move', 'yarn', old['yarn_park'], 'transition: yarn rise at old Y to Z50'),
            ('move', 'yarn', w['yarn_park'], 'transition: yarn change Y at Z50'),
            ('servo100', 'yarn', None, 'next needle MG90S 100'),
            ('move', 'left', w['left_park'], 'transition: left change Y at parking X/Z40'),
            ('open', 'left', None, 'next needle left AO13'),
            ('move', 'right', w['right_park'], 'transition: right change Y at parking X/Z40'),
            ('open', 'right', None, 'next needle right AO13'),
        ]

    def stitch_actions(self):
        w = self.waypoints()
        return [
            ('move', 'yarn', w['above_yarn'], '4 yarn descend to work Z30'),
            ('move', 'right', w['above_west_R'], '5 right enter at Z40'),
            ('move', 'right', w['push_west_R'], '6 right descend to Z27'),
            ('close', 'right', None, '7 right AO0 holds feeding yarn'),
            ('feed', 'yarn', w['above_yarn'], '8 yarn +Z36 and delayed DC START'),
            ('move', 'yarn', w['above_yarn'], '9 yarn return to Z30'),
            ('move', 'right', w['above_west_R'], '10 right lift to Z40'),
            # ('move', 'right', w['right_drag'], '11 right X+10'),
            # ('move', 'right', w['above_west_R'], '12 right X-10'),
            ('move', 'right', w['push_west_R'], '13 right descend to Z27'),
            ('open', 'right', None, '14 right AO13 release'),
            ('move', 'right', w['above_west_R'], '15 right lift to Z40'),
            ('move', 'right', w['right_clearance'], '16 right X+20 clearance'),
            ('move', 'left', w['above_east_L'], '17 left enter at Z40'),
            ('move', 'left', w['push_east_L'], '18 left descend to Z28'),
            ('close', 'left', None, '19 left AO0 picks old loop'),
            ('move', 'left', w['above_east_L'], '20 left lift to Z40'),
            ('move', 'left', w['hold_close_west_L'], '21 left X-20 clearance'),
            ('move', 'right', w['above_west_R'], '22 right enter left groove at Z40'),
            ('move', 'right', w['push_west_R'], '23 right descend to Z27'),
            ('close', 'right', None, '24a right AO0 picks new loop'),
            ('move', 'right', w['above_west_R'], '24b right Z+13'),
            ('move', 'right', w['above_east_R'], '24c right X+3 at Z40'),
            ('move', 'right', w['push_east_R'], '24d right Z-13 at right groove'),
            ('release', 'right', None, '24e right AO20 releases new loop'),
            ('move', 'right', w['above_east_R'], '24f right Z+13'),
            ('move', 'right', w['right_park'], '24g right X+40 parks beyond right groove'),
            ('release', 'left', None, '25 left AO20 at current X=-6.7'),
            ('move', 'left', w['left_release_up'], '26 left Z+4'),
            ('move', 'left', w['left_release_back'], '27 left X-4 at Z44'),
            ('move', 'left', w['hold_close_west_L'], '28 left X+4/Z-4 in one MoveL'),
            ('servo0', 'yarn', None, '29 MG90S 0'),
        ]

    def execute_actions(self, actions, leftarm, rightarm, yarnarm):
        arms = {'left': leftarm, 'right': rightarm, 'yarn': yarnarm}
        functions = {'open': open_gripper, 'close': close_gripper,
                     'release': release_gripper, 'servo100': close_yarn_swing,
                     'servo0': open_yarn_swing}
        for kind, name, target, label in actions:
            print(f'Needle ({self.grid_x},{self.grid_y}) | {label} | {target or ""}', flush=True)
            arm = arms[name]
            if kind == 'move':
                move_arm(arm, target, self.velocity, label)
            elif kind == 'feed':
                feed_yarn(arm, target)
            else:
                check_robot(arm)
                functions[kind](arm)

    def simple_stitch(self, leftarm, rightarm, yarnarm):
        self.execute_actions(self.stitch_actions(), leftarm, rightarm, yarnarm)


def print_plan(needle_bed):
    previous = None
    for key in NEEDLE_ORDER:
        needle = needle_bed[key]
        print(f'\n===== Needle {key} =====')
        for kind, arm, pose, label in needle.preparation(previous) + needle.stitch_actions():
            print(f'{label:52s} {arm:5s} {pose if pose is not None else kind}')
        previous = needle


def main():
    global robotyarn, robotleft, robotright, PHYSICAL_NEEDLE_MAP
    if len(sys.argv) != 1:
        raise SystemExit('不支持命令行参数；不会连接。预览请直接运行后输入 PREVIEW。')
    validate_calibration()  # 所有缺失值在 import SDK / RPC / 动作前报出
    PHYSICAL_NEEDLE_MAP = generate_calibration_map()
    needle_bed = {key: Needle(*key) for key in NEEDLE_ORDER}
    print_plan(needle_bed)
    print('\nPREVIEW=只看上述顺序，不连接；START=真实执行五个loop。')
    print('首次parking是从当前位姿直线到表中parking，必须事先检查路径。')
    print('API均非阻塞；软件逐步等运动到位，喂纱步骤除外有意重叠DC。')
    print('AO/MG90S使用执行后等待时间，无机械夹爪位置反馈。')
    print(f'DC固件周期假定{DC_FEED_SECONDS}s；程序不发送DC STOP。')
    if input('请输入 START 执行，其他输入只预览：').strip() != 'START':
        return
    connected = []
    sequence_started = False
    try:
        robotyarn = Robot.RPC('192.168.0.50')
        connected.append(robotyarn)
        robotleft = Robot.RPC('192.168.0.51')
        connected.append(robotleft)
        robotright = Robot.RPC('192.168.0.52')
        connected.append(robotright)
        for arm in connected:
            if not getattr(arm, 'is_connect', False):
                raise RuntimeError('RPC未完全连接；不启动序列')
            tool = read_status(arm.GetActualTCPNum(), 'GetActualTCPNum')
            user = read_status(arm.GetActualWObjNum(), 'GetActualWObjNum')
            if (tool, user) != (TOOL_ID, USER_ID):
                raise RuntimeError(f'坐标系不匹配：tool={tool}, user={user}')
            check_robot(arm)
            if motion_done(arm) != 1:
                raise RuntimeError('有机械臂正在运动；不启动序列')
        previous = None
        sequence_started = True  # BREAKPOINT: 全部动作前检查；之后F5连续执行
        for key in NEEDLE_ORDER:
            needle = needle_bed[key]
            needle.execute_actions(needle.preparation(previous), robotleft, robotright, robotyarn)
            needle.simple_stitch(robotleft, robotright, robotyarn)
            previous = needle
        print('五个loop执行完毕。最后保持第29步状态，不自动返回第一针。')
    except BaseException:
        if sequence_started:
            for arm in connected:
                try:
                    check(arm.StopMotion(), 'StopMotion')
                except Exception as exc:
                    print(f'机械臂停止请求失败：{exc}；请检查实物，必要时急停。', flush=True)
        raise
    finally:
        # 按用户要求无任何DC STOP；异常也不自动打开夹爪或移动回停车点。
        for arm in reversed(connected):
            try:
                arm.CloseRPC()
            except Exception as exc:
                print(f'CloseRPC failed: {exc}', flush=True)


if __name__ == '__main__':
    main()

