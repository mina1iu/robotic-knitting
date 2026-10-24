import time

# --- 2. Calibration Database ---
def generate_calibration_map():
    safe_map = {}
    
    # Exact physical coordinates measured with the Right Arm
    measured_x = [-3, 16.246, 31, 46.3, 60.7, 76.1]
    measured_y = [3.8, 18.7, 34, 49, 63.5, 79]
    
    for x in range(6):
        for y in range(6):
            safe_map[(x, y)] = (measured_x[x], measured_y[y])
            
    return safe_map

PHYSICAL_NEEDLE_MAP = generate_calibration_map()

def get_physical_location(grid_x, grid_y):
    return PHYSICAL_NEEDLE_MAP.get((grid_x, grid_y), None)

# --- 3. Stripped-Down Needle Object ---
class Needle:
    def __init__(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        
        physical_coords = get_physical_location(self.grid_x, self.grid_y)
        if physical_coords is None:
            raise ValueError(f"Needle ({self.grid_x}, {self.grid_y}) is out of bounds.")
            
        self.physical_x, self.physical_y = physical_coords
        
        # Left Arm Offset (so the Left Arm hits the exact same target point)
        self.left_x_offset = 2.6          
        self.base_x_L = self.physical_x - self.left_x_offset

# --- 4. Initialization ---
needle_bed = {}

# Build the 6x6 needle grid
for x in range(6):
    for y in range(6):
        needle_bed[(x, y)] = Needle(grid_x=x, grid_y=y)


# --- 5. Calibration Test Function ---
def test_calibration_path(arm, needle_bed, is_left_arm=False, velocity=15):
    """
    Traces the entire 6x6 needle bed to visually verify physical calibration.
    Moves row by row (Y), gliding across columns (X).
    Applies the pre-calculated left-arm offset if is_left_arm=True.
    """
    z_push = 36.0  
    z_hop = z_push + 30.0  
    rot = [0.0, 0.0, 0.0]
    
    arm_name = "Left Arm" if is_left_arm else "Right Arm"
    print(f"\n>> Starting calibration test path for {arm_name}...")
    
    def get_target_x(needle_obj):
        return needle_obj.base_x_L if is_left_arm else needle_obj.physical_x

    def move_to(pose):
        result = arm.MoveL(pose, tool=1, user=2, vel=velocity, blendR=-1.0)
        if result != 0:
            raise RuntimeError(f"{arm_name} MoveL failed at {pose}: {result}")

    print(">> Moving to home position...")
    safe_hover_coord = [0, 0, 75, 0, 0, 0]
    move_to(safe_hover_coord)
    
    # 2. Traverse the Grid
    for y in range(6):
        start_needle = needle_bed[(0, y)]
        target_x = get_target_x(start_needle)
        
        print(f">> Row {y}: (0, {y}) -> (5, {y})")
        # Travel to X=0 at clearance height, then lower to the first needle.
        move_to([target_x, start_needle.physical_y, z_hop] + rot)
        move_to([target_x, start_needle.physical_y, z_push] + rot)
        time.sleep(0.3)
        
        # Glide across X
        for x in range(1, 6):
            needle = needle_bed[(x, y)]
            target_x = get_target_x(needle)
            move_to([target_x, needle.physical_y, z_push] + rot)
            time.sleep(0.3)  
            
        # Hop up at end of row
        end_needle = needle_bed[(5, y)]
        target_x = get_target_x(end_needle)
        move_to([target_x, end_needle.physical_y, z_hop] + rot)

    print(f">> Test path complete for {arm_name}. Moving to safe park position.")
    # Return home using MoveL, after lifting above the last needle.
    move_to(safe_hover_coord)


# ==========================================
# --- EXECUTION ---
# ==========================================

if __name__ == "__main__":
    from fairino import Robot

    # Connect only to the arm being tested. Importing this file does not move it.
    robotright = Robot.RPC('192.168.0.52')
    test_calibration_path(robotright, needle_bed, is_left_arm=False)

    # To test the left arm instead, replace the two lines above with:
    # robotleft = Robot.RPC('192.168.0.51')
    # test_calibration_path(robotleft, needle_bed, is_left_arm=True)
