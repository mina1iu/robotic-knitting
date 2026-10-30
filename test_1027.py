from fairino import Robot
import time

# A connection is established with the robot controllers.
robotyarn  = Robot.RPC('192.168.0.50')  # Third arm: Yarn Distributor
robotleft  = Robot.RPC('192.168.0.51')
robotright = Robot.RPC('192.168.0.52')

def close_gripper(arm):
    print("Gripper closing...")
    result = arm.SetAO(0, 0.0)
    if result != 0:
        raise RuntimeError(f"Gripper close failed: {result}")
    time.sleep(0.5)

def open_gripper(arm):
    print("Gripper opening...")
    result = arm.SetAO(0, 13.0)
    if result != 0:
        raise RuntimeError(f"Gripper open failed: {result}")
    time.sleep(0.5)

# --- YARN DISTRIBUTOR SWING FUNCTIONS ---
MG90S_ID = 1
DC_MOTOR_ID = 2
SPEED = 50
FORCE = 0
MAX_TIME_MS = 10000
DC_FEED_SECONDS = 2.5  # Timed cycle; confirm against current ESP32 firmware.


def close_yarn_swing(arm):
    print("Yarn swing -> 100...")
    result = arm.MoveGripper(MG90S_ID, 100, SPEED, FORCE, MAX_TIME_MS, 0, 0, 0, 0, 0)
    if result != 0:
        raise RuntimeError(f"MG90S 100 failed: {result}")
    time.sleep(0.5)


def open_yarn_swing(arm):
    print("Yarn swing -> 0...")
    result = arm.MoveGripper(MG90S_ID, 0, SPEED, FORCE, MAX_TIME_MS, 0, 0, 0, 0, 0)
    if result != 0:
        raise RuntimeError(f"MG90S 0 failed: {result}")
    time.sleep(0.5)


def feed_yarn(arm):
    """One forward command, timed wait, then STOP; no measured rotation feedback."""
    started = time.monotonic()
    try:
        result = arm.MoveGripper(DC_MOTOR_ID, 1, SPEED, FORCE, MAX_TIME_MS, 0, 0, 0, 0, 0)
        if result != 0:
            raise RuntimeError(f"DC START failed: {result}")
        time.sleep(max(0.0, DC_FEED_SECONDS - (time.monotonic() - started)))
    finally:
        result = arm.MoveGripper(DC_MOTOR_ID, 0, SPEED, FORCE, MAX_TIME_MS, 0, 0, 0, 0, 0)
        if result != 0:
            raise RuntimeError(f"DC STOP failed: {result}")


# --- Calibration Databases ---
def generate_calibration_map():
    safe_map = {}
    
    # # Exact physical coordinates measured with the Right Arm
    # measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
    # measured_y = [-0.4, 14.6, 29.7, 44.3, 60, 74.8]
    measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
    measured_y = [4.6, 18.8, 33.8, 48.4, 63.2, 78.4]
    
    for x in range(6):
        for y in range(6):
            safe_map[(x, y)] = (measured_x[x], measured_y[y])
            
    # Latest calibrated right-arm pickup for the single tested stitch.
    safe_map[(1, 1)] = (13.3, 18.3)
    return safe_map

PHYSICAL_NEEDLE_MAP = generate_calibration_map()

def get_physical_location(grid_x, grid_y):
    return PHYSICAL_NEEDLE_MAP.get((grid_x, grid_y), None)

def get_yarn_physical_location(grid_x, grid_y):
    """
    Independent mapping for the Yarn Distributor (3rd Arm).
    Currently isolated to perfect the 1,1 stitch location.
    """

    # hard-coded mapping for the yarn distributor at (1, 1), into west needle position
    yarn_map = {
        (1, 1): (10.95, 23.42)
    }
    # Fallback to standard mapping if not defined
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
        
        # --- Calibration and fixed distances ---
        # Latest explicit positions supersede the older 3.65 Y offset.
        self.left_x_offset = -0.03  # right X 13.30 -> left X 13.33
        self.left_y_offset = 2.93   # right Y 18.30 -> left pickup Y 15.37
        self.left_entry_y_offset = 0.0  # left entry/parking Y 14.37
        self.base_x_L = round(self.physical_x - self.left_x_offset, 6)
        self.base_y_L = round(self.physical_y - self.left_y_offset, 6)
        self.base_x_Y = self.yarn_physical_x
        self.base_y_Y = self.yarn_physical_y

        # Parking X retained from the previously recalibrated program.
        self.left_parking_x = -64.824
        self.right_parking_x = 92.546

        self.z_push = 28.0             # left low Z
        self.z_push_R = 27.0           # right low Z
        self.lift_dist = 10.0          # fixed vertical travel for both arms
        self.z_above = self.z_push + self.lift_dist
        self.z_above_R = self.z_push_R + self.lift_dist
        self.z_yarn = 30             # .50 fixed working height
        self.offset_dist = 3.18        # FULL spacing between the two right-arm pins
        self.left_retract_dist = 13.99 # left 13.33 -> -0.66
        self.rot_left = [0.0, 0.0, 0.0]
        self.rot_right = [0.0, 0.0, 0.0]
        self.rot_yarn = [0.0, 0.0, 0.0]
        self.velocity = 5

    def simple_stitch(self, leftarm, rightarm, yarnarm):
        # Only (1,1) has been recalibrated for this fixed-layer sequence.
        if (self.grid_x, self.grid_y) != (1, 1):
            raise ValueError("Only needle (1, 1) is calibrated for this sequence.")
        bx, by = self.physical_x, self.physical_y
        bx_L, by_L = self.base_x_L, self.base_y_L
        bx_Y, by_Y = self.base_x_Y, self.base_y_Y
        by_entry_L = round(by_L + self.left_entry_y_offset, 6)
        od = self.offset_dist
        za, zp = self.z_above, self.z_push
        za_R, zp_R = self.z_above_R, self.z_push_R
        rl, rr, ry = self.rot_left, self.rot_right, self.rot_yarn

        waypoints = {
            "above_yarn": [bx_Y, by_Y, self.z_yarn] + ry,
            "hover_west_L": [self.left_parking_x, by_entry_L, za] + rl,
            "above_east_L": [bx_L, by_entry_L, za] + rl,
            "push_east_L": [bx_L, by_L, zp] + rl,
            "lift_east_L": [bx_L, by_L, za] + rl,
            "hold_close_west_L": [round(bx_L - self.left_retract_dist, 6), by_L, za] + rl,
            "hover_east_R": [self.right_parking_x, by, za_R] + rr,
            "above_west_R": [bx, by, za_R] + rr,
            "push_west_R": [bx, by, zp_R] + rr,
            "above_east_R": [round(bx + od, 6), by, za_R] + rr,
            "push_east_R": [round(bx + od, 6), by, zp_R] + rr,
        }

        # 0. Initialize all to safe parking corners
        print(">> Parking all arms in safe hovers...")
        #yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
        move_result = leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"leftarm MoveL failed: {move_result}")
        move_result = rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")

        # --- YARN DISTRIBUTOR SEQUENCE (MOVE IN & HOLD) ---
        print(">> Yarn Arm: Moving in to position...")
        move_result = yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"Yarn arm failed to reach needle position: {move_result}")

        # feed_yarn(yarnarm)
        close_yarn_swing(yarnarm)

        print(">> Yarn Arm: Holding position...")
        
        # --- GRIPPER STITCHING SEQUENCE ---
        
        # Step 1: Left arm works while Right is safely parked
        print(">> Left Arm: Initiating Step 1 (Pulling old loop West & Holding Close)...")
        move_result = leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"leftarm MoveL failed: {move_result}")
        open_gripper(leftarm)
        move_result = leftarm.MoveL(waypoints["push_east_L"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"leftarm MoveL failed: {move_result}")
        close_gripper(leftarm)
        
        # Left arm lifts 10 mm, then pulls back 13.99 mm while closed
        move_result = leftarm.MoveL(waypoints["lift_east_L"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"leftarm MoveL failed: {move_result}")
        move_result = leftarm.MoveL(waypoints["hold_close_west_L"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"leftarm MoveL failed: {move_result}")

        # Step 2: Right arm works while Left holds the yarn
        print(">> Right Arm: Initiating Step 2 (Moving yarn to East needle)...")
        open_gripper(rightarm)
        move_result = rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")
        move_result = rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")
        close_gripper(rightarm)
        
        # Move yarn from West to East
        move_result = rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")
        move_result = rightarm.MoveL(waypoints["above_east_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")
        move_result = rightarm.MoveL(waypoints["push_east_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")
        
        # Release and retract
        open_gripper(rightarm)
        move_result = rightarm.MoveL(waypoints["above_east_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")
        move_result = rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"rightarm MoveL failed: {move_result}")

        # Left arm can now release and return to deep hover
        # open_gripper(leftarm)
        print("Left gripper final release -> 30%")
        result = leftarm.SetAO(0, 30.0)
        if result != 0:
            raise RuntimeError(f"Left gripper final release failed: {result}")
        time.sleep(0.5)
        move_result = leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
        if move_result != 0:
            raise RuntimeError(f"leftarm MoveL failed: {move_result}")
        # -------------------------------------------------

        # --- YARN DISTRIBUTOR SEQUENCE (RELEASE & STOP) ---
        print(">> Yarn Arm: Stitch complete. Releasing yarn and stopping in place...")
        open_yarn_swing(yarnarm)
        # (Retraction moves completely removed here)


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