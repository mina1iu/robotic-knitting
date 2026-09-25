-- 0921 adapted to the supplied DaHuan V10 request/response structure.
-- Standalone loop retained. Upload filename should start AXLE_LUA_End.
-- Experimental controller write-feedback change: validated FC06 instead of 2.
-- ESP32 MUST implement these same registers and Modbus RTU CRC.
-- This is NOT compatible with AA 03 POSITION 55 / BB 03 POSITION 66.
-- DaHuan confirms mappings 02/03/04/05/07/08/0A in the supplied file.
-- 01/09/0B/0C remain project extensions for the ESP32 register map.
local DEVICE_ID = 1
local RESPONSE_WAIT_MS = 60 -- Wait after TX; not a complete stream timeout engine.

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

    -- Match the reference sequence: TX -> wait -> RX.
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
    -- DaHuan write assignment omits A: its Rxd3 is this R[2].
    -- Under the A,byte1,byte2,... convention this is FC06 (6).
    -- Firmware acceptance must be tested; this is NOT a motion-done value.
    GripStateBack(R[2])
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

local function ReadAndFeedback(T,id,maximum)
    local value=ReadRegister(T,id,maximum)
    if value~=nil then GripStateBack(value) end -- Zero is valid.
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
            LastModbusException = 0
            -- Explicit command branches, as in DaHuan; shared helpers validate replies.
            if Rcmd3==0x01 then
                WriteRegister(T11,Rcmd2,1)
            elseif Rcmd3==0x02 then
                WriteRegister(T1,Rcmd2,1)
            elseif Rcmd3==0x03 then
                -- ESP32 uses 0..100 directly. Do NOT multiply by 10.
                if IsIntegerInRange(Rcmd4,100) then
                    WriteRegister(T2,Rcmd2,Rcmd4)
                else LastTransportError=242 end
            elseif Rcmd3==0x04 then
                if IsIntegerInRange(Rcmd4,100) then
                    WriteRegister(T3,Rcmd2,Rcmd4)
                else LastTransportError=242 end
            elseif Rcmd3==0x05 then
                if Rcmd4==0 then WriteRegister(T4,Rcmd2,0)
                else LastTransportError=242 end
            elseif Rcmd3==0x07 then
                ReadAndFeedback(T6,Rcmd2,1)
            elseif Rcmd3==0x08 then
                ReadAndFeedback(T5,Rcmd2,1)
            elseif Rcmd3==0x09 then
                ReadAndFeedback(T8,Rcmd2,255)
            elseif Rcmd3==0x0A then
                -- ESP32 returns 0..100 directly. Do NOT divide by 10.
                ReadAndFeedback(T7,Rcmd2,100)
            elseif Rcmd3==0x0B then
                ReadAndFeedback(T9,Rcmd2,100)
            elseif Rcmd3==0x0C then
                ReadAndFeedback(T10,Rcmd2,0)
            else
                LastTransportError=243
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
