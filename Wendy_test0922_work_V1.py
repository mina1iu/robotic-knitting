# #WORKABLE VERSION1 -- ONLY ROTATE ONE TIMES AND CHECK STATUS
# from fairino import Robot
# import time

# ROBOT_IP = "192.168.0.52"

# TARGET_POSITION = 80   # 每次只测试一个位置：0–100
# SPEED = 50
# FORCE = 0             # MG90S 没有力控制
# MAX_TIME_MS = 10000
# READ_INTERVAL = 0.5   # 每500ms查询一次


# def check_return(name, result):
#     print(f"{name} return: {result!r}")

#     if result != 0:
#         raise RuntimeError(f"{name} failed: {result!r}")


# print("Connecting to FAIRINO...")
# robot = Robot.RPC(ROBOT_IP)
# print(f"Connected: {ROBOT_IP}")


# try:
#     # ========================================================
#     # 1. Initialize the gripper once
#     # ========================================================

#     input("\nPress Enter to initialize the servo...")

#     # ret = robot.ActGripper(
#     #     1,  # gripper index
#     #     1   # activate
#     # )

#     # check_return("ActGripper", ret)

#     # ESP32 initialization currently requires about 1.5 seconds
#     print("Waiting 2 seconds for ESP32 initialization...")
#     time.sleep(2)


#     # ========================================================
#     # 2. Send only one position command
#     # ========================================================

#     input(
#         f"\nPress Enter to send position "
#         f"{TARGET_POSITION}%..."
#     )

#     ret = robot.MoveGripper(
#         1,                  # index
#         TARGET_POSITION,    # position: 0–100
#         SPEED,              # speed: 0–100
#         FORCE,              # force placeholder: 0
#         MAX_TIME_MS,        # maximum waiting time
#         0,                  # block
#         0,                  # type
#         0,                  # rotNum
#         0,                  # rotVel
#         0                   # rotTorque
#     )

#     print("MoveGripper return:", ret)

#     if ret != 0:
#         raise RuntimeError(
#             f"MoveGripper failed: {ret}. "
#             "Save the ESP32 serial log before resetting anything."
#         )


#     # ========================================================
#     # 3. Continuously read raw feedback
#     # ========================================================

#     print()
#     print("============================================")
#     print("RAW GetGripperCurPosition() feedback")
#     print("The position is software-commanded position,")
#     print("not a physically measured MG90S angle.")
#     print("Press Ctrl+C to stop.")
#     print("============================================")
#     print()

#     start_time = time.time()

#     while True:
#         result = robot.GetGripperCurPosition()
#         elapsed = time.time() - start_time

#         print(
#             f"[{elapsed:6.2f}s] "
#             f"GetGripperCurPosition = {result!r}",
#             flush=True
#         )

#         time.sleep(READ_INTERVAL)


# except KeyboardInterrupt:
#     print()
#     print("Stopped by user.")


# except Exception as e:
#     print()
#     print("============================================")
#     print("ERROR")
#     print("============================================")
#     print(e)


# finally:
#     print()
#     print("Closing RPC...")

#     try:
#         robot.CloseRPC()
#     except Exception as e:
#         print("CloseRPC warning:", e)

#     print("RPC closed.")




# WORKABLE VERSION2--SET THE TARGET POSITION IN THE PYTHON TERMINAL
from fairino import Robot
import time

ROBOT_IP = "192.168.0.52"
GRIPPER_ID = 1
SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000


def main():
    robot = None

    try:
        print(f"Connecting to {ROBOT_IP}...", flush=True)
        robot = Robot.RPC(ROBOT_IP)
        time.sleep(1)

        print("\n本程序不重复初始化舵机。")
        print("请确认 Arduino 日志中 ready=1、error=0。")
        print("输入位置百分比 0–100，每次回车执行一条命令。")
        print("例如：20 → 标称63°，80 → 标称117°。")
        print("输入 q 退出。\n")

        while True:
            text = input("目标位置 0–100 / q：").strip()

            if text.lower() == "q":
                break

            try:
                position = int(text)
            except ValueError:
                print("请输入整数，例如 20、50、80。\n")
                continue

            if not 0 <= position <= 100:
                print("位置必须在 0–100 之间。\n")
                continue

            nominal_angle = 45 + position * 90 / 100

            print(
                f"\nSending position={position}% "
                f"(nominal angle={nominal_angle:.1f} deg)",
                flush=True
            )

            start_time = time.monotonic()

            ret = robot.MoveGripper(
                GRIPPER_ID,   # 夹爪编号
                position,     # 位置百分比
                SPEED,        # 软件速度百分比
                FORCE,        # MG90S力占位：0
                MAX_TIME_MS,  # 最大等待时间，毫秒
                0,            # 阻塞模式
                0,            # 普通夹爪类型
                0,            # rotNum
                0,            # rotVel
                0             # rotTorque
            )

            elapsed = time.monotonic() - start_time

            print(
                f"MoveGripper return: {ret!r}, "
                f"elapsed: {elapsed:.2f}s",
                flush=True
            )

            if ret != 0:
                print(
                    "移动报错，停止发送后续命令。"
                    "请保存 Arduino 日志，不要立即 Reset。",
                    flush=True
                )
                break

            # 保留原始返回格式，不假设它一定是二元或三元组
            feedback = robot.GetGripperCurPosition()
            print(
                f"GetGripperCurPosition raw: {feedback!r}",
                flush=True
            )

            print(
                "请观察舵机实际动作；"
                "反馈为软件位置，不是测得的真实角度。\n"
            )

    except (KeyboardInterrupt, EOFError):
        print("\nStopped by user.")

    except Exception as e:
        print(f"\nERROR: {e}", flush=True)

    finally:
        if robot is not None:
            try:
                robot.CloseRPC()
            except Exception as e:
                print(f"CloseRPC warning: {e}")

        # 关闭RPC不会关闭舵机PWM，也不等于发送停止命令
        print("Program ended.", flush=True)


if __name__ == "__main__":
    main()

# from fairino import Robot
# import threading
# import queue
# import time

# ROBOT_IP = "192.168.0.52"
# READ_INTERVAL = 2.0

# commands = queue.Queue()


# # 后台只负责接收键盘输入，不调用机器人API
# def keyboard_input():
#     while True:
#         try:
#             text = input().strip()
#         except EOFError:
#             commands.put("q")
#             return

#         if text:
#             commands.put(text)

#         if text.lower() == "q":
#             return


# def main():
#     robot = None

#     try:
#         print(f"Connecting to {ROBOT_IP}...", flush=True)
#         robot = Robot.RPC(ROBOT_IP)
#         time.sleep(1)

#         print("\n请确认 ESP32 已初始化：ready=1、error=0。")
#         print("输入位置 0–100 并回车；输入 q 退出。")
#         print("每2秒显示一次位置API的原始返回值。")
#         print("数据滚动时也可以直接输入命令。\n", flush=True)

#         threading.Thread(
#             target=keyboard_input,
#             daemon=True
#         ).start()

#         start_time = time.monotonic()
#         next_read = time.monotonic()

#         while True:
#             # 优先处理用户输入
#             try:
#                 text = commands.get_nowait()
#             except queue.Empty:
#                 text = None

#             if text is not None:
#                 if text.lower() == "q":
#                     break

#                 try:
#                     position = int(text)
#                 # except ValueError:
#                 #     print("请输入整数0–100，或q退出。", flush=True)
#                 #     continue
#                 except ValueError:
#                     print(
#                         f"收到的实际输入是 {text!r}；请输入整数0–100，或q退出。",
#                         flush=True
#                     )
#                     continue

#                 if not 0 <= position <= 100:
#                     print("位置必须在0–100之间。", flush=True)
#                     continue

#                 print(
#                     f"\nSending position={position}%",
#                     flush=True
#                 )

#                 ret = robot.MoveGripper(
#                     1,          # 夹爪编号
#                     position,   # 位置百分比
#                     50,         # 速度
#                     0,          # 力占位
#                     10000,      # 最大等待时间，毫秒
#                     0,          # 阻塞模式
#                     0,          # type
#                     0,          # rotNum
#                     0,          # rotVel
#                     0           # rotTorque
#                 )

#                 print(
#                     f"MoveGripper position={position} return: {ret!r}",
#                     flush=True
#                 )

#                 if ret != 0:
#                     print(
#                         "移动报错，停止测试。请保留Arduino日志。",
#                         flush=True
#                     )
#                     break

#             # 每2秒查询一次原始位置反馈
#             now = time.monotonic()

#             if now >= next_read:
#                 result = robot.GetGripperCurPosition()
#                 elapsed = time.monotonic() - start_time

#                 print(
#                     f"[{elapsed:7.2f}s] "
#                     f"GetGripperCurPosition = {result!r}",
#                     flush=True
#                 )

#                 next_read = time.monotonic() + READ_INTERVAL

#             time.sleep(0.05)

#     except KeyboardInterrupt:
#         print("\nStopped by user.")

#     except Exception as e:
#         print(f"\nERROR: {e}", flush=True)

#     finally:
#         if robot is not None:
#             try:
#                 robot.CloseRPC()
#             except Exception as e:
#                 print(f"CloseRPC warning: {e}")

#         print("Program ended.", flush=True)


# if __name__ == "__main__":
#     main()