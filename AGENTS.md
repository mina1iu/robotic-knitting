# Robotic Knitting Project

## Project purpose
Control three FAIRINO robot arms for automated knitting on a
6×6 needle bed.

Prefer readable, straightforward Python and small modules.
Inspect existing code before making changes, and preserve
working behavior unless the task requires changing it.

## Robot identities
- Left arm: 192.168.0.51
- Middle arm / yarn feeder: 192.168.0.50
- Right arm: 192.168.0.52

Verify these identities against the existing configuration
before using them. Keep robot configuration centralized.

## Hardware execution
- Never connect to or move physical robots while implementing,
  debugging, or running automated tests.
- Hardware execution requires an explicit user request.
- Importing a module must not connect to hardware or cause motion.
- Keep robot connections inside explicit execution entry points.
- Default motion-related CLI commands to offline preview.
- Never guess safe poses, speeds, workspace limits, or clearances.
- A target pose being valid does not establish that the path to it
  is collision-free.
- Stop issuing movement commands after an SDK error.
- Do not attempt automatic recovery movements.
- Do not change gripper or motor outputs as a side effect of
  calibration commands.

## Calibration model
- The bed has 36 needles with shared grid IDs:
  (grid_x, grid_y), where both values range from 0 through 5.
- Each arm may have different calibrated poses for the same needle.
- Shared needle IDs do not imply a shared physical coordinate frame.
- Store calibration data separately from knitting and motion logic.
- Record the arm, tool ID, user-frame ID, and coordinate-frame
  description with calibration data.
- Represent poses as [x, y, z, rx, ry, rz].
- Use millimeters for position and degrees for orientation.
- Support separate working and approach poses for each needle.
- Do not assume adding to Z produces a safe approach.
- Distinguish uncalibrated, provisional, and measured records.
- Never silently substitute another arm's calibration.
- Never silently substitute a neighboring needle's calibration.
- Do not treat a constant offset between arms as verified calibration.
- Leave missing measurements unset instead of inventing values.

The long-term design should support a shared needle-bed coordinate
frame, a separate transform for each arm, and optional per-needle
corrections. Do not invent transforms before reference measurements
are available.

## Calibration file changes
- Validate data before saving.
- Reject invalid needle IDs, malformed poses, and nonfinite numbers.
- Preserve unrelated calibration records when updating one entry.
- Use a versioned data format and atomic writes.
- Back up existing calibration data before replacing it.
- Never overwrite measured values with generated estimates silently.
- Preserve legacy values during migration and label estimates
  as provisional.

## Motion code
- Separate path planning from SDK execution so paths can be
  inspected and tested offline.
- Use explicit arm names instead of flags such as is_left_arm.
- Do not add full-grid hardware traversal unless requested.
- Do not assume the legacy home or park position is safe.
- Check existing SDK usage and available documentation before
  introducing or changing SDK calls.
- Do not invent API signatures or return-code meanings.
- Identify missing hardware information clearly.

## Development and verification
- Reuse existing repository conventions and dependencies.
- Avoid unrelated refactors.
- Use fake robot clients for automated tests.
- Test calibration lookup, validation, independent arm records,
  persistence, and failure handling where relevant.
- Run relevant offline checks after changes.
- Do not claim hardware behavior has been verified through
  offline tests.

## Completion report
Summarize:
- What changed and why.
- Which offline checks ran and their results.
- Any missing calibration or configuration.
- Exact commands the user can run next.
- Whether hardware behavior remains unverified.