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

# --- NEW YARN DISTRIBUTOR SWING FUNCTIONS ---
def close_yarn_swing(arm):
    print("Yarn swing closing (Holding yarn)...")
    arm.SetAO(0, 0.0) 
    time.sleep(0.5)

def open_yarn_swing(arm):
    print("Yarn swing opening (Releasing yarn)...")
    arm.SetAO(0, 15.0) 
    time.sleep(0.5)


# --- Calibration Databases ---
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

def get_yarn_physical_location(grid_x, grid_y):
    """
    Independent mapping for the Yarn Distributor (3rd Arm).
    Currently isolated to perfect the 1,1 stitch location.
    """
    yarn_map = {
        (1, 1): (12.6, 19.9)
    }
    # Fallback to standard mapping if not defined so the script doesn't crash on full-bed loops
    return yarn_map.get((grid_x, grid_y), get_physical_location(grid_x, grid_y))


# --- Needle Object ---
class Needle:
    def __init__(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        
        # 1. Base Physical Coordinates (For Left/Right Grippers)
        physical_coords = get_physical_location(self.grid_x, self.grid_y)
        if physical_coords is None:
            raise ValueError(f"Needle ({self.grid_x}, {self.grid_y}) is out of bounds.")
        self.physical_x, self.physical_y = physical_coords
        
        # 2. Yarn Physical Coordinates (For Distributor)
        yarn_coords = get_yarn_physical_location(self.grid_x, self.grid_y)
        self.yarn_physical_x, self.yarn_physical_y = yarn_coords
        
        # Arm Offsets
        self.left_x_offset = 2.6          
        self.base_x_L = self.physical_x - self.left_x_offset
        
        # --- YARN DISTRIBUTOR DIRECTIONAL OFFSET (NORTH/SOUTH) ---
        # 1 = South to North | -1 = North to South
        self.yarn_direction = 1 
        
        # The physical distance to shift the tool along the Y-axis so the gap frames the needle
        self.yarn_gap_offset_y = 30.0 
        
        # Calculates the base coordinates for the yarn arm
        self.base_x_Y = self.yarn_physical_x 
        self.base_y_Y = self.yarn_physical_y + (self.yarn_gap_offset_y * self.yarn_direction)
        # ---------------------------------------------------------
        
        # --- COLLISION AVOIDANCE HOVER OFFSETS ---
        self.clearance_x = 150.0     
        self.yarn_y_hover_offset = 150.0 
        
        # Z-heights for the stages of a stitch
        self.z_hover = 100.0         
        self.z_above = 40.0   
        self.z_push = 26.0      
        
        # Independent diagonal retraction amounts (Y set to 0)
        self.diag_retract_x = 1.5
        self.diag_retract_y = 0.0
        
        # Ensures rotation is all 0s for the yarn arm at 1,1
        self.rot_left = [0.0, 0.0, 0.0] 
        self.rot_right = [0.0, 0.0, 0.0] 
        self.rot_yarn = [0.0, 0.0, 0.0]
        
        self.offset_dist = 1.6
        self.velocity = 15

    def simple_stitch(self, leftarm, rightarm, yarnarm):
        # Local variables for concise waypoint lookup table
        bx, by = self.physical_x, self.physical_y
        bx_L = self.base_x_L
        bx_Y, by_Y = self.base_x_Y, self.base_y_Y
        yyh = self.yarn_y_hover_offset
        od = self.offset_dist
        cx = self.clearance_x
        zh, za, zp = self.z_hover, self.z_above, self.z_push
        dx, dy = self.diag_retract_x, self.diag_retract_y
        rl, rr, ry = self.rot_left, self.rot_right, self.rot_yarn

        # Pre-calculated physical waypoints for all three arms
        waypoints = {
            # Yarn Distributor Waypoints 
            "hover_yarn":  [bx_Y, by_Y + yyh, zh] + ry,
            "above_yarn":  [bx_Y, by_Y, za] + ry,
            "push_yarn":   [bx_Y, by_Y, zp] + ry,
            "adjust_yarn": [bx_Y + 15.0, by_Y, zp] + ry, # Pulls tension along X-axis
            
            # Left Arm Waypoints 
            "hover_west_L": [bx_L - od - cx, by, zh] + rl,
            "above_west_L": [bx_L - od, by, za] + rl,
            "push_west_L":  [bx_L - od, by, zp] + rl,
            "diagonal_retract_west_L": [bx_L - od - dx, by + dy, za] + rl,
            "above_far_west_L": [bx_L - (od * 8), by, za] + rl,
            "hover_east_L": [bx_L + od - cx, by, zh] + rl,
            "above_east_L": [bx_L + od, by, za] + rl,
            "push_east_L":  [bx_L + od, by, zp] + rl,
            "diagonal_retract_east_L": [bx_L + od - dx, by + dy, za] + rl,
            
            # Right Arm Waypoints 
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

        # --- YARN DISTRIBUTOR SEQUENCE (MOVE IN & HOLD) ---
        print(">> Yarn Arm: Moving in to position...")
        yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        yarnarm.MoveL(waypoints["push_yarn"], tool=1, user=2, vel=self.velocity)
        
        open_yarn_swing(yarnarm)
        close_yarn_swing(yarnarm)
        
        print(">> Yarn Arm: Adjusting length and holding...")
        yarnarm.MoveL(waypoints["adjust_yarn"], tool=1, user=2, vel=self.velocity)
        # Note: The yarn distributor now WAITS here while grippers work
        # -------------------------------------------------

        
        # --- GRIPPER STITCHING SEQUENCE ---
        # Step 1: Right arm works while Left is safely parked
        print(">> Right Arm: Initiating Step 1...")
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
        open_gripper(rightarm)
        rightarm.MoveL(waypoints["diagonal_retract_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)

        # Step 2: Left arm works while Right is safely parked
        print(">> Left Arm: Initiating Step 2...")
        leftarm.MoveL(waypoints["hover_east_L"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        open_gripper(leftarm)
        leftarm.MoveL(waypoints["push_east_L"], tool=1, user=2, vel=self.velocity)
        close_gripper(leftarm)
        
        leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["above_far_west_L"], tool=1, user=2, vel=self.velocity)
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
        rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)
        # -------------------------------------------------

        # --- YARN DISTRIBUTOR SEQUENCE (RELEASE & RETRACT) ---
        print(">> Yarn Arm: Stitch complete. Releasing and returning to hover...")
        open_yarn_swing(yarnarm)
        yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)


# --- Execution ---
needle_bed = {}

# Initialize the 6x6 needle grid
for x in range(6):
    for y in range(6):
        needle_bed[(x, y)] = Needle(grid_x=x, grid_y=y)

print("\n====================================")
print("--- Initiating Single Stitch at Needle (1, 1) ---")
print("====================================")

# Execute only the single stitch at (1, 1)
target_needle = needle_bed[(1, 1)]
target_needle.simple_stitch(robotleft, robotright, robotyarn)