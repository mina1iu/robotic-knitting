# Developer notes

## Needle calibration reference

When recording a needle's X/Y coordinates, align the **back middle pincher with the middle of the needle**. This is the physical alignment reference for the saved calibration points.

Use this reference consistently when measuring each needle for each arm.

## What each file does

- `calibration.json`: the current measurements and robot settings. This is the file to edit.
- `calibration.py`: reads those measurements, checks the requested points, and builds a list of movement poses. It never connects to robots.
- `calibration_test.py`: validates and prints that list, then connects to the selected robot and performs real movements. There is no preview mode.
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

Run one left-arm needle with real movement:

```bash
python3 calibration_test.py left --needle 0 0
```

Run all 36 left-arm needles with real movement:

```bash
python3 calibration_test.py left
```

Check the tool, user frame, orientation, heights, and physical route before starting. These commands start real motion after validation and printing the plan, without another confirmation. Older commands with `--execute` still work, but the flag is unnecessary.

Replace `left` with `middle` or `right` only after entering and checking that arm's measurements. The script connects only to the selected arm.

## Running with the VS Code debugger

1. Open the `robotic-knitting` folder in VS Code and save `calibration.json`.
2. Press **⌘⇧D** to open Run and Debug.
3. Select **Debug left calibration (REAL MOTION)** or **Debug right calibration (REAL MOTION)** in the dropdown.
4. Press **F5** to debug, or **Ctrl+F5** to run without debugging. Both perform real movement through all 36 needles for the selected arm.

Both configurations enable `--pause-each-row`. After each row's final rise to upper Z, execution waits in the integrated terminal. Click the terminal and press **Enter** to continue, or type **q** and press Enter to stop without further movement. Any nonempty response, Ctrl+C, or closed input stops the sequence. The final row also pauses before the return to the demo hover. No breakpoint is required.

Equivalent right-arm terminal command (REAL MOTION):

```bash
python3 calibration_test.py right --execute --pause-each-row
```

Using **Current File** without arguments causes `SystemExit: 2` because the script requires an arm name. If the named configurations are missing, open this repository folder (not just the Python file) and run **Developer: Reload Window** from the Command Palette.

Pausing Python does not stop a movement already sent to the controller. The row pause occurs after the blocking movement returns; keep the controller's stop/emergency stop available during physical testing.

## Movement sequence

For each point, the script:

1. Moves to that point's X/Y at `upper_z`.
2. Moves straight down to `lower_z`, keeping X/Y and orientation unchanged.
3. Moves straight back up to `upper_z`.
4. Moves to the next point at `upper_z` and repeats.

The full-grid order is `(0,0), (1,0), …, (5,0)`, then `(0,1)` through `(5,1)`, continuing through row 5. After the final needle, it returns to the existing stitch-demo hover pose. The route also starts with a move to that hover pose.

Velocity is set to `15` in `calibration_test.py`: the SDK interprets this as **15% speed**, not 15 mm/s. Each `MoveL` uses `blendR=-1`, so it waits for completion before issuing the next move. No sideways motion is planned at lower Z. There are no gripper, home, or park commands.

The first command moves directly from the robot's current position to the existing stitch-demo hover pose; it does not first lift vertically from the current position. Check that initial route and the routes between points before executing. Keep the controller's stop/emergency stop available.

## Validation and failures

The complete requested path is checked before connecting. All requested points must have status `measured` and valid X/Y numbers; heights and orientation must be finite numbers, with upper Z greater than lower Z. Invalid input prevents the run from starting.

An SDK error or exception ends the sequence without further movement commands. There is no automatic retreat or retry. A small local SDK addition lets this script disable `MoveL` socket retries; it also disables Python XML-RPC's automatic resend. Other SDK callers retain the original retry default. If communication fails, the last command's outcome may be unknown; exiting the script is not a controller emergency stop.

Offline checks:

```bash
python3 -m unittest discover -s tests -v
```

These verify software behavior with fake robots. They do not verify physical clearance or hardware behavior.
