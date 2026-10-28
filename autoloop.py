from fairino import Robot
import time

ROBOT_IP = "192.168.0.50"

MG90S_ID = 1
DC_MOTOR_ID = 2

SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000

robot = None


def move_gripper(gripper_id, position, label):
    print(label)

    ret = robot.MoveGripper(
        gripper_id,
        position,
        SPEED,
        FORCE,
        MAX_TIME_MS,
        0,
        0,
        0,
        0,
        0
    )

    print("return =", ret)

    if ret != 0:
        raise RuntimeError(
            f"{label} failed, return = {ret}"
        )


try:
    print(f"Connecting to robot: {ROBOT_IP}")
    robot = Robot.RPC(ROBOT_IP)
    time.sleep(1)

    print("Connected. Starting sequence...\n")

    #init
    move_gripper(
        MG90S_ID,
        50,
        "Init MG90S -> 50%"
    )

    # 1. DC motor START 一次
    move_gripper(
        DC_MOTOR_ID,
        1,
        "[1/3] DC motor -> START"
    )

    # 2. Servo 到 20%
    move_gripper(
        MG90S_ID,
        20,
        "[2/3] MG90S -> 20%"
    )

    # 3. Servo 到 100%
    move_gripper(
        MG90S_ID,
        100,
        "[3/3] MG90S -> 100%"
    )

    print("\nSequence completed.")

except KeyboardInterrupt:
    print("\nProgram interrupted.")

except Exception as e:
    print("\nERROR:", e)

finally:
    if robot is not None:
        try:
            robot.CloseRPC()
        except Exception:
            pass

    print("Program ended.")