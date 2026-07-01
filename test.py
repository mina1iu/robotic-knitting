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


def close_gripper(arm):
    print("Gripper closing...")
    arm.SetAO(0, 0.0) 
    time.sleep(0.5)

def open_gripper(arm):
    print("Gripper opening...")
    arm.SetAO(0, 20.0) 
    time.sleep(0.5)

# open_gripper(robotleft)
# open_gripper(robotright)
# close_gripper(robotleft)
# close_gripper(robotright)

# --- Calibration Database ---
def generate_calibration_map():
    safe_map = {}
    
    # Exact physical coordinates measured with the Right Arm
    measured_x = [1.81, 11.38, 22.15, 31.40, 41.61, 51.08]
    measured_y = [0.5, 10.3, 20.3, 30.3, 40.1, 50.2]
    
    for x in range(6):
        for y in range(6):
            # Maps grid (x,y) directly to your exact measurements
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
        
        # Verify physical location exists in calibration map
        physical_coords = get_physical_location(self.grid_x, self.grid_y)
        if physical_coords is None:
            raise ValueError(f"Needle ({self.grid_x}, {self.grid_y}) is out of bounds.")
            
        self.physical_x, self.physical_y = physical_coords
        
        # Arm & Stitch Parameters
        self.left_x_offset = 2.6          
        self.base_x_L = self.physical_x - self.left_x_offset
        
        # Z-heights for the three stages of a stitch
        self.z_hover = 100.0         
        self.z_above = 40.0   
        self.z_push = 25.0      
        
        # Safe travel clearances
        self.clearance_x = 100.0     
        self.clearance_y = -25.0     
        
        self.rot_left = [0.0, 0.0, 0.0] 
        self.rot_right = [0.0, 0.0, 0.0] 
        
        self.offset_dist = 1.6
        self.diagonal_factor = 0.04
        self.velocity = 15

    def simple_stitch(self, leftarm, rightarm):
        # Local variables for concise waypoint lookup table
        bx, by = self.physical_x, self.physical_y
        bx_L = self.base_x_L
        od = self.offset_dist
        cx, cy = self.clearance_x, self.clearance_y
        zh, za, zp = self.z_hover, self.z_above, self.z_push
        df = self.diagonal_factor
        rl, rr = self.rot_left, self.rot_right

        # Pre-calculated physical waypoints for both arms
        waypoints = {
            "hover_west_L": [bx_L - od - cx, by + cy, zh] + rl,
            "above_west_L": [bx_L - od, by, za] + rl,
            "push_west_L":  [bx_L - od, by, zp] + rl,
            "diagonal_retract_west_L": [bx_L - od - (cx * df), by + (cy * df), za] + rl,
            "above_far_west_L": [bx_L - (od * 8), by, za] + rl,
            "hover_east_L": [bx_L + od - cx, by + cy, zh] + rl,
            "above_east_L": [bx_L + od, by, za] + rl,
            "push_east_L":  [bx_L + od, by, zp] + rl,
            "diagonal_retract_east_L": [bx_L + od - (cx * df), by + (cy * df), za] + rl,
            
            "hover_west_R": [bx - od + cx, by + cy, zh] + rr,
            "above_west_R": [bx - od, by, za] + rr,
            "push_west_R":  [bx - od, by, zp] + rr,
            "diagonal_retract_west_R": [bx - od + (cx * df), by + (cy * df), za] + rr,
            "hover_east_R": [bx + od + cx, by + cy, zh] + rr,
            "above_east_R": [bx + od, by, za] + rr,
            "push_east_R":  [bx + od, by, zp] + rr,
            "diagonal_retract_east_R": [bx + od + (cx * df), by + (cy * df), za] + rr
        }

        # Initialize to safe hover positions
        leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
        rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
        
        # Step 1: Right arm places new loop on West needle
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
        open_gripper(leftarm)
        leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)

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
    Parks safely out of the workspace when finished.
    """
    z_push = 35.0
    z_hop = z_push + 30.0  # 55.0 mm to clear the sticking out needles
    rot = [0.0, 0.0, 0.0]
    
    arm_name = "Left Arm" if is_left_arm else "Right Arm"
    print(f">> Starting calibration test path for {arm_name}...")
    
    # Helper to quickly grab the correct X-coordinate based on the arm
    def get_target_x(needle_obj):
        return needle_obj.base_x_L if is_left_arm else needle_obj.physical_x

    # Start at a safe hover above (0,0) before beginning the sequence
    first_needle = needle_bed[(0, 0)]
    start_x = get_target_x(first_needle)
    arm.MoveL([start_x, first_needle.physical_y, 100.0] + rot, tool=1, user=2, vel=velocity)
    
    for y in range(6):
        # 1. Move to the start of the row (x=0) at the safe hop height
        start_needle = needle_bed[(0, y)]
        target_x = get_target_x(start_needle)
        arm.MoveL([target_x, start_needle.physical_y, z_hop] + rot, tool=1, user=2, vel=velocity)
        
        # 2. Move down 30mm to the glide/push height
        arm.MoveL([target_x, start_needle.physical_y, z_push] + rot, tool=1, user=2, vel=velocity)
        
        # 3. Glide through all X values in the current row
        for x in range(6):
            needle = needle_bed[(x, y)]
            target_x = get_target_x(needle)
            arm.MoveL([target_x, needle.physical_y, z_push] + rot, tool=1, user=2, vel=velocity)
            
            # Brief pause at each needle so you can visually verify alignment
            time.sleep(0.5)  
            
        # 4. End of the row (x=5), move straight up 30mm to clear the needles
        end_needle = needle_bed[(5, y)]
        target_x = get_target_x(end_needle)
        arm.MoveL([target_x, end_needle.physical_y, z_hop] + rot, tool=1, user=2, vel=velocity)

    print(f">> Test path complete for {arm_name}. Moving to safe park position.")
    
    # NEW: Move out of the way to avoid dual-arm collisions
    park_x = -100.0 if is_left_arm else 150.0
    arm.MoveL([park_x, first_needle.physical_y, 100.0] + rot, tool=1, user=2, vel=velocity)


# ==========================================
# --- EXECUTION ---
# ==========================================

# Test Right Arm (Default)
test_calibration_path(robotright, needle_bed, is_left_arm=False)

# Test Left Arm (Applies the 2.6mm offset)
test_calibration_path(robotleft, needle_bed, is_left_arm=True)
