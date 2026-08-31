

# # from fairino import Robot

# # robotright = Robot.RPC("192.168.0.52")

# # print("Error:", robotright.GetRobotErrorCode())

# # ret, pose = robotright.GetActualTCPPose()
# # print("Current Pose", pose)

# # if ret == 0:

# #     target = pose.copy()

# #     target[2] += 10

# #     print("Target pose:", target)

# #     robotright.MoveL(target, tool=1, user=2, vel=5)

# # robotright.CloseRPC()
# from fairino import Robot
# import time

# print("Connecting RobotRight...")

# robotright = Robot.RPC("192.168.0.52")

# time.sleep(2)

# print("Current error:")
# print(robotright.GetRobotErrorCode())

# print("Current TCP pose:")
# print(robotright.GetActualTCPPose())

# print("Current joints:")
# print(robotright.GetActualJointPosDegree())

# robotright.CloseRPC()
# print("RPC closed.")