# Robotic knitting

## Files

- `stitch_demo.py` (formerly `test.py`): demonstrates one stitch using the original stitch coordinates and gripper sequence. Running it connects to all three robots and performs real movement. Importing it does not.
- `calibration.json`: enter each robot's manually measured needle X/Y positions here.
- `calibration.py`: reads those positions and builds the calibration-test sequence.
- `calibration_test.py`: prints the planned sequence without connecting to hardware.
- `tests/test_calibration.py`: offline software checks.

## Enter your points

Measure positions in each robot's web app, using the tool/user frame recorded for that arm in `calibration.json`. The three robots' coordinate frames are independent.

For each arm, find a needle entry such as `"2,1"` (column 2, row 1):

```json
"2,1": {"xy": null, "status": "uncalibrated"}
```

Replace `null` with that arm's actual `[X, Y]` measurement and change status to `measured`. For example, these made-up numbers show the syntax:

```json
"2,1": {"xy": [31.2, 18.4], "status": "measured"}
```

All 108 entries start empty. Each arm has its own full set of 36 independent X/Y pairs. Even needles in the same row/column can have different physical Y/X values; nothing is copied, averaged, or inferred.

## Set the two test heights once

Near the top of `calibration.json`:

```json
"test_heights": {"upper_z": null, "lower_z": null}
```

Replace both nulls with the installed setup's verified heights in millimeters. These two values apply to **every needle and every arm**, as requested. They are not repeated per needle. Upper Z must be greater than lower Z.

Each arm's `orientation` holds its fixed `[RX, RY, RZ]` in degrees for this test. The initial `[0,0,0]` comes from the original script; verify it for each robot. Tool 1/user 2 also need to match the web app.

For each needle, the planned path is:

1. Move to its X/Y at `upper_z`.
2. Lower to `lower_z`, keeping X/Y and orientation unchanged.
3. Rise to `upper_z`, keeping X/Y and orientation unchanged.
4. Travel to the next needle at `upper_z` and repeat.

Full-grid order is `(0,0)` through `(5,0)`, then row 1, and so on. There is no sideways movement at lower Z and no automatic home move. The route from the current robot position to the first upper pose still needs to be checked. Identical numeric heights across different robot frames must be verified physically for each arm.

## Preview without moving robots

After entering heights and one needle:

```bash
python3 calibration_test.py left --needle 2 1
```

After entering all 36 needles for an arm:

```bash
python3 calibration_test.py left
```

The preview validates the complete requested path before printing it. Missing measurements produce an error. These commands **only print poses**. Hardware execution remains unimplemented: the bundled SDK retries socket errors internally, so a fail-stop transport and an explicitly configured execution speed are still needed before a hardware runner can meet the requested failure behavior.

## Stitch demonstration

`stitch_demo.py` retains its original stitch-specific waypoints and heights. Its needle dip/pull/yarn motions differ from the calibration test's straight down/up motion. It has not been connected to the JSON yet. Running it performs real hardware operations; use it only after checking the installed setup.

Moving the bed/base or changing grippers, tool definitions, or user frames requires remeasuring affected positions.

## Offline software checks

```bash
python3 -m unittest discover -s tests -v
```
