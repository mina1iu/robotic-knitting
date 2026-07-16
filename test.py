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
    measured_x = [1.81, 11.38, 22.15, 31.40, 41.61, 51.08]
    measured_y = [0.5, 10.3, 20.3, 30.3, 40.1, 50.2]
    
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
        
        # Third Arm (Yarn Distributor) Offset - Increased in X
        self.yarn_x_offset = 30.0
        self.base_x_Y = self.physical_x + self.yarn_x_offset
        
        # Z-heights for the stages of a stitch
        self.z_hover = 100.0         
        self.z_above = 40.0   
        self.z_push = 26.0      
        
        # Safe travel clearances
        self.clearance_x = 50.0     
        
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
        od = self.offset_dist
        cx = self.clearance_x
        zh, za, zp = self.z_hover, self.z_above, self.z_push
        dx, dy = self.diag_retract_x, self.diag_retract_y
        rl, rr, ry = self.rot_left, self.rot_right, self.rot_yarn

        # Pre-calculated physical waypoints for all three arms
        waypoints = {
            # Yarn Distributor Waypoints
            "hover_yarn":  [bx_Y, by, zh] + ry,
            "above_yarn":  [bx_Y, by, za] + ry,
            "push_yarn":   [bx_Y, by, zp] + ry,
            "adjust_yarn": [bx_Y + 15.0, by, zp] + ry, # Pulls further X to adjust length
            
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

        # 0. Initialize all to safe hover positions (Collision Avoidance)
        yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

        # --- YARN DISTRIBUTOR SEQUENCE ---
        # The 3rd arm takes over the manual feeding step
        yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        yarnarm.MoveL(waypoints["push_yarn"], tool=1, user=2, vel=self.velocity)
        
        # [IMAGINARY STEP] Open pincher, lay yarn, close pincher
        # open_gripper(yarnarm)
        # close_gripper(yarnarm)
        # time.sleep(1)
        
        # Adjust the yarn length
        yarnarm.MoveL(waypoints["adjust_yarn"], tool=1, user=2, vel=self.velocity)
        
        # [IMAGINARY STEP] Release yarn to the needle
        # open_gripper(yarnarm)
        
        # Retract yarn arm safely out of the way before the grippers move in
        yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
        # ---------------------------------

        
        # Step 1: Right arm moves West loop to East needle (or acts on the prepped yarn)
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
        open_gripper(rightarm)
        rightarm.MoveL(waypoints["diagonal_retract_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)

        # Step 2: Left arm grabs East loop and pulls it West
        leftarm.MoveL(waypoints["hover_east_L"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        open_gripper(leftarm)
        leftarm.MoveL(waypoints["push_east_L"], tool=1, user=2, vel=self.velocity)
        close_gripper(leftarm)
        
        leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        leftarm.MoveL(waypoints["above_far_west_L"], tool=1, user=2, vel=self.velocity)

        # Step 3: Right arm moves West loop to East needle
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
        close_gripper(rightarm)
        
        rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["above_east_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["push_east_R"], tool=1, user=2, vel=self.velocity)
        open_gripper(rightarm)
        
        rightarm.MoveL(waypoints["diagonal_retract_east_R"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

        open_gripper(leftarm)
        leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)


# --- Execution ---
needle_bed = {}

# Initialize the 6x6 needle grid
for x in range(6):
    for y in range(6):
        needle_bed[(x, y)] = Needle(grid_x=x, grid_y=y)

target_needle = needle_bed[(0, 0)]

# Pass all three arms to the stitch function
target_needle.simple_stitch(robotleft, robotright, robotyarn)

