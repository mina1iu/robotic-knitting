# from example.servo import joint_pos
from fairino import Robot
import time

# A connection is established with the robot controllers.
robotyarn  = Robot.RPC('192.168.0.50')  # Third arm: Yarn Distributor
robotleft  = Robot.RPC('192.168.0.51')
robotright = Robot.RPC('192.168.0.52')

JP1 = [117.408,-86.777,81.499,-87.788,-92.964,92.959]
DP1 = [327.359,-420.973,518.377,-177.199,3.209,114.449]

JP2 = [72.515,-86.774,81.525,-87.724,-91.964,92.958]
DP2 = [-65.169,-529.17,518.018,-177.189,3.119,69.556]

DP2_h = [-65.169,-529.17,528.018,-177.189,3.119,69.556]

JP3 = [89.281,-102.959,81.527,-69.955,-86.755,92.958]
DP3 = [102.939,-378.069,613.165,176.687,1.217,86.329]

desc = [0,0,0,0,0,0]

def close_gripper(arm):
    print("Gripper closing...")
    arm.SetAO(0, 0.0) 
    time.sleep(0.5)

def open_gripper(arm):
    print("Gripper opening...")
    arm.SetAO(0, 15.0) 
    time.sleep(0.5)


# --- Calibration Database ---
def generate_calibration_map():
    safe_map = {}
    
    # Exact physical coordinates measured with the Right Arm
    measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
    measured_y = [-0.4, 14.2, 29.7, 44.3, 60, 74.8]
    
    for x in range(6):
        for y in range(6):
            safe_map[(x, y)] = (measured_x[x], measured_y[y])
            
    return safe_map

PHYSICAL_NEEDLE_MAP = generate_calibration_map()

def get_physical_location(grid_x, grid_y):
    return PHYSICAL_NEEDLE_MAP.get((grid_x, grid_y), None)


# --- Needle Object ---
class Needle:
    def __init__(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        
        physical_coords = get_physical_location(self.grid_x, self.grid_y)
        if physical_coords is None:
            raise ValueError(f"Needle ({self.grid_x}, {self.grid_y}) is out of bounds.")
            
        self.physical_x, self.physical_y = physical_coords
        
        # Arm Offsets
        self.left_x_offset = 2.6          
        self.base_x_L = self.physical_x - self.left_x_offset
        
        # Third Arm (Yarn Distributor) Offset
        self.yarn_x_offset = 30.0
        self.base_x_Y = self.physical_x + self.yarn_x_offset
        
        # --- COLLISION AVOIDANCE HOVER OFFSETS ---
        # Massively increased X clearance so Left stays far left, Right stays far right
        self.clearance_x = 150.0     
        
        # Pulls the yarn arm 100mm deeply back on the Y-axis to wait safely out of the way
        self.yarn_y_hover_offset = 150.0 
        
        # Z-heights for the stages of a stitch
        self.z_hover = 100.0         
        self.z_above = 40.0   
        self.z_push = 26.0      
        
        # Independent diagonal retraction amounts (Y set to 0)
        self.diag_retract_x = 1.5
        self.diag_retract_y = 0.0
        
        self.rot_left = [0.0, 0.0, 0.0] 
        self.rot_right = [0.0, 0.0, 0.0] 
        self.rot_yarn = [0.0, 0.0, 0.0]
        
        self.offset_dist = 1.6
        self.velocity = 15

    def simple_stitch(self, leftarm, rightarm, yarnarm):
        # Local variables for concise waypoint lookup table
        bx, by = self.physical_x, self.physical_y
        bx_L = self.base_x_L
        bx_Y = self.base_x_Y
        yyh = self.yarn_y_hover_offset
        od = self.offset_dist
        cx = self.clearance_x
        zh, za, zp = self.z_hover, self.z_above, self.z_push
        dx, dy = self.diag_retract_x, self.diag_retract_y
        rl, rr, ry = self.rot_left, self.rot_right, self.rot_yarn

        # Pre-calculated physical waypoints for all three arms
        waypoints = {
            # Yarn Distributor Waypoints (Hover is pushed 300mm back on Y)
            "hover_yarn":  [bx_Y, by + yyh, zh] + ry,
            "above_yarn":  [bx_Y, by, za] + ry,
            "push_yarn":   [bx_Y, by, zp] + ry,
            "adjust_yarn": [bx_Y + 15.0, by, zp] + ry, 
            
            # Left Arm Waypoints (Pushed 150mm Left on X during hover)
            "hover_west_L": [bx_L - od - cx, by, zh] + rl,
            "above_west_L": [bx_L - od, by, za] + rl,
            "push_west_L":  [bx_L - od, by, zp] + rl,
            "diagonal_retract_west_L": [bx_L - od - dx, by + dy, za] + rl,
            "above_far_west_L": [bx_L - (od * 8), by, za] + rl,
            "hover_east_L": [bx_L + od - cx, by, zh] + rl,
            "above_east_L": [bx_L + od, by, za] + rl,
            "push_east_L":  [bx_L + od, by, zp] + rl,
            "diagonal_retract_east_L": [bx_L + od - dx, by + dy, za] + rl,
            
            # Right Arm Waypoints (Pushed 150mm Right on X during hover)
            "hover_west_R": [bx - od + cx, by, zh] + rr,
            "above_west_R": [bx - od, by, za] + rr,
            "push_west_R":  [bx - od, by, zp] + rr,
            "diagonal_retract_west_R": [bx - od + dx, by + dy, za] + rr,
            "hover_east_R": [bx + od + cx, by, zh] + rr,
            "above_east_R": [bx + od, by, za] + rr,
            "push_east_R":  [bx + od, by, zp] + rr,
            "diagonal_retract_east_R": [bx + od + dx, by + dy, za] + rr
        }

        # 0. Initialize all to safe parking corners
        print(">> Parking all arms in safe hovers...")
        yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

        # --- YARN DISTRIBUTOR SEQUENCE ---
        print(">> Yarn Arm: Moving in...")
        yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        yarnarm.MoveL(waypoints["push_yarn"], tool=1, user=2, vel=self.velocity)
        
        # [IMAGINARY STEP] Open pincher, lay yarn, close pincher
        # open_gripper(yarnarm)
        # close_gripper(yarnarm)
        # time.sleep(1)
        
        yarnarm.MoveL(waypoints["adjust_yarn"], tool=1, user=2, vel=self.velocity)
        
        # [IMAGINARY STEP] Release yarn to the needle
        # open_gripper(yarnarm)
        
        print(">> Yarn Arm: Retracting to safe hover...")
        yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
        # ---------------------------------

        
        # Step 1: Right arm works while Left is safely parked 150mm away
        print(">> Right Arm: Initiating Step 1...")
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
        open_gripper(rightarm)
        rightarm.MoveL(waypoints["diagonal_retract_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)

        # Step 2: Left arm works while Right is safely parked 150mm away
        print(">> Left Arm: Initiating Step 2...")
        leftarm.MoveL(waypoints["hover_east_L"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        open_gripper(leftarm)
        leftarm.MoveL(waypoints["push_east_L"], tool=1, user=2, vel=self.velocity)
        close_gripper(leftarm)
        
        leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["above_far_west_L"], tool=1, user=2, vel=self.velocity)
        # Return Left Arm to deep safe hover
        leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)

        # Step 3: Right arm works while Left is safely parked
        print(">> Right Arm: Initiating Step 3...")
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        close_gripper(rightarm)
        
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_east_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["push_east_R"], tool=1, user=2, vel=self.velocity)
        open_gripper(rightarm)
        
        rightarm.MoveL(waypoints["diagonal_retract_east_R"], tool=1, user=2, vel=self.velocity)
        # Return Right Arm to deep safe hover
        rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

# --- Execution ---
needle_bed = {}

# Initialize the 6x6 needle grid
for x in range(6):
    for y in range(6):
        needle_bed[(x, y)] = Needle(grid_x=x, grid_y=y)

target_needle = needle_bed[(0, 0)]
#target_needle.simple_stitch(robotleft, robotright)


def test_calibration_path(arm, needle_bed, is_left_arm=False, velocity=15):
    """
    Traces the entire 6x6 needle bed to visually verify physical calibration.
    Moves row by row (Y), gliding across columns (X).
    Applies the pre-calculated left-arm offset if is_left_arm=True.
    """
    z_push = 30.0  # Updated to match your Needle class push depth
    z_hop = z_push + 30.0  
    rot = [0.0, 0.0, 0.0]
    
    arm_name = "Left Arm" if is_left_arm else "Right Arm"
    print(f"\n>> Starting calibration test path for {arm_name}...")
    
    # Helper to quickly grab the correct X-coordinate based on the arm
    def get_target_x(needle_obj):
        return needle_obj.base_x_L if is_left_arm else needle_obj.physical_x

    # 1. Approach safely using Joint Move to avoid straight-line errors
    print(">> Moving to safe home position...")
    safe_hover_joints = [0, 0, 75, 0, 0, 0]
    arm.MoveL(safe_hover_joints, tool=1, user=2, vel=velocity)
    
    # 2. Traverse the Grid
    for y in range(6):
        start_needle = needle_bed[(0, y)]
        target_x = get_target_x(start_needle)
        
        # Hop to start of row
        arm.MoveL([target_x, start_needle.physical_y, z_hop] + rot, tool=1, user=2, vel=velocity)
        arm.MoveL([target_x, start_needle.physical_y, z_push] + rot, tool=1, user=2, vel=velocity)
        
        # Glide across X
        for x in range(6):
            needle = needle_bed[(x, y)]
            target_x = get_target_x(needle)
            arm.MoveL([target_x, needle.physical_y, z_push] + rot, tool=1, user=2, vel=velocity)
            
            # Brief pause at each needle so you can visually verify alignment
            time.sleep(0.3)  
            
        # Hop up at end of row
        end_needle = needle_bed[(5, y)]
        target_x = get_target_x(end_needle)
        arm.MoveL([target_x, end_needle.physical_y, z_hop] + rot, tool=1, user=2, vel=velocity)

    print(f">> Test path complete for {arm_name}. Moving to safe park position.")
    # 3. Retreat safely using Joint Move
    arm.MoveL(safe_hover_joints, tool=1, user=2, vel=velocity)
# ==========================================
# --- EXECUTION ---
# ==========================================

# # Test Right Arm (Default)
robotright.MoveL([.9, -.4, 50] + [0.0, 0.0, 0.0], tool=1, user=2, vel=10)
test_calibration_path(robotright, needle_bed, is_left_arm=False)

# # Test Left Arm (Applies the 2.6mm offset)
# test_calibration_path(robotleft, needle_bed, is_left_arm=True)

# Pass all three arms to the stitch function
#target_needle.simple_stitch(robotleft, robotright, robotyarn)