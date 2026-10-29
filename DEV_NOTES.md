# Developer notes

## Needle calibration reference

When recording a needle's X/Y coordinates, align the **back middle pincher with the middle of the needle**. This is the physical alignment reference for the saved calibration points.

Use this reference consistently when measuring each needle for each arm.

## What each file does

- `calibration.json`: the current measurements and robot settings. This is the file to edit.
- `calibration.py`: reads those measurements, checks the requested points, and builds a list of movement poses. It never connects to robots.
- `calibration_test.py`: prints that list by default. With `--execute`, it connects to the selected robot and performs the movements.
- `stitch_demo.py`: formerly `test.py`. Runs the separate, original one-stitch demonstration. It still uses its own coordinates and heights, not the JSON calibration points. Do not use it to check these measurements.
- `tests/test_calibration_software.py`: software tests using fake robots; they do not move hardware.

The robot's tool/user-frame calibration and manual position measurements happen in its web app. These Python files store and use the numbers you recorded; they do not perform that web-app calibration.

## Entering measurements

In `calibration.json`, find the arm (`left`, `middle`, or `right`), then the needle ID. For example:

```json
"2,1": {"xy": [31.2, 18.4], "status": "measured"}
```

The numbers above illustrate the format. Use your own measured X/Y values in millimeters. `"2,1"` is column 2, row 1 (IDs run from 0 to 5), not physical X/Y. Leave unknown points as `"xy": null` with status `"uncalibrated"`.

Each arm has its own 36 independent X/Y pairs. Points in the same column can have different physical X values; points in the same row can have different physical Y values. Another arm's coordinates are never substituted.

The two test heights are stored once, near the top:

```json
"test_heights": {"upper_z": 45, "lower_z": 35}
```

These are the current settings, in millimeters, shared by every test point and arm. Each arm also has a fixed `orientation` `[RX, RY, RZ]` in degrees, plus its IP, tool ID, user-frame ID, and frame description. Confirm the settings match the web app and installed setup. Shared numeric heights do not establish that different robot frames have the same physical clearance.

## Running the actual calibration test

Save `calibration.json` first. Run commands from the repository folder, using the Python environment with the bundled FAIRINO SDK's dependencies installed.

First preview one needle without connecting:

```bash
python3 calibration_test.py left --needle 0 0
```

After checking the tool, user frame, orientation, heights, and physical route, execute that one needle:

```bash
python3 calibration_test.py left --needle 0 0 --execute
```

Preview all 36 left-arm needles:

```bash
python3 calibration_test.py left
```

Execute all 36 left-arm needles:

```bash
python3 calibration_test.py left --execute
```

Replace `left` with `middle` or `right` only after entering and checking that arm's measurements. The script connects only to the selected arm. **`--execute` starts real motion after printing the plan; there is no additional confirmation prompt.** Without that flag, the command only prints poses.

## Running with the VS Code debugger

1. Save `calibration.json` and open the root `calibration_test.py` (not the software tests under `tests/`).
2. Press **⌘⇧D** on macOS, or click the **Run and Debug** icon in the left sidebar.
3. At the top of that sidebar, click the configuration dropdown beside the green ▶ button. It may currently say **Python Debugger: Current File**.
4. Select **Calibration: left preview (no motion)** to print the full grid without moving, or **Calibration: left EXECUTE (real motion)** to move the left arm through all 36 needles.
5. Click the green ▶ button or press **F5** to start the selected configuration.

These named configurations live in `.vscode/launch.json` and supply the required `left` argument. The execution configuration also supplies `--execute`. Using **Current File** without arguments causes `SystemExit: 2` because the script requires an arm name.

To pause after each row, open `calibration_test.py` and click the left gutter beside this line inside `execute_path()` to set a breakpoint:

```python
print(f"Row {step['needle'][1]} complete; arm is at upper_z.", flush=True)
```

It is reached after X=0 through X=5 have finished for that row, after the final rise to upper Z. Press **F5** to continue through the next row. This breakpoint is only reached during execution, not preview.

Pausing Python does not stop a movement already sent to the controller. The row-end breakpoint waits until the blocking movement has returned; keep the controller's stop/emergency stop available during physical testing.

## Movement sequence

For each point, the script:

1. Moves to that point's X/Y at `upper_z`.
2. Moves straight down to `lower_z`, keeping X/Y and orientation unchanged.
3. Moves straight back up to `upper_z`.
4. Moves to the next point at `upper_z` and repeats.

The full-grid order is `(0,0), (1,0), …, (5,0)`, then `(0,1)` through `(5,1)`, continuing through row 5. It finishes above `(5,5)`. With `--needle`, it finishes above that needle instead.

Velocity is set to `10` in `calibration_test.py`: the SDK interprets this as **10% speed**, not 10 mm/s. Each `MoveL` uses `blendR=-1`, so it waits for completion before issuing the next move. No sideways motion is planned at lower Z. There are no gripper, home, or park commands.

The first command moves directly from the robot's current position to the first upper pose; it does not first lift vertically from the current position. Check that initial route and the routes between points before executing. Keep the controller's stop/emergency stop available.

## Validation and failures

The complete requested path is checked before connecting. All requested points must have status `measured` and valid X/Y numbers; heights and orientation must be finite numbers, with upper Z greater than lower Z. Invalid input prevents the run from starting.

An SDK error or exception ends the sequence without further movement commands. There is no automatic retreat or retry. A small local SDK addition lets this script disable `MoveL` socket retries; it also disables Python XML-RPC's automatic resend. Other SDK callers retain the original retry default. If communication fails, the last command's outcome may be unknown; exiting the script is not a controller emergency stop.

Offline checks:

```bash
python3 -m unittest discover -s tests -v
```

These verify software behavior with fake robots. They do not verify physical clearance or hardware behavior.
