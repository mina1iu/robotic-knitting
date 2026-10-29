# Robotic knitting

Start with [DEV_NOTES.md](DEV_NOTES.md) for entering measurements and running the calibration check.

| File | Purpose | When to use it |
| --- | --- | --- |
| `calibration.json` | Saved X/Y measurements for each needle and arm; shared upper/lower Z heights and robot settings. | Edit your measurements here. |
| `calibration_test.py` | Checks physical needle alignment using the down/up sequence. Previews by default; `--execute` moves the selected robot. | Run this to check alignment. |
| `calibration.py` | Reads the JSON, validates requested points, and builds poses. No hardware connections. | Helper imported by the check script; normally leave it alone. |
| `stitch_demo.py` | Original single-stitch demonstration, formerly `test.py`. Uses its own older coordinates, not the JSON. | Separate stitch experiment; running it performs real motion. |
| `tests/test_calibration_software.py` | Automated software checks using fake robots. Not used when running the robot alignment check. | Run when changing the code. |
| `DEV_NOTES.md` | Alignment reference, measurement format, execution commands, and behavior. | Developer operating guide. |
| `AGENTS.md` | Repository instructions for coding assistants. | Development guidance, not robot configuration. |
| `fairino/` | Bundled robot SDK and its license/release notes. | Used by hardware scripts. Local `MoveL` retry option is explained in the developer notes. |

`calibration_cli.py` and the old root `test.py` are no longer present. If they still appear as editor tabs, those tabs refer to removed/renamed files. Close them rather than saving them back into the project.
