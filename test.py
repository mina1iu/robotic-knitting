# from example.servo import joint_pos
from fairino import Robot
import time
# A connection is established with the robot controller. A successful connection returns a robot object
robotleft = Robot.RPC('192.168.0.51')
robotright = Robot.RPC('192.168.0.52')

JP1 = [117.408,-86.777,81.499,-87.788,-92.964,92.959]
DP1 = [327.359,-420.973,518.377,-177.199,3.209,114.449]

JP2 = [72.515,-86.774,81.525,-87.724,-91.964,92.958]
DP2 = [-65.169,-529.17,518.018,-177.189,3.119,69.556]

# JP2_h = [72.515,-86.774,81.525,-87.724,-91.964,92.958]
DP2_h = [-65.169,-529.17,528.018,-177.189,3.119,69.556]

JP3 = [89.281,-102.959,81.527,-69.955,-86.755,92.958]
DP3 = [102.939,-378.069,613.165,176.687,1.217,86.329]

desc = [0,0,0,0,0,0]


def startjog(self):
    """机器人点动测试"""
    print("关节1、负向运动、90°、速度30、加速度100")
    error = robot.StartJOG(ref=0,nb=1,dir=0,max_dis=10,vel=30)
    print("StartJOG return ",error)

def stopjog(self):
    """机器人点动减速停止测试"""
    robot.StartJOG(ref=0,nb=1,dir=1,max_dis=90,vel=50)
    time.sleep(3)
    print("关节点动停止")
    error = robot.StopJOG(ref=1)
    print("StopJOG return ",error)

def immstopjog(self):
    """机器人点动立即停止测试"""
    robot.StartJOG(ref=0,nb=1,dir=1,max_dis=90,vel=50)
    time.sleep(3)
    print("关节立即点动停止")
    error = robot.ImmStopJOG()
    print("ImmStopJOG return ",error)

def movej(self):
    """机器人MoveJ测试"""
    JP = [28.166,-108.269,-59.859,-87,94.532,-0.7]
    error = robot.MoveJ(JP,tool=0,user=0, vel=30)
    print("MoveJ return ",error)

def movel(self):
    """机器人MoveL测试"""
    error = robot.MoveL(DP1,tool=0,user=0, vel=30)
    print("MoveL return ",error)

def movecart(self):
    """机器人MoveCart测试"""
    error = robot.MoveCart(DP2,tool=0,user=0, vel=30)
    print("MoveCart return ",error)

def movec(self):
    """机器人MoveC测试"""
    robot.MoveCart(DP2, tool=0, user=0, vel=30)
    error = robot.MoveC(desc_pos_p=DP3,tool_p=0,user_p=0,desc_pos_t=DP1,tool_t=0,user_t=0)
    print("MoveC return ",error)

def circle(self):
    """机器人Circle测试"""
    error = robot.Circle(desc_pos_p=DP3,tool_p=0,user_p=0,desc_pos_t=DP2,tool_t=0,user_t=0)
    print("Circle return ",error)

def newspiral(self):
    """机器人NewSpiral测试"""
    error = robot.NewSpiral(desc_pos=DP2_h,tool=0,user=0,param=[5.0,10,30,10,5,0])
    print("NewSpiral return ",error)

def servoj(self):
    """机器人ServoJ测试"""
    error,pos = robot.GetActualJointPosDegree()
    robot.ServoMoveStart()
    i=0
    while i < 100:
        time.sleep(0.1)
        pos[4] -= 0.2
        error = robot.ServoJ(joint_pos=pos,axisPos=[0,0,0,0])
        i += 1
    robot.ServoMoveEnd()
    print("ServoJ return ",error)

def servocart(self):
    """机器人ServoCart测试"""
    robot.ServoMoveStart()
    pos = [0,0,0.2,0,0,0]
    i=0
    while i < 200:
        # pos[2] += 0.01
        time.sleep(0.008)
        error = robot.ServoCart(mode=1,desc_pos=pos)
        i += 1
    robot.ServoMoveEnd()
    print("ServoCart return ",error)

def splineptp(self):
    """机器人SplinePTP测试"""
    robot.SplineStart()
    error = robot.SplinePTP(joint_pos=JP2,tool=0,user=0)
    robot.SplineEnd()
    print("SplinePTP return ", error)

def newsplineptp(self):
    """机器人NewSplinePTP测试"""
    robot.NewSplineStart(type=0)
    pos1 = [-104.846,309.573,336.647,179.681,-0.419,-92.692]
    pos2 = [-194.846,309.573,336.647,179.681,-0.419,-92.692]
    pos3 = [ -254.846,259.573,336.647,179.681,-0.419,-92.692]
    pos4 = [-304.846,259.573,336.647,179.681,-0.419,-92.692]
    robot.MoveCart(pos1, tool=0, user=0, vel=30)
    robot.NewSplinePoint(desc_pos=pos1, tool=0, user=0, lastFlag=0)
    robot.NewSplinePoint(desc_pos=pos2, tool=0, user=0, lastFlag=0)
    robot.NewSplinePoint(desc_pos=pos3, tool=0, user=0, lastFlag=0)
    error = robot.NewSplinePoint(desc_pos=pos4, tool=0, user=0, lastFlag=1)
    robot.NewSplineEnd()
    print("NewSplinePTP return ", error)

def pointsoffset(self):
    """机器人PointsOffSet测试"""
    robot.PointsOffsetEnable(flag=0,offset_pos=[0,0,-100,0,0,0])
    error = robot.MoveL(DP1, tool=0, user=0)
    robot.PointsOffsetDisable()
    print("PointsOffset return ", error)

def jointoverspeedprotect(self):
    """机器人超速保护测试"""
    error = robot.MoveL(DP1, tool=0,vel=100, user=0,overSpeedStrategy=3,speedPercent=100)
    print("超速保护 return ", error)

def movej_test(self):
    """机器人MoveJ测试"""
    JP = [28.166,-108.269,-59.859,-87,94.532,-0.7]
    DP = [612.425,221.199,567.61,-165.032,4.199,-59.99]

    JP1 = [130.124,-99.15,-110.123,-62.577,90.997,-81.748]
    DP1 = [612.425, 221.199, 567.61, -165.032, 4.199, -59.99]
    error = robot.MoveJ(joint_pos=JP1,tool=0,user=0, vel=30)
    print("MoveJ return ",error)

def fvg3_move(self):
    print(robot.GetActualWObjNum(flag=0))
    print(robot.GetActualToolFlangePose(flag=0))
    print(robot.GetActualTCPPose(flag=0))
    for i in range(0,10):
        for j in range(0,10):
            error = robot.MoveL([i*10, j*10, 50, 0, 0, 0],tool=1, user=1, vel=10)
            robot.WaitMs(250)


def simple_stitch(leftarm, rightarm, needle_location):
    # 1. Coordinate & Offset Definitions
    base_x, base_y = needle_location
    base_x, base_y = base_x + 4, base_y + 1
    
    # The three vertical stages
    z_hover = 100.0         # Safe hovering height (clears the bed and the other arm)
    z_above_needle = 40.0   # Spot right above the needle for approach
    z_push_down = 25.0      # Lowest part to push the yarn down
    
    # Safe clearance distances to prevent arm collisions during transit
    clearance_x = 90.0      # Pushes left arm further left, right arm further right
    clearance_y = -15.0     # Pushes both arms back from the needle bed (change sign depending on your robot's base origin)

    # Rotations
    rot_left = [0.0, 0.0, 0] 
    rot_right = [0.0, 0.0, 0.0] 
    
    offset_dist = 2.9

    velocity=15
    
    # --- LEFT ARM WAYPOINTS ---
    # Hover points pull further left (-clearance_x) and back (+clearance_y)
    hover_west_L = [base_x - offset_dist - clearance_x, base_y + clearance_y, z_hover] + rot_left
    above_west_L = [base_x - offset_dist, base_y, z_above_needle] + rot_left
    push_west_L  = [base_x - offset_dist, base_y, z_push_down] + rot_left
    
    hover_east_L = [base_x + offset_dist - clearance_x, base_y + clearance_y, z_hover] + rot_left
    above_east_L = [base_x + offset_dist, base_y, z_above_needle] + rot_left
    push_east_L  = [base_x + offset_dist, base_y, z_push_down] + rot_left
    
    # --- RIGHT ARM WAYPOINTS ---
    # Hover points pull further right (+clearance_x) and back (+clearance_y)
    hover_west_R = [base_x - offset_dist + clearance_x, base_y + clearance_y, z_hover] + rot_right
    above_west_R = [base_x - offset_dist, base_y, z_above_needle] + rot_right
    push_west_R  = [base_x - offset_dist, base_y, z_push_down] + rot_right
    
    hover_east_R = [base_x + offset_dist + clearance_x, base_y + clearance_y, z_hover] + rot_right
    above_east_R = [base_x + offset_dist, base_y, z_above_needle] + rot_right
    push_east_R  = [base_x + offset_dist, base_y, z_push_down] + rot_right


    # ==========================================
    # --- STEP 1: Right arm puts new loop on West
    # ==========================================
    print("Right Arm: Moving to West hover...")
    rightarm.MoveL(hover_west_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Approaching above needle...")
    rightarm.MoveL(above_west_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Pushing down to place loop...")
    rightarm.MoveL(push_west_R, tool=1, user=1, vel=velocity)

    print("Actuating needle bed (AO)...")
    rightarm.SetAO(1, 100.0) 
    time.sleep(0.5)
    
    print("Right Arm: Releasing loop...")
    rightarm.SetDO(1, 0, 0, 0) # Gripper open
    time.sleep(0.5)
    
    print("Right Arm: Retracting straight up to hover...")
    rightarm.MoveL(above_west_R, tool=1, user=1, vel=velocity)
    rightarm.MoveL(hover_west_R, tool=1, user=1, vel=velocity)
    
    
    # ==========================================
    # --- STEP 2: Left arm grabs East and pulls West
    # ==========================================
    print("Left Arm: Moving to East hover...")
    leftarm.MoveL(hover_east_L, tool=1, user=1, vel=velocity)
    
    print("Left Arm: Approaching above East needle...")
    leftarm.MoveL(above_east_L, tool=1, user=1, vel=velocity)
    
    print("Left Arm: Pushing down to grab East yarn...")
    leftarm.MoveL(push_east_L, tool=1, user=1, vel=velocity)
    
    print("Left Arm: Closing gripper...")
    leftarm.SetDO(1, 1, 0, 0) # Gripper close
    time.sleep(0.5)
    
    print("Left Arm: Pulling yarn toward West (staying low)...")
    leftarm.MoveL(push_west_L, tool=1, user=1, vel=velocity)
    
    print("Left Arm: Releasing pulled yarn...")
    leftarm.SetDO(1, 0, 0, 0) # Gripper open
    time.sleep(0.5)
    
    print("Left Arm: Retracting straight up to hover...")
    leftarm.MoveL(above_west_L, tool=1, user=1, vel=velocity)
    leftarm.MoveL(hover_west_L, tool=1, user=1, vel=velocity)


    # ==========================================
    # --- STEP 3: Right arm picks up West, drops East
    # ==========================================
    print("Right Arm: Moving to West hover...")
    rightarm.MoveL(hover_west_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Approaching above West needle...")
    rightarm.MoveL(above_west_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Pushing down to pick up West yarn...")
    rightarm.MoveL(push_west_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Closing gripper...")
    rightarm.SetDO(1, 1, 0, 0) # Gripper close
    time.sleep(0.5)
    
    print("Right Arm: Lifting yarn above needle for transit...")
    rightarm.MoveL(above_west_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Moving yarn to above East needle...")
    rightarm.MoveL(above_east_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Pushing down to drop yarn in East...")
    rightarm.MoveL(push_east_R, tool=1, user=1, vel=velocity)
    
    print("Right Arm: Dropping yarn...")
    rightarm.SetDO(1, 0, 0, 0) # Gripper open
    time.sleep(0.5)
    
    print("Right Arm: Retracting straight up to hover...")
    rightarm.MoveL(above_east_R, tool=1, user=1, vel=velocity)
    rightarm.MoveL(hover_east_R, tool=1, user=1, vel=velocity)
# movej_test(robot)
#robotright.MoveL([0, 0, 150, 0, 0, 0],tool=1, user=1, vel=10)
simple_stitch(robotleft,robotright,[0,0])
#fvg3_move(robot)
# startjog(robot)
# stopjog(robot)
# immstopjog(robot)
# movej(robot)
# movel(robot)
# movecart(robot)
# movec(robot)
# circle(robot)
# newspiral(robot)
# servoj(robot)
# servocart(robot)
# splineptp(robot)
# newsplineptp(robot)
# pointsoffset(robot)
# jointoverspeedprotect(robot)