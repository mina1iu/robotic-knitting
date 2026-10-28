from fairino import Robot
import time
import sys

ROBOT_IP = '192.168.0.50'
TOOL_ID = 1
USER_ID = 2
# These are Wobj=2 coordinates. Manually verify start BEFORE each run.
START_POSE = [10.949, 23.425, 54.017, 0.003, -0.001, 0.0]
LIFT_DISTANCE_MM = 10.0  # Distance magnitude; target Z subtracts this value.
velocity = 5  # Percentage, NOT mm/s.
TARGET_TIME_S = 5.0
TIMEOUT_S = 20.0
POLL_INTERVAL_S = 0.02


def check(result, action):
    if result != 0:
        raise RuntimeError(f'{action} failed: {result}')


def read(result, action):
    if not isinstance(result, (list, tuple)) or len(result) != 2:
        raise RuntimeError(f'{action}: unexpected return {result}')
    check(result[0], action)
    return result[1]


def motion_done(robotyarn):
    state = read(robotyarn.GetRobotMotionDone(), 'GetRobotMotionDone')
    if state not in (0, 1):
        raise RuntimeError(f'Invalid motion state: {state}')
    return state


def check_fault(robotyarn):
    codes = read(robotyarn.GetRobotErrorCode(), 'GetRobotErrorCode')
    if not isinstance(codes, (list, tuple)) or len(codes) != 2 or any(codes):
        raise RuntimeError(f'Robot fault/unexpected state: {codes}')


def main():
    if len(sys.argv) != 1:
        raise SystemExit('No arguments supported; no --dry-run mode.')
    if not (0 < velocity <= 100 and LIFT_DISTANCE_MM > 0):
        raise ValueError('Invalid velocity or distance')
    target = START_POSE.copy()
    target[2] = round(target[2] - LIFT_DISTANCE_MM, 6)
    print('真实运动测试：只有 .50 下降，不发送任何电机/夹爪指令。')
    print(f'Tool={TOOL_ID}, Wobj={USER_ID}, velocity={velocity}%')
    print(f'运行前手动确认起点：{START_POSE}')
    print(f'终点：{target}；下降 {LIFT_DISTANCE_MM} mm')
    print('不会自动到起点，也不会自动返回。请确认整个路径无障碍。')
    print('重复测试前必须手动恢复起点；否则10mm平均速度计算无效。')
    if input('确认后输入 START 并回车，其他输入取消：').strip() != 'START':
        print('已取消，未连接。')
        return

    robotyarn = None
    attempted = False
    completed = False
    samples = []
    first_busy = None
    last_print = -1.0
    try:
        robotyarn = Robot.RPC(ROBOT_IP)
        if not getattr(robotyarn, 'is_connect', False):
            raise RuntimeError('RPC未完全连接；未发送运动指令')
        check_fault(robotyarn)
        if motion_done(robotyarn) != 1:
            raise RuntimeError('机器人当前正在运动；取消测试')
        # Check speed API BEFORE sending motion.
        read(robotyarn.GetActualTCPCompositeSpeed(), 'GetActualTCPCompositeSpeed')
        print('已就绪。断点1放在下一行；检查后F5连续运行。', flush=True)
        attempted = True  # BREAKPOINT 1: last pre-motion breakpoint
        started = time.monotonic()
        check(robotyarn.MoveL(
            target, tool=TOOL_ID, user=USER_ID, vel=velocity, blendR=0.0
        ), 'MoveL')
        returned = time.monotonic()
        while True:
            check_fault(robotyarn)
            state = motion_done(robotyarn)
            now = time.monotonic()
            elapsed = now - started
            if elapsed >= TIMEOUT_S:
                raise RuntimeError('运动/状态等待超时，不计算完整行程平均速度')
            if state == 0 and first_busy is None:
                first_busy = now
            if state == 1 and first_busy is not None:
                completed = True
                break
            if first_busy is None and elapsed > 2.0:
                raise RuntimeError('未观察到运动开始；检查起点和状态反馈')
            speeds = read(robotyarn.GetActualTCPCompositeSpeed(),
                          'GetActualTCPCompositeSpeed')
            tcp_speed = float(speeds[0])
            if state == 0:
                samples.append(tcp_speed)
            if elapsed - last_print >= 0.25:
                print(f't={elapsed:.3f}s | 实际TCP速度={tcp_speed:.3f} mm/s', flush=True)
                last_print = elapsed
            time.sleep(POLL_INTERVAL_S)
    finally:
        if robotyarn is not None:
            if attempted and not completed:
                try:
                    check(robotyarn.StopMotion(), 'StopMotion')
                    print('已发送停止请求，请确认实际停止。', flush=True)
                except Exception as exc:
                    print(f'停止请求失败：{exc}；必要时使用实体急停。', flush=True)
            try:
                robotyarn.CloseRPC()
            except Exception as exc:
                print(f'CloseRPC failed: {exc}', flush=True)

    print('\n===== 测速结果 =====')  # BREAKPOINT 2: after cleanup
    print(f'velocity设置：{velocity}%')
    print(f'非阻塞MoveL调用耗时：{returned - started:.3f}s')
    print(f'指令发出至完成状态：{elapsed:.3f}s（包含通信/轮询延迟）')
    print(f'观察到运动中至完成：{now - first_busy:.3f}s（状态采样估算）')
    print(f'实际TCP速度采样峰值：{max(samples, default=0.0):.3f} mm/s')
    print('以下计算仅在实际完成规定10mm行程、无外部暂停时有效：')
    print(f'全程平均速度估算：{LIFT_DISTANCE_MM / elapsed:.3f} mm/s')
    estimate = velocity * elapsed / TARGET_TIME_S
    print(f'10mm行程约5秒的百分比初步估算：{estimate:.3f}%（不自动应用，需复测）')
    print('加减速/限速会影响比例估算；状态完成不代替实际终点检查。')
    print('机械臂留在下方终点，无自动返回。')


if __name__ == '__main__':
    main()

