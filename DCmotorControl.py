from fairino import Robot
import time

ROBOT_IP = "192.168.0.50"

MG90S_ID = 1
DC_MOTOR_ID = 2

SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000

robot = None

try:
    print(f"Connecting to robot: {ROBOT_IP}")
    robot = Robot.RPC(ROBOT_IP)

    time.sleep(1)

    print("Connected.")
    print("")
    print("Commands:")
    print("SERVO 20")
    print("SERVO 50")
    print("SERVO 80")
    print("DC START")
    print("DC REVERSE")
    print("DC STOP")
    print("Q")
    print("")

    while True:
        cmd = input("> ").strip().upper()

        if cmd == "Q":
            break

        # ----------------------------
        # MG90S
        # ----------------------------
        if cmd.startswith("SERVO "):
            try:
                position = int(cmd.split()[1])
            except:
                print("Use: SERVO 20")
                continue

            if position < 0 or position > 100:
                print("Position must be 0-100")
                continue

            print(f"MG90S -> {position}%")

            ret = robot.MoveGripper(
                MG90S_ID,
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
            print()
            continue

        # ----------------------------
        # DC MOTOR FORWARD
        # ----------------------------
        if cmd == "DC START":
            print("DC motor -> START")

            ret = robot.MoveGripper(
                DC_MOTOR_ID,
                1,
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
            print()
            continue

        # ----------------------------
        # DC MOTOR REVERSE
        # ----------------------------
        if cmd == "DC REVERSE":
            print("DC motor -> REVERSE")

            ret = robot.MoveGripper(
                DC_MOTOR_ID,
                2,
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
            print()
            continue

        # ----------------------------
        # DC MOTOR STOP
        # ----------------------------
        if cmd == "DC STOP":
            print("DC motor -> STOP")

            ret = robot.MoveGripper(
                DC_MOTOR_ID,
                0,
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
            print()
            continue

        print("Unknown command")
        print("Use:")
        print("SERVO 20")
        print("SERVO 50")
        print("SERVO 80")
        print("DC START")
        print("DC REVERSE")
        print("DC STOP")
        print("Q")
        print()

except KeyboardInterrupt:
    print("\nStopped.")

except Exception as e:
    print("\nERROR:", e)

finally:
    if robot is not None:
        try:
            robot.CloseRPC()
        except:
            pass

    print("Program ended.")