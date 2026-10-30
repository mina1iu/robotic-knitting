from fairino import Robot

# Read-only diagnostic: no movement, gripper or IO commands.
robotyarn = None
try:
    robotyarn = Robot.RPC('192.168.0.50')
    if not getattr(robotyarn, 'is_connect', False):
        raise RuntimeError('RPC connection incomplete; aborting diagnostic')
    for name in ('GetActualTCPNum', 'GetActualWObjNum',
                 'GetActualTCPPose', 'GetCurWObjCoord', 'GetCurToolCoord'):
        try:
            print(f'{name}: {getattr(robotyarn, name)()}', flush=True)
        except Exception as exc:
            print(f'{name}: FAILED: {exc}', flush=True)
    print('Read-only diagnostic finished. No motion or motor commands sent.', flush=True)
finally:
    if robotyarn is not None:
        robotyarn.CloseRPC()