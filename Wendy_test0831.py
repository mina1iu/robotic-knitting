
# # from fairino import Robot
# # import time

# # robot = Robot.RPC("192.168.0.52")

# # print("Connected")

# # # ONLY send a gripper command.
# # # This does NOT command robot-arm motion.
# # ret = robot.MoveGripper(
# #     1,      # index
# #     50,     # position
# #     50,     # speed
# #     50,     # force
# #     5000,   # max time
# #     1,      # non-blocking
# #     0,      # parallel gripper
# #     0,      # no rotation
# #     0,      # no rotational velocity
# #     0       # no rotational torque
# # )

# # print("MoveGripper result:", ret)

# # time.sleep(2)

# # robot.CloseRPC()
# # print("RPC closed.")
# from fairino import Robot
# import time

# ROBOT_IP = "192.168.0.52"
# READ_INTERVAL = 1   # 1000ms

# print("Connecting to FAIRINO")
# robot = Robot.RPC(ROBOT_IP)
# print(f"Connected: {ROBOT_IP}")


# try:

#     # ========================================================
#     # Send one command
#     # ========================================================

#     print()
#     print("Sending MoveGripper command...")

#     ret = robot.MoveGripper(
#         1,      # index
#         50,     # pos
#         50,     # vel
#         50,     # force
#         5000,   # max_time
#         0,      # block
#         0,      # type
#         0,      # rotNum
#         0,      # rotVel
#         0       # rotTorque
#     )

#     print("MoveGripper return:", ret)

#     print()
#     print("================================")
#     print("RAW GetGripperCurPosition()")
#     print("Do NOT interpret values yet")
#     print("================================")
#     print()

#     start_time = time.time()

#     # ========================================================
#     # Continuously read raw feedback
#     # ========================================================

#     while True:

#         result = robot.GetGripperCurPosition()

#         elapsed = time.time() - start_time

#         print(
#             f"[{elapsed:6.2f}s] "
#             f"(error code, fault, position(motor rotate) percentage) = {result}"
#         )

#         time.sleep(READ_INTERVAL)


# # ============================================================
# # Ctrl+C
# # ============================================================

# except KeyboardInterrupt:

#     print()
#     print("================================")
#     print("Stopped by user")
#     print("================================")


# # ============================================================
# # Error
# # ============================================================

# except Exception as e:

#     print()
#     print("================================")
#     print("ERROR")
#     print("================================")
#     print(e)


# # ============================================================
# # Close RPC
# # ============================================================

# finally:

#     print()
#     print("Closing RPC...")

#     try:
#         robot.CloseRPC()

#     except Exception as e:
#         print("CloseRPC warning:", e)

#     print("RPC closed.Done.")
from fairino import Robot
import time

robot = Robot.RPC("192.168.0.52")

time.sleep(1)

for position in [10, 50, 90]:

    print(f"Sending position = {position}")

    ret = robot.MoveGripper(
        1,
        position,
        50,
        50,
        5000,
        0,
        0,
        0,
        0,
        0
    )

    print("MoveGripper return:", ret)

    time.sleep(2)

robot.CloseRPC()