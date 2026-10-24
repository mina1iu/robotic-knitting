# # """Single stitch: .50 RS-485 MG90S; .51/.52 control-box AO.
# # Assumes MG90S ID1 replaces the legacy yarn swing.
# # Set the two YARN_SWING_*_POS constants before running.
# # DC ID2 helpers are provided but no DC actions are inserted.
# # Motion coordinates and stitch order are preserved from the supplied source.
# # """
# # from fairino import Robot
# # import time

# # # .51 / .52 retain their original control-box AO commands.
# # def close_gripper(arm):
# #     print("Gripper closing...")
# #     arm.SetAO(0, 0.0)
# #     time.sleep(0.5)


# # def open_gripper(arm):
# #     print("Gripper opening...")
# #     arm.SetAO(0, 13.0)
# #     time.sleep(0.5)


# # # .50 RS-485 motors; argument format matches the supplied working API test.
# # MG90S_ID = 1
# # DC_MOTOR_ID = 2
# # SPEED = 50
# # FORCE = 0
# # MAX_TIME_MS = 10000

# # # REQUIRED: replace None with experimentally verified integer positions (0-100).
# # # AO values 85 and 100 are NOT automatically equivalent to these positions.
# # YARN_SWING_OPEN_POS = 0 # MG90S position that releases yarn
# # YARN_SWING_CLOSE_POS = 100 # MG90S position that holds yarn

# # robotyarn = None
# # robotleft = None
# # robotright = None


# # def validate_yarn_swing_positions():
# #     for name, position in (
# #         ("YARN_SWING_OPEN_POS", YARN_SWING_OPEN_POS),
# #         ("YARN_SWING_CLOSE_POS", YARN_SWING_CLOSE_POS),
# #     ):
# #         if type(position) is not int or not 0 <= position <= 100:
# #             raise ValueError(
# #                 f"Set {name} to a verified integer position (0-100) before running."
# #             )


# # def yarn_motor_command(arm, motor_id, value):
# #     if arm is None or arm is not robotyarn:
# #         raise ValueError("Yarn motor commands must use robotyarn (.50).")
# #     if motor_id == MG90S_ID:
# #         if type(value) is not int or not 0 <= value <= 100:
# #             raise ValueError("MG90S position must be an integer from 0 to 100.")
# #     elif motor_id == DC_MOTOR_ID:
# #         if type(value) is not int or value not in (0, 1, 2):
# #             raise ValueError("DC command must be 0=STOP, 1=START, or 2=REVERSE.")
# #     else:
# #         raise ValueError("Unsupported yarn motor ID.")
# #     result = arm.MoveGripper(
# #         motor_id, value, SPEED, FORCE, MAX_TIME_MS, 0, 0, 0, 0, 0
# #     )
# #     if result != 0:
# #         raise RuntimeError(
# #             f".50 MoveGripper failed: ID={motor_id}, value={value}, return={result}"
# #         )
# #     return result


# # def close_yarn_swing(arm):
# #     validate_yarn_swing_positions()
# #     print("Yarn swing closing (Holding yarn)...")
# #     yarn_motor_command(arm, MG90S_ID, YARN_SWING_CLOSE_POS)
# #     time.sleep(0.5)


# # def open_yarn_swing(arm):
# #     validate_yarn_swing_positions()
# #     print("Yarn swing opening (Releasing yarn)...")
# #     yarn_motor_command(arm, MG90S_ID, YARN_SWING_OPEN_POS)
# #     time.sleep(0.5)


# # # Available for later integration. NOT called by the original stitch sequence.
# # # No DC run time, rotation count, or automatic stop is inferred here.
# # def start_yarn_dc(arm):
# #     return yarn_motor_command(arm, DC_MOTOR_ID, 1)


# # def reverse_yarn_dc(arm):
# #     return yarn_motor_command(arm, DC_MOTOR_ID, 2)


# # def stop_yarn_dc(arm):
# #     return yarn_motor_command(arm, DC_MOTOR_ID, 0)


# # # --- Calibration Databases ---
# # def generate_calibration_map():
# #     safe_map = {}
    
# #     # # Exact physical coordinates measured with the Right Arm
# #     # measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
# #     # measured_y = [-0.4, 14.6, 29.7, 44.3, 60, 74.8]
# #     # New 1021
# #     measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
# #     measured_y = [4.6, 18.8, 33.8, 48.4, 63.2, 78.4]
    
# #     for x in range(6):
# #         for y in range(6):
# #             safe_map[(x, y)] = (measured_x[x], measured_y[y])
            
# #     return safe_map

# # PHYSICAL_NEEDLE_MAP = generate_calibration_map()

# # def get_physical_location(grid_x, grid_y):
# #     return PHYSICAL_NEEDLE_MAP.get((grid_x, grid_y), None)

# # def get_yarn_physical_location(grid_x, grid_y):
# #     """
# #     Independent mapping for the Yarn Distributor (3rd Arm).
# #     Currently isolated to perfect the 1,1 stitch location.
# #     """

# #     # hard-coded mapping for the yarn distributor at (1, 1), into west needle position
# #     yarn_map = {
# #         (1, 1): (11.9, 21.95)
# #     }
# #     # Fallback to standard mapping if not defined
# #     return yarn_map.get((grid_x, grid_y), get_physical_location(grid_x, grid_y))


# # # --- Needle Object ---
# # class Needle:
# #     def __init__(self, grid_x, grid_y):
# #         self.grid_x = grid_x
# #         self.grid_y = grid_y
        
# #         # 1. Base Physical Coordinates (For Left/Right Grippers)
# #         physical_coords = get_physical_location(self.grid_x, self.grid_y)
# #         if physical_coords is None:
# #             raise ValueError(f"Needle ({self.grid_x}, {self.grid_y}) is out of bounds.")
# #         self.physical_x, self.physical_y = physical_coords
        
# #         # 2. Yarn Physical Coordinates (For Distributor)
# #         yarn_coords = get_yarn_physical_location(self.grid_x, self.grid_y)
# #         self.yarn_physical_x, self.yarn_physical_y = yarn_coords
        
# #         # Arm Offsets
# #         self.left_x_offset = 4.77          
# #         self.base_x_L = self.physical_x - self.left_x_offset
# #         self.left_y_offset = 3.65
# #         self.base_y_L = self.physical_y - self.left_y_offset
        
# #         # --- YARN DISTRIBUTOR DIRECTIONAL OFFSET (NORTH/SOUTH) ---
# #         # 1 = South to North | -1 = North to South
# #         self.yarn_direction = 1 
        
# #         # The physical distance to shift the tool along the Y-axis so the gap frames the needle
# #         self.yarn_gap_offset_y = 0 
        
# #         # Calculates the base coordinates for the yarn arm
# #         self.base_x_Y = self.yarn_physical_x 
# #         self.base_y_Y = self.yarn_physical_y + (self.yarn_gap_offset_y * self.yarn_direction)
        
# #         # --- COLLISION AVOIDANCE HOVER OFFSETS ---
# #         self.clearance_x = 75.0      # Lowered to keep Left arm in reachable workspace
# #         self.yarn_y_hover_offset = 50.0 
        
# #         # Z-heights for the stages of a stitch
# #         self.z_hover = 70.0         
# #         self.z_above = 41.0   
# #         self.z_push = 26.0 
        
# #         # Independent diagonal retraction amounts (Y set to 0)
# #         self.diag_retract_x = 1.5
# #         self.diag_retract_y = 0.0
        
# #         self.rot_left = [0.0, 0.0, 0.0] 
# #         self.rot_right = [0.0, 0.0, 0.0] 
# #         self.rot_yarn = [0.0, 0.0, 0.0]
        
# #         self.offset_dist = 1.3
# #         self.velocity = 5
        

# #     def simple_stitch(self, leftarm, rightarm, yarnarm):
# #         bx, by = self.physical_x, self.physical_y
# #         bx_L = self.base_x_L
# #         by_L = self.base_y_L
# #         bx_Y, by_Y = self.base_x_Y, self.base_y_Y
# #         yyh = self.yarn_y_hover_offset
# #         od = self.offset_dist
# #         cx = self.clearance_x
# #         zh, za, zp = self.z_hover, self.z_above, self.z_push
# #         dx, dy = self.diag_retract_x, self.diag_retract_y
# #         rl, rr, ry = self.rot_left, self.rot_right, self.rot_yarn

# #         # Pre-calculated physical waypoints for all three arms
# #         waypoints = {
# #             # Yarn Distributor Waypoints 
# #             "hover_yarn":  [bx_Y, by_Y + yyh, zh] + ry,
# #             "above_yarn":  [bx_Y, by_Y, za] + ry,
# #             "push_yarn":   [bx_Y, by_Y, zp + 5] + ry,
            
# #             # Left Arm Waypoints 
# #             "hover_west_L": [bx_L - od - cx, by_L, zh] + rl,
# #             "above_west_L": [bx_L - od, by_L, za] + rl,
# #             "push_west_L":  [bx_L - od, by_L, zp] + rl,
# #             "diagonal_retract_west_L": [bx_L - od - dx, by_L + dy, za] + rl,
# #             "hold_close_west_L": [bx_L - (od*8.5), by_L, za] + rl,  # <--- New close hold position
# #             "hover_east_L": [bx_L + od - cx, by_L, zh] + rl,
# #             "above_east_L": [bx_L + od, by_L, za] + rl,
# #             "push_east_L":  [bx_L + od, by_L, zp] + rl,
# #             "diagonal_retract_east_L": [bx_L + od - dx, by_L + dy, za] + rl,
            
# #             # Right Arm Waypoints 
# #             "hover_west_R": [bx - od + cx, by, zh] + rr,
# #             "above_west_R": [bx - od, by, za] + rr,
# #             "push_west_R":  [bx - od, by, zp] + rr,
# #             "diagonal_retract_west_R": [bx - od + dx, by + dy, za] + rr,
# #             "hover_east_R": [bx + od + cx, by, zh] + rr,
# #             "above_east_R": [bx + od, by, za] + rr,
# #             "push_east_R":  [bx + od, by, zp] + rr,
# #             "diagonal_retract_east_R": [bx + od + dx, by + dy, za] + rr
# #         }

# #         # 0. Initialize all to safe parking corners
# #         print(">> Parking all arms in safe hovers...")
# #         #yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
# #         leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
# #         rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

# #         # --- YARN DISTRIBUTOR SEQUENCE (MOVE IN & HOLD) ---
# #         print(">> Yarn Arm: Moving in to position...")
# #         move_result = yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
# #         if move_result != 0:
# #             raise RuntimeError(f"Yarn arm failed to reach needle position: {move_result}")

# #         # DC ID2 timing is not specified; no automatic DC command here.
        
# #         open_yarn_swing(yarnarm)
        
# #         # ==========================================================
# #         # BREAKPOINT: YARN PLACING
# #         # (Insert manual pause, wait command, or debug input here)
# #         # ==========================================================
        
# #         close_yarn_swing(yarnarm)
# #         yarnarm.MoveL(waypoints["push_yarn"], tool=1, user=2, vel=self.velocity)
        
# #         print(">> Yarn Arm: Holding position...")
        
# #         # --- GRIPPER STITCHING SEQUENCE ---
        
# #         # Step 1: Left arm works while Right is safely parked
# #         print(">> Left Arm: Initiating Step 1 (Pulling old loop West & Holding Close)...")
# #         leftarm.MoveL(waypoints["hover_east_L"], tool=1, user=2, vel=self.velocity)
# #         leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
# #         open_gripper(leftarm)
# #         leftarm.MoveL(waypoints["push_east_L"], tool=1, user=2, vel=self.velocity)
# #         close_gripper(leftarm)
        
# #         # Left arm pulls up and holds the yarn CLOSE (higher X value)
# #         leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
# #         leftarm.MoveL(waypoints["hold_close_west_L"], tool=1, user=2, vel=self.velocity)

# #         # Step 2: Right arm works while Left holds the yarn
# #         print(">> Right Arm: Initiating Step 2 (Moving yarn to East needle)...")
# #         rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
# #         rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        
# #         # Ensure gripper is open before plunging down to grab the new yarn
# #         open_gripper(rightarm) 
# #         rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
# #         close_gripper(rightarm)
        
# #         # Move yarn from West to East
# #         rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
# #         rightarm.MoveL(waypoints["above_east_R"], tool=1, user=2, vel=self.velocity)
# #         rightarm.MoveL(waypoints["push_east_R"], tool=1, user=2, vel=self.velocity)
        
# #         # Release and retract
# #         open_gripper(rightarm)
# #         rightarm.MoveL(waypoints["diagonal_retract_east_R"], tool=1, user=2, vel=self.velocity)
# #         rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

# #         # Left arm can now release and return to deep hover
# #         open_gripper(leftarm)
# #         leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
# #         # -------------------------------------------------

# #         # --- YARN DISTRIBUTOR SEQUENCE (RELEASE & STOP) ---
# #         print(">> Yarn Arm: Stitch complete. Releasing yarn and stopping in place...")
# #         open_yarn_swing(yarnarm)
# #         # (Retraction moves completely removed here)


# # def main():
# #     global robotyarn, robotleft, robotright
# #     # Validate BEFORE connecting to or moving any robot.
# #     validate_yarn_swing_positions()
# #     try:
# #         robotyarn = Robot.RPC('192.168.0.50')
# #         robotleft = Robot.RPC('192.168.0.51')
# #         robotright = Robot.RPC('192.168.0.52')
# #         needle_bed = {}
# #         for x in range(6):
# #             for y in range(6):
# #                 needle_bed[(x, y)] = Needle(grid_x=x, grid_y=y)
# #         print("--- Initiating Single Stitch at Needle (1, 1) ---")
# #         target_needle = needle_bed[(1, 1)]
# #         target_needle.simple_stitch(robotleft, robotright, robotyarn)
# #     finally:
# #         # Closing RPC releases connections; it is NOT a robot emergency stop.
# #         for arm in (robotyarn, robotleft, robotright):
# #             if arm is not None:
# #                 try:
# #                     arm.CloseRPC()
# #                 except Exception as exc:
# #                     print(f"CloseRPC failed: {exc}")


# # if __name__ == "__main__":
# #     main()

# """Single stitch: .50 RS-485 MG90S; .51/.52 control-box AO.
# Assumes MG90S ID1 replaces the legacy yarn swing.
# MG90S goes to 100 after above_yarn, then to 0 after both arms finish.
# DC START is sent once after the MG90S 100 command succeeds.
# Motion coordinates and stitch order are preserved from the supplied source.
# """
# from fairino import Robot
# import time

# # .51 / .52 retain their original control-box AO commands.
# def close_gripper(arm):
#     print("Gripper closing...")
#     arm.SetAO(0, 0.0)
#     time.sleep(0.5)


# def open_gripper(arm):
#     print("Gripper opening...")
#     arm.SetAO(0, 13.0)
#     time.sleep(0.5)


# # .50 RS-485 motors; argument format matches the supplied working API test.
# MG90S_ID = 1
# DC_MOTOR_ID = 2
# SPEED = 50
# FORCE = 0
# MAX_TIME_MS = 10000

# # Positions explicitly requested for this stitch sequence.
# YARN_SWING_OPEN_POS = 0
# YARN_SWING_CLOSE_POS = 100

# robotyarn = None
# robotleft = None
# robotright = None


# def validate_yarn_swing_positions():
#     for name, position in (
#         ("YARN_SWING_OPEN_POS", YARN_SWING_OPEN_POS),
#         ("YARN_SWING_CLOSE_POS", YARN_SWING_CLOSE_POS),
#     ):
#         if type(position) is not int or not 0 <= position <= 100:
#             raise ValueError(
#                 f"Set {name} to a verified integer position (0-100) before running."
#             )


# def yarn_motor_command(arm, motor_id, value):
#     if arm is None or arm is not robotyarn:
#         raise ValueError("Yarn motor commands must use robotyarn (.50).")
#     if motor_id == MG90S_ID:
#         if type(value) is not int or not 0 <= value <= 100:
#             raise ValueError("MG90S position must be an integer from 0 to 100.")
#     elif motor_id == DC_MOTOR_ID:
#         if type(value) is not int or value not in (0, 1, 2):
#             raise ValueError("DC command must be 0=STOP, 1=START, or 2=REVERSE.")
#     else:
#         raise ValueError("Unsupported yarn motor ID.")
#     result = arm.MoveGripper(
#         motor_id, value, SPEED, FORCE, MAX_TIME_MS, 0, 0, 0, 0, 0
#     )
#     if result != 0:
#         raise RuntimeError(
#             f".50 MoveGripper failed: ID={motor_id}, value={value}, return={result}"
#         )
#     return result


# def close_yarn_swing(arm):
#     validate_yarn_swing_positions()
#     print("Yarn swing closing (Holding yarn)...")
#     yarn_motor_command(arm, MG90S_ID, YARN_SWING_CLOSE_POS)
#     time.sleep(0.5)


# def open_yarn_swing(arm):
#     validate_yarn_swing_positions()
#     print("Yarn swing opening (Releasing yarn)...")
#     yarn_motor_command(arm, MG90S_ID, YARN_SWING_OPEN_POS)
#     time.sleep(0.5)


# # DC START is called once in simple_stitch, after MG90S 100.
# # No DC run time, rotation count, or automatic stop is inferred here.
# def start_yarn_dc(arm):
#     return yarn_motor_command(arm, DC_MOTOR_ID, 1)


# def reverse_yarn_dc(arm):
#     return yarn_motor_command(arm, DC_MOTOR_ID, 2)


# def stop_yarn_dc(arm):
#     return yarn_motor_command(arm, DC_MOTOR_ID, 0)


# # --- Calibration Databases ---
# def generate_calibration_map():
#     safe_map = {}
    
#     # # Exact physical coordinates measured with the Right Arm
#     # measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
#     # measured_y = [-0.4, 14.6, 29.7, 44.3, 60, 74.8]
#     # New 1021
#     measured_x = [.9, 16.246, 31, 46.3, 60.7, 76.1]
#     measured_y = [4.6, 18.8, 33.8, 48.4, 63.2, 78.4]
    
#     for x in range(6):
#         for y in range(6):
#             safe_map[(x, y)] = (measured_x[x], measured_y[y])
            
#     return safe_map

# PHYSICAL_NEEDLE_MAP = generate_calibration_map()

# def get_physical_location(grid_x, grid_y):
#     return PHYSICAL_NEEDLE_MAP.get((grid_x, grid_y), None)

# def get_yarn_physical_location(grid_x, grid_y):
#     """
#     Independent mapping for the Yarn Distributor (3rd Arm).
#     Currently isolated to perfect the 1,1 stitch location.
#     """

#     # hard-coded mapping for the yarn distributor at (1, 1), into west needle position
#     yarn_map = {
#         (1, 1): (10.95, 21.42)
#     }
#     # Fallback to standard mapping if not defined
#     return yarn_map.get((grid_x, grid_y), get_physical_location(grid_x, grid_y))


# # --- Needle Object ---
# class Needle:
#     def __init__(self, grid_x, grid_y):
#         self.grid_x = grid_x
#         self.grid_y = grid_y
        
#         # 1. Base Physical Coordinates (For Left/Right Grippers)
#         physical_coords = get_physical_location(self.grid_x, self.grid_y)
#         if physical_coords is None:
#             raise ValueError(f"Needle ({self.grid_x}, {self.grid_y}) is out of bounds.")
#         self.physical_x, self.physical_y = physical_coords
        
#         # 2. Yarn Physical Coordinates (For Distributor)
#         yarn_coords = get_yarn_physical_location(self.grid_x, self.grid_y)
#         self.yarn_physical_x, self.yarn_physical_y = yarn_coords
        
#         # Arm Offsets
#         self.left_x_offset = 4.77          
#         self.base_x_L = self.physical_x - self.left_x_offset
#         self.left_y_offset = 3.65
#         self.base_y_L = self.physical_y - self.left_y_offset
        
#         # --- YARN DISTRIBUTOR DIRECTIONAL OFFSET (NORTH/SOUTH) ---
#         # 1 = South to North | -1 = North to South
#         self.yarn_direction = 1 
        
#         # The physical distance to shift the tool along the Y-axis so the gap frames the needle
#         self.yarn_gap_offset_y = 0 
        
#         # Calculates the base coordinates for the yarn arm
#         self.base_x_Y = self.yarn_physical_x 
#         self.base_y_Y = self.yarn_physical_y + (self.yarn_gap_offset_y * self.yarn_direction)
        
#         # --- COLLISION AVOIDANCE HOVER OFFSETS ---
#         self.clearance_x = 75.0      # Lowered to keep Left arm in reachable workspace
#         self.yarn_y_hover_offset = 50.0 
        
#         # Z-heights for the stages of a stitch
#         self.z_hover = 70.0         
#         self.z_above = 38.0  
#         self.z_push = 28.0
        
#         # Independent diagonal retraction amounts (Y set to 0)
#         self.diag_retract_x = 1.5
#         self.diag_retract_y = 0.0
        
#         self.rot_left = [0.0, 0.0, 0.0] 
#         self.rot_right = [0.0, 0.0, 0.0] 
#         self.rot_yarn = [0.0, 0.0, 0.0]
        
#         self.offset_dist = 1.3
#         self.velocity = 5
        

#     def simple_stitch(self, leftarm, rightarm, yarnarm):
#         bx, by = self.physical_x, self.physical_y
#         bx_L = self.base_x_L
#         by_L = self.base_y_L
#         bx_Y, by_Y = self.base_x_Y, self.base_y_Y
#         yyh = self.yarn_y_hover_offset
#         od = self.offset_dist
#         cx = self.clearance_x
#         zh, za, zp = self.z_hover, self.z_above, self.z_push
#         dx, dy = self.diag_retract_x, self.diag_retract_y
#         rl, rr, ry = self.rot_left, self.rot_right, self.rot_yarn

#         # Pre-calculated physical waypoints for all three arms
#         waypoints = {
#             # Yarn Distributor Waypoints 
#             "hover_yarn":  [bx_Y, by_Y + yyh, zh] + ry,
#             "above_yarn":  [bx_Y, by_Y, za] + ry,
#             "push_yarn":   [bx_Y, by_Y, zp + 5] + ry,
            
#             # Left Arm Waypoints 
#             "hover_west_L": [bx_L - od - cx, by_L, zh] + rl,
#             "above_west_L": [bx_L - od, by_L, za] + rl,
#             "push_west_L":  [bx_L - od, by_L, zp] + rl,
#             "diagonal_retract_west_L": [bx_L - od - dx, by_L + dy, za] + rl,
#             "hold_close_west_L": [bx_L - (od*8.5), by_L, za] + rl,  # <--- New close hold position
#             "hover_east_L": [bx_L + od - cx, by_L, zh] + rl,
#             "above_east_L": [bx_L + od, by_L, za] + rl,
#             "push_east_L":  [bx_L + od, by_L, zp] + rl,
#             "diagonal_retract_east_L": [bx_L + od - dx, by_L + dy, za] + rl,
            
#             # Right Arm Waypoints 
#             "hover_west_R": [bx - od + cx, by, zh] + rr,
#             "above_west_R": [bx - od, by, za] + rr,
#             "push_west_R":  [bx - od, by, zp] + rr,
#             "diagonal_retract_west_R": [bx - od + dx, by + dy, za] + rr,
#             "hover_east_R": [bx + od + cx, by, zh] + rr,
#             "above_east_R": [bx + od, by, za] + rr,
#             "push_east_R":  [bx + od, by, zp] + rr,
#             "diagonal_retract_east_R": [bx + od + dx, by + dy, za] + rr
#         }

#         # 0. Initialize all to safe parking corners
#         print(">> Parking all arms in safe hovers...")
#         #yarnarm.MoveL(waypoints["hover_yarn"], tool=1, user=2, vel=self.velocity)
#         leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
#         rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

#         # --- YARN DISTRIBUTOR SEQUENCE (MOVE IN & HOLD) ---
#         print(">> Yarn Arm: Moving in to position...")
#         move_result = yarnarm.MoveL(waypoints["above_yarn"], tool=1, user=2, vel=self.velocity)
#         if move_result != 0:
#             raise RuntimeError(f"Yarn arm failed to reach needle position: {move_result}")

#         # One MG90S 100 command, followed by one DC START command.
#         # Successful API return is not a measurement of the actual servo angle.
#         close_yarn_swing(yarnarm)
#         start_yarn_dc(yarnarm)
#         yarnarm.MoveL(waypoints["push_yarn"], tool=1, user=2, vel=self.velocity)
        
#         print(">> Yarn Arm: Holding position...")
        
#         # --- GRIPPER STITCHING SEQUENCE ---
        
#         # Step 1: Left arm works while Right is safely parked
#         print(">> Left Arm: Initiating Step 1 (Pulling old loop West & Holding Close)...")
#         leftarm.MoveL(waypoints["hover_east_L"], tool=1, user=2, vel=self.velocity)
#         leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
#         open_gripper(leftarm)
#         leftarm.MoveL(waypoints["push_east_L"], tool=1, user=2, vel=self.velocity)
#         close_gripper(leftarm)
        
#         # Left arm pulls up and holds the yarn CLOSE (higher X value)
#         leftarm.MoveL(waypoints["above_east_L"], tool=1, user=2, vel=self.velocity)
#         leftarm.MoveL(waypoints["hold_close_west_L"], tool=1, user=2, vel=self.velocity)

#         # Step 2: Right arm works while Left holds the yarn
#         print(">> Right Arm: Initiating Step 2 (Moving yarn to East needle)...")
#         rightarm.MoveL(waypoints["hover_west_R"], tool=1, user=2, vel=self.velocity)
#         rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
        
#         # Ensure gripper is open before plunging down to grab the new yarn
#         open_gripper(rightarm) 
#         rightarm.MoveL(waypoints["push_west_R"], tool=1, user=2, vel=self.velocity)
#         close_gripper(rightarm)
        
#         # Move yarn from West to East
#         rightarm.MoveL(waypoints["above_west_R"], tool=1, user=2, vel=self.velocity)
#         rightarm.MoveL(waypoints["above_east_R"], tool=1, user=2, vel=self.velocity)
#         rightarm.MoveL(waypoints["push_east_R"], tool=1, user=2, vel=self.velocity)
        
#         # Release and retract
#         open_gripper(rightarm)
#         rightarm.MoveL(waypoints["diagonal_retract_east_R"], tool=1, user=2, vel=self.velocity)
#         rightarm.MoveL(waypoints["hover_east_R"], tool=1, user=2, vel=self.velocity)

#         # Left arm can now release and return to deep hover
#         open_gripper(leftarm)
#         leftarm.MoveL(waypoints["hover_west_L"], tool=1, user=2, vel=self.velocity)
#         # -------------------------------------------------

#         # --- YARN DISTRIBUTOR SEQUENCE (RELEASE & STOP) ---
#         print(">> Yarn Arm: Stitch complete. Releasing yarn and stopping in place...")
#         open_yarn_swing(yarnarm)
#         # (Retraction moves completely removed here)


# def main():
#     global robotyarn, robotleft, robotright
#     # Validate BEFORE connecting to or moving any robot.
#     validate_yarn_swing_positions()
#     try:
#         robotyarn = Robot.RPC('192.168.0.50')
#         robotleft = Robot.RPC('192.168.0.51')
#         robotright = Robot.RPC('192.168.0.52')
#         needle_bed = {}
#         for x in range(6):
#             for y in range(6):
#                 needle_bed[(x, y)] = Needle(grid_x=x, grid_y=y)
#         print("--- Initiating Single Stitch at Needle (1, 1) ---")
#         target_needle = needle_bed[(1, 1)]
#         target_needle.simple_stitch(robotleft, robotright, robotyarn)
#     finally:
#         # Closing RPC releases connections; it is NOT a robot emergency stop.
#         for arm in (robotyarn, robotleft, robotright):
#             if arm is not None:
#                 try:
#                     arm.CloseRPC()
#                 except Exception as exc:
#                     print(f"CloseRPC failed: {exc}")


# if __name__ == "__main__":
#     main()

"""Fixed-layer single stitch, calibrated 2026-10-23.
Coordinates are in the existing tool=1 / user=2 frames, in mm.
DC feed is TIMED, not encoder-measured. Confirm DC_FEED_SECONDS on hardware.
"""
import argparse
import time

YARN_IP = '192.168.0.50'
LEFT_IP = '192.168.0.51'
RIGHT_IP = '192.168.0.52'
TOOL_ID = 1
USER_ID = 2
VELOCITY = 5
YARN_ROT = (0.0, 0.0, 0.0)
LEFT_ROT = (0.0, 0.0, 0.0)
RIGHT_ROT = (0.0, 0.0, 0.0)

YARN_WORK_XYZ = (10.95, 22.42, 33.4)

LEFT_PICK_X = 13.33
LEFT_PICK_Y = 15.12
LEFT_LOW_Z = 28.0
LEFT_ENTRY_Y_DELTA = 0.01  # entry/parking Y=15.13; pick/hold Y=15.12
LEFT_ENTRY_Z_IS_LOW = False  # requested entry Z=28, NOT 38
# Original initial hover_west_L X: 16.246 - 4.77 - 1.3 - 75
LEFT_PARK_X = -64.824

RIGHT_PICK_X = 13.30
RIGHT_PICK_Y = 18.80
RIGHT_LOW_Z = 27.0
# Original hover_east_R X: 16.246 + 1.3 + 75
RIGHT_PARK_X = 92.546

# ==================== FIXED RELATIVE DISTANCES ====================
VERTICAL_TRAVEL = 10.0     # left 28<->38; right 27<->37
NEEDLE_PITCH_X = 3.18      # right pickup -> release along +X
LEFT_PULL_BACK_X = 13.99  # 13.33 - 13.99 = -0.66, along -X

# ==================== MOTOR SETTINGS ====================
AO_CHANNEL = 0
AO_OPEN = 13.0
AO_CLOSED = 0.0
GRIP_SETTLE_SECONDS = 0.5
MG90S_ID = 1
DC_MOTOR_ID = 2
MOTOR_SPEED = 50
MOTOR_FORCE = 0
MAX_TIME_MS = 10000
SERVO_WORK_POS = 100
SERVO_FINISH_POS = 0
# Previous nominal one-cycle duration. Recalibrate for load/supply/speed.
# This is not angle feedback. A STOP command is sent after the timed interval.
DC_FEED_SECONDS = 7.5


def build_waypoints():
    left_high = LEFT_LOW_Z + VERTICAL_TRAVEL
    right_high = RIGHT_LOW_Z + VERTICAL_TRAVEL
    left_entry_y = round(LEFT_PICK_Y + LEFT_ENTRY_Y_DELTA, 6)
    left_hold_x = round(LEFT_PICK_X - LEFT_PULL_BACK_X, 6)
    right_release_x = round(RIGHT_PICK_X + NEEDLE_PITCH_X, 6)
    def pose(x, y, z, rotation):
        return [x, y, z, *rotation]
    return {
        'yarn_work': [*YARN_WORK_XYZ, *YARN_ROT],
        'left_park': pose(LEFT_PARK_X, left_entry_y, left_high, LEFT_ROT),
        'left_entry': pose(LEFT_PICK_X, left_entry_y,
                           LEFT_LOW_Z if LEFT_ENTRY_Z_IS_LOW else left_high, LEFT_ROT),
        'left_pick': pose(LEFT_PICK_X, LEFT_PICK_Y, LEFT_LOW_Z, LEFT_ROT),
        'left_lift': pose(LEFT_PICK_X, LEFT_PICK_Y, left_high, LEFT_ROT),
        'left_hold': pose(left_hold_x, LEFT_PICK_Y, left_high, LEFT_ROT),
        'right_park': pose(RIGHT_PARK_X, RIGHT_PICK_Y, right_high, RIGHT_ROT),
        'right_above_pick': pose(RIGHT_PICK_X, RIGHT_PICK_Y, right_high, RIGHT_ROT),
        'right_pick': pose(RIGHT_PICK_X, RIGHT_PICK_Y, RIGHT_LOW_Z, RIGHT_ROT),
        'right_above_release': pose(right_release_x, RIGHT_PICK_Y, right_high, RIGHT_ROT),
        'right_release': pose(right_release_x, RIGHT_PICK_Y, RIGHT_LOW_Z, RIGHT_ROT),
    }


class StitchController:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.arms = {}
        self.points = build_waypoints()
        self.dc_may_be_running = False

    def connect(self):
        if self.dry_run:
            return
        from fairino import Robot
        for name, ip in (('yarn', YARN_IP), ('left', LEFT_IP), ('right', RIGHT_IP)):
            self.arms[name] = Robot.RPC(ip)

    def wait(self, seconds):
        if not self.dry_run:
            time.sleep(seconds)

    @staticmethod
    def check(result, action):
        if result != 0:
            raise RuntimeError(f'{action} failed: return={result}; sequence aborted')

    def move(self, arm, point):
        target = self.points[point]
        print(f'MOVE {arm}: {point} {target}')
        if not self.dry_run:
            result = self.arms[arm].MoveL(target, tool=TOOL_ID, user=USER_ID, vel=VELOCITY)
            self.check(result, f'{arm} MoveL {point}')

    def gripper(self, arm, opened):
        value = AO_OPEN if opened else AO_CLOSED
        print(f'AO {arm}: {value}%')
        if not self.dry_run:
            self.check(self.arms[arm].SetAO(AO_CHANNEL, value), f'{arm} SetAO {value}')
        self.wait(GRIP_SETTLE_SECONDS)

    def motor(self, motor_id, value):
        print(f'RS485 yarn: ID={motor_id}, value={value}')
        if not self.dry_run:
            self.check(self.arms['yarn'].MoveGripper(
                motor_id, value, MOTOR_SPEED, MOTOR_FORCE,
                MAX_TIME_MS, 0, 0, 0, 0, 0
            ), f'MoveGripper ID={motor_id} value={value}')

    def feed_once(self):
        # Mark before START so a failed response still results in a STOP attempt.
        self.dc_may_be_running = True
        started = time.monotonic()
        self.motor(DC_MOTOR_ID, 1)
        # API may itself block. Wait only the remaining part of the timed interval.
        remaining = max(0.0, DC_FEED_SECONDS - (time.monotonic() - started))
        print(f'DC timed feed: configured duration {DC_FEED_SECONDS}s (not measured rotation)')
        self.wait(remaining)
        self.motor(DC_MOTOR_ID, 0)
        self.dc_may_be_running = False

    def run_stitch(self):
        # Retain original pre-parking before bringing .50 into the work area.
        self.move('left', 'left_park')
        self.move('right', 'right_park')

        # .50: one fixed work point -> DC forward/stop -> MG90S 100.
        self.move('yarn', 'yarn_work')
        self.feed_once()
        self.motor(MG90S_ID, SERVO_WORK_POS)
        self.wait(GRIP_SETTLE_SECONDS)

        # .51: requested entry Z is already 28. Next move changes Y by -0.01 only.
        self.move('left', 'left_entry')
        self.gripper('left', True)
        self.move('left', 'left_pick')
        self.gripper('left', False)
        self.move('left', 'left_lift')
        self.move('left', 'left_hold')
        # Left remains closed while the right arm performs its full sequence.

        # .52: open before entering, pick -> lift -> +3.18 -> lower -> release.
        self.gripper('right', True)
        self.move('right', 'right_above_pick')
        self.move('right', 'right_pick')
        self.gripper('right', False)
        self.move('right', 'right_above_pick')
        self.move('right', 'right_above_release')
        self.move('right', 'right_release')
        self.gripper('right', True)
        self.move('right', 'right_above_release')
        self.move('right', 'right_park')

        # Retain original end sequence: left releases/parks, then MG90S returns to 0.
        self.gripper('left', True)
        self.move('left', 'left_park')
        self.motor(MG90S_ID, SERVO_FINISH_POS)
        self.wait(GRIP_SETTLE_SECONDS)

    def close(self):
        # Best-effort DC stop after an interrupted feed; no automatic arm recovery.
        if self.dc_may_be_running and (self.dry_run or 'yarn' in self.arms):
            try:
                self.motor(DC_MOTOR_ID, 0)
            except Exception as exc:
                print(f'DC STOP failed: {exc}')
        for name, arm in self.arms.items():
            try:
                arm.CloseRPC()  # Disconnect only; NOT an emergency stop.
            except Exception as exc:
                print(f'{name} CloseRPC failed: {exc}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Print sequence without SDK/network/motion')
    args = parser.parse_args()
    if DC_FEED_SECONDS <= 0 or VERTICAL_TRAVEL <= 0:
        raise ValueError('DC_FEED_SECONDS and VERTICAL_TRAVEL must be positive')
    controller = StitchController(dry_run=args.dry_run)
    try:
        controller.connect()
        controller.run_stitch()
    finally:
        controller.close()


if __name__ == '__main__':
    main()

