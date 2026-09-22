-- FAIRINO end-gripper Lua: corrected Modbus single-register adapter.
-- ESP32 MUST implement these same registers and Modbus RTU CRC.
-- This is NOT compatible with AA 03 POSITION 55 / BB 03 POSITION 66.
-- Command mappings 01/07/08/09 and WRITE_ACK=2 are retained project
-- assumptions, NOT established by the supplied official demo.
local DEVICE_ID = 1
local WRITE_ACK = 2 -- Verify with the controller's gripper API documentation.
local RESPONSE_WAIT_MS = 35 -- Wait after TX; not a complete stream timeout engine.

-- Local diagnostics only; these are not automatically reported to WebApp.
LastTransportError = 0 -- 240 invalid/missing reply, 241 exception, 242 range,
                       -- 243 unsupported command, 244 wrong device ID.
LastModbusException = 0
LastRxMeta = nil -- EndRxGripData first return: meaning not assumed.

-- 8 BYTES per request. CRC occupies indices 7 and 8 (low, high).
local T1  = {1,0x06,0x01,0x00,0,1,0,0} -- write initialize
local T2  = {1,0x06,0x01,0x03,0,0,0,0} -- write position percent
local T3  = {1,0x06,0x01,0x04,0,0,0,0} -- write speed percent
local T4  = {1,0x06,0x01,0x01,0,0,0,0} -- write force placeholder: zero only
local T5  = {1,0x03,0x02,0x00,0,1,0,0} -- read initialized
local T6  = {1,0x03,0x02,0x01,0,1,0,0} -- read completion
local T7  = {1,0x03,0x02,0x02,0,1,0,0} -- read commanded position
local T8  = {1,0x03,0x02,0x03,0,1,0,0} -- read device error
local T9  = {1,0x03,0x02,0x04,0,1,0,0} -- read speed
local T10 = {1,0x03,0x02,0x05,0,1,0,0} -- read force placeholder
local T11 = {1,0x06,0x01,0x05,0,1,0,0} -- write execute/confirm; no restart

local function IsIntegerInRange(value, maximum)
    return type(value)=="number" and value>=0 and value<=maximum
           and value%1==0
end

local function HasBytes(r, n)
    for i=1,n do
        if not IsIntegerInRange(r[i],255) then return false end
    end
    return true
end

local function SendAndReceive(T, id)
    LastTransportError = 240
    LastModbusException = 0
    T[1] = id
    T[7],T[8] = CrcValue(T[1],T[2],T[3],T[4],T[5],T[6])

    -- Match the proven sequence: TX -> wait -> RX.
    -- Do NOT perform an undocumented pre-send receive/flush.
    EndTxGripData(T[1],T[2],T[3],T[4],T[5],T[6],T[7],T[8])
    DelayMs(RESPONSE_WAIT_MS)
    IwdgTaskHandle()
    local A,b1,b2,b3,b4,b5,b6,b7,b8 = EndRxGripData()
    LastRxMeta = A
    local R = {b1,b2,b3,b4,b5,b6,b7,b8}

    -- FC 03/06 exception: ID, FC+0x80, exception, CRC_L, CRC_H.
    if HasBytes(R,5) and R[1]==id and R[2]==T[2]+0x80 then
        local lo,hi = CrcValue(R[1],R[2],R[3])
        if R[4]==lo and R[5]==hi then
            LastTransportError = 241
            LastModbusException = R[3]
        end
        return nil
    end
    return R
end

local function WriteRegister(T, id, value)
    if not IsIntegerInRange(value,65535) then
        LastTransportError = 242
        return false
    end
    -- Split a 16-BIT value into high and low BYTES without bitwise syntax.
    T[6] = value%256
    T[5] = (value-T[6])/256
    local R = SendAndReceive(T,id)
    if R==nil or not HasBytes(R,8) then return false end
    -- FC06 response echoes the complete request, including its CRC.
    for i=1,8 do
        if R[i]~=T[i] then return false end
    end
    LastTransportError = 0
    return true
end

local function ReadRegister(T, id, maxValue)
    local R = SendAndReceive(T,id)
    if R==nil or not HasBytes(R,7) then return nil end
    if R[1]~=id or R[2]~=0x03 or R[3]~=2 then return nil end
    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
    if R[6]~=lo or R[7]~=hi then return nil end
    local value = R[4]*256+R[5] -- Combine two bytes into a 16-bit value.
    if value>maxValue then
        LastTransportError = 242
        return nil
    end
    LastTransportError = 0
    return value -- Actual ESP32 response; maxValue is only a range check.
end

while(1)
do
    IwdgTaskHandle()
    MainLoop()
    UpDownLoadHandle()
    SdoRwPara()
    EndErrClear()
    local BFlag = LuaBreak()
    if BFlag==1 then break end

    local Rcmd1,Rcmd2,Rcmd3,Rcmd4 = GetGripCmd()
    if Rcmd1==1 then
        if Rcmd2~=DEVICE_ID then
            LastTransportError = 244 -- Unicast only; no broadcast response.
        else
            DelayMs(3)
            local request = nil
            local writeValue = nil
            local maxValue = nil
            LastModbusException = 0

            if Rcmd3==0x01 then
                request=T11; writeValue=1
            elseif Rcmd3==0x02 then
                request=T1; writeValue=1
            elseif Rcmd3==0x03 then
                if IsIntegerInRange(Rcmd4,100) then
                    request=T2; writeValue=Rcmd4
                else LastTransportError=242 end
            elseif Rcmd3==0x04 then
                if IsIntegerInRange(Rcmd4,100) then
                    request=T3; writeValue=Rcmd4
                else LastTransportError=242 end
            elseif Rcmd3==0x05 then
                if Rcmd4==0 then
                    request=T4; writeValue=0
                else LastTransportError=242 end
            elseif Rcmd3==0x07 then
                request=T6; maxValue=1
            elseif Rcmd3==0x08 then
                request=T5; maxValue=1
            elseif Rcmd3==0x09 then
                request=T8; maxValue=255
            elseif Rcmd3==0x0A then
                request=T7; maxValue=100
            elseif Rcmd3==0x0B then
                request=T9; maxValue=100
            elseif Rcmd3==0x0C then
                request=T10; maxValue=0
            else
                LastTransportError=243
            end

            if request~=nil then
                if writeValue~=nil then
                    if WriteRegister(request,Rcmd2,writeValue) then
                        -- Retained project ACK convention, not motion completion.
                        GripStateBack(WRITE_ACK)
                    end
                else
                    local value = ReadRegister(request,Rcmd2,maxValue)
                    if value~=nil then
                        GripStateBack(value) -- Zero is a valid response too.
                    end
                end
            end
        end
    end
    LuaGc()
end

-- Transport limitations:
-- A single EndRxGripData must return a complete frame. No partial-frame
-- accumulation, verified byte count, stale-frame recovery or retries here.
-- FC03 replies contain no register address: delayed replies to different
-- queries cannot be distinguished from bytes alone. Resynchronize the
-- receive path after a timeout once the vendor RX API semantics are known.
-- Standard MG90S reports commanded position / estimated completion only.
