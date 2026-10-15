# Robotic Knitting

Python scripts for robotic knitting with three FAIRINO robot arms and the FAIRINO Python SDK. Two arms manipulate yarn loops, while a third arm positions and holds the yarn.

The project maps a **6 × 6 needle bed**. The current knitting script runs **one stitch at needle `(1, 1)`**, rather than knitting the full grid.

## Files

| File | Purpose |
| --- | --- |
| `test.py` | Runs the three-arm single-stitch sequence. |
| `calibration_test.py` | Moves an arm across the needle bed to check alignment. Tests the right arm by default. |
| `fairino/Robot.py` | Included FAIRINO Python SDK implementation. |
| `fairino/README.txt` | SDK release notes bundled with the project. |
| `fairino/LICENSE` | License for the included SDK. |

## Setup

You need Python 3, the configured robot hardware, and a computer connected to the robot controllers' network. Use a Python version and SDK compatible with your controller firmware.

From the project folder, create a virtual environment and install the SDK's external dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install python-mbedtls
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

Keep the `fairino` folder beside the scripts so this import works:

```python
from fairino import Robot
```

## Robot configuration

The controller addresses are set near the top of each script:

| Arm | IP address | Role |
| --- | --- | --- |
| Yarn arm | `192.168.0.50` | Positions and holds yarn. |
| Left arm | `192.168.0.51` | Pulls and holds the existing loop. |
| Right arm | `192.168.0.52` | Moves yarn to the other needle. |

Update these addresses if your setup differs. Both scripts use **tool frame `1`** and **user frame `2`**, which must be calibrated on the robots for this needle bed.

Before running, check the measured needle coordinates, tool offsets, motion heights, and analog-output settings against the installed hardware. Clear the motion area and keep the emergency stop accessible.

**Both scripts send real hardware commands immediately when run or imported. There is no simulation mode or confirmation prompt.**

## Check calibration

After verifying the setup, run:

```bash
python calibration_test.py
```

This moves the right arm across all 36 grid positions, lifting between rows and returning to a hover position afterward. It also connects to the left controller.

To check the left arm instead, disable the right-arm execution calls at the bottom of the file and enable:

```python
test_calibration_path(robotleft, needle_bed, is_left_arm=True)
```

The calibration values are stored separately in each script. Currently, they differ:

| Setting | `calibration_test.py` | `test.py` |
| --- | --- | --- |
| Second measured Y coordinate | `14.2` | `14.6` |
| Left-arm X offset | `2.6` | `3.2` |

Verify which values match the hardware before using calibration results for stitching.

## Run one stitch

After checking calibration and the three-arm paths, run:

```bash
python test.py
```

The script performs these steps in sequence:

1. Moves the left and right arms to their configured hover positions.
2. Positions the yarn arm and closes its yarn swing to hold the yarn.
3. Uses the left arm to pull and hold the existing loop.
4. Uses the right arm to pick up yarn and move it from west to east.
5. Releases and retracts the left and right grippers.
6. Opens the yarn swing. The yarn arm stays in place at the end.

## Adjust the stitch

In `test.py`:

- **Needle coordinates:** edit `measured_x` and `measured_y` in `generate_calibration_map()`.
- **Motion settings:** edit offsets, heights, rotations, and `velocity` in `Needle.__init__()`.
- **Target needle:** change `needle_bed[(1, 1)]` at the bottom. Grid indices range from `0` to `5`.
- **Yarn-arm alignment:** edit `get_yarn_physical_location()`. Only `(1, 1)` currently has a dedicated yarn-arm coordinate; other positions fall back to the main needle map and need verification.
- **Gripper control:** edit the `SetAO` values in the gripper and yarn-swing functions to match the hardware.

## Current limitations

- The RS-485 yarn feeder code is commented out and disabled.
- The initial yarn-arm hover move is commented out; its first active move goes directly to the above-needle position.
- The “BREAKPOINT: YARN PLACING” comment does not pause execution.
- Most motion and gripper calls do not check return codes. Review controller status during operation.
- These are hardware experiment scripts, not automated software tests.
