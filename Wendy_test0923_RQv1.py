"""Interactive FAIRINO test for the supplied DaHuan Lua and MG90S_DaHuan.
One move followed by one status snapshot; no background API polling.
No controller gripper configuration is changed by this script.
"""
import argparse
import time
from fairino import Robot

def check_rc(name, result):
    print(f"{name}: {result!r}", flush=True)
    if result != 0:
        raise RuntimeError(f"{name} failed; stop testing and save both logs.")

def status(robot):
    # Keep raw returns: SDK releases differ between flat and nested tuples.
    print("GetGripperMotionDone =", repr(robot.GetGripperMotionDone()), flush=True)
    print("GetGripperCurPosition =", repr(robot.GetGripperCurPosition()), flush=True)
    print("Feedback may be cached; MG90S position/completion are NOT measured.", flush=True)

def initialize(robot):
    check_rc("ActGripper(1, 1)", robot.ActGripper(1, 1))
    # ESP32 midpoint initialization estimates 1500 ms. ACK is not completion.
    time.sleep(2.5)
    print("Initialization settling wait ended; check ESP32 ready=1.", flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", default="192.168.0.52")
    parser.add_argument("--speed", type=int, default=50)
    args = parser.parse_args()
    if not 0 <= args.speed <= 100:
        parser.error("--speed must be 0..100")
    robot = None
    try:
        print(f"Connecting to {args.ip}", flush=True)
        robot = Robot.RPC(args.ip)
        time.sleep(1)
        print("Initializing once at startup: servo will move to midpoint.", flush=True)
        initialize(robot)
        print("Enter position 0..100 (percent), INIT, STATUS, or Q.", flush=True)
        print("Example: 20 -> nominal 63 deg; 80 -> nominal 117 deg.", flush=True)
        while True:
            command = input("position> ").strip()
            if not command:
                continue
            if command.upper() in ("Q", "QUIT", "EXIT"):
                break
            if command.upper() == "INIT":
                initialize(robot)
                status(robot)
                continue
            if command.upper() == "STATUS":
                status(robot)
                continue
            try:
                position = int(command)
            except ValueError:
                print(f"Invalid input {command!r}; enter 0..100, INIT, STATUS, Q.")
                continue
            if not 0 <= position <= 100:
                print("Position must be 0..100 percent.")
                continue
            print(f"Sending {position}% (nominal {45 + 0.9 * position:.1f} deg)", flush=True)
            started = time.monotonic()
            # Single-threaded, blocking request. No additional read while in flight.
            result = robot.MoveGripper(1, position, args.speed, 0, 15000, 0, 0, 0, 0, 0)
            check_rc("MoveGripper", result)
            print(f"Move API returned in {time.monotonic()-started:.2f}s.", flush=True)
            time.sleep(0.5)
            status(robot)
    except (KeyboardInterrupt, EOFError):
        print("\nStopped by user.")
    except Exception as exc:
        print(f"ERROR: {exc}", flush=True)
    finally:
        if robot is not None:
            try:
                robot.CloseRPC()
            except Exception as exc:
                print(f"CloseRPC: {exc}")
        print("Program ended. Closing RPC does not command a servo stop.")

if __name__ == "__main__":
    main()