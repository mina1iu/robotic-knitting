local DEVICE_ID = 1
local WRITE_ACK = 2
-- local seq = 0
local RESPONSE_WAIT_MS = 35
local lastTransportError = 0

-- -- make sure the message is correct when senting to esp32 by using crc16 function, use XOR logic to compare each bits 

-- IMOPRTANT!!
-- this template is from official sample, we use this as reference to set up the template:

-- the following table hode the rcmd3 data ! 
-- rcmd3 = 0x02 -> initialization
-- rcmd3 = 0x03 -> position control
-- rcmd3 = 0x04 -> speed control
-- rcmd3 = 0x05 -> force control
-- rcmd3 = 0x08 -> position query
-- rcmd3 = 0x0A -> query position 
-- rcmd3 = 0x0B -> query speed 
-- rcmd3 = 0x0C -> query force 

-- this data structure will hold some template values that will be passed to gripper.
-- data structure example ! T1 = {0x01,0x06,0x01,0x00,0x00,0x01,0x49,0xF6}
--  {0x01 - slave address of your gripper or gripper ID
--  0x06  - function code for initialization from the gripper manual 
--  0x01  0x00 register address for the function command
--  0x00  0x01 the value of the command 
--  0x049, 0xF6 crc value will be update later !  }

-- 8 bits Action template for our gripper command, t[6] and t[7] will re-calculate using crc when sending
-- Modbus define 0x06 as write single register, 0x03 as read holding register, 0x08 is diagnotics
-- T[1]: the slave id
-- T[2]: read or write register for the function cmd
-- T[3]and T[4]: combine as one single register adress, t[3] is high byte, t[4] is low byte.
-- T[5]and T[6]: update value for the command
-- T[7]and T[8]: crc

-- write funtion template
local T1 = {1, 0x06, 0x01, 0x00, 0, 1, 0, 0} -- input initialization
local T2 = {1, 0x06, 0x01, 0x03, 0, 0, 0, 0} -- input position
local T3 = {1, 0x06, 0x01, 0x04, 0, 0, 0, 0} -- input speed
local T4 = {1, 0x06, 0x01, 0x01, 0, 0, 0, 0} -- input force
local T5 = {1, 0x03, 0x02, 0x00, 0, 1, 0, 0} -- check initialization status
local T6 = {1, 0x03, 0x02, 0x01, 0, 1, 0, 0} -- check movement status
local T7 = {1, 0x03, 0x02, 0x02, 0, 1, 0, 0} -- check demand location
local T8 = {1, 0x03, 0x02, 0x03, 0, 1, 0, 0} -- check error
local T9 = {1, 0x03, 0x02, 0x04, 0, 1, 0, 0} -- check speed
local T10 = {1, 0x03, 0x02, 0x05, 0, 1, 0, 0} -- check force
local T11 = {1, 0x06, 0x01, 0x05, 0, 1, 0, 0} -- comfirm to excute


-- check return value indeed includes n legal bytes.
local function HasBytes(r,n)
    for i =1, n do 
        if type(r[i]) ~= "number" or r[i]<0 or r[i]>255 or r[i]%1~=0 then
            return false
        end
    end
    return true
end


-- send and receive action, actual action depends on T1..11 and branch below
local function SendAndReceive(T, id)
    T[1] = id
    T[7], T[8] = CrcValue(T[1], T[2], T[3], T[4], T[5], T[6])
    -- as the receive funtion will consume storage, throw away the last result
    EndRxGripData()
    EndTxGripData(T[1], T[2], T[3], T[4], T[5], T[6], T[7], T[8])
    DelayMs(RESPONSE_WAIT_MS)
    IwdgTaskHandle()
    local A, b1, b2, b3, b4, b5, b6, b7, b8 = EndRXGripData()
    local R = {b1, b2, b3, b4, b5, b6, b7, b8}
    lastTransportError = 240
    -- no valid response
    -- if Modbus abnormal, feedback 5 bytes answer: ID, FC|0x80, error code, CRC_L, CRC_H
    if HasBytes(R,5) and R[1] == id and R[2] == (T[2]|0x80) then
        local lo,hi = CrcValue(R[1], R[2], R[3])
        if R[4] == lo and R[5] == hi then
            lastTransportError = 241
        end
        return nil
    end
    return R
end


-- write register: must be 8 bytes so that can comfirm write succussefully
local function WriteRegister(T, id, value)
    T[5] = (value>>8) & 0xFF
    T[6] = value & 0xFF
    local R = SendAndReceive(T, id)
    if R==nil or not HasBytes(R, 8) then return end
    for i =1, 8 do
        if R[i] ~= T[i] then return end
    end
   lastTransportError = 0
   GripStateBack(WRITE_ACK) -- only comfirm when write succeed
end

-- read register: check address, function code, length of data, CRC, combine as 16 bytes
local function ReadRegister(T, id, maxValue)
    local R = SendAndReceive(T, id)
    if R==nil or not HasBytes(R, 7) then return end
    if R[1]~=id or R[2]~=0x03 or R[3]~=2 then return end
    local lo,hi = CrcValue(R[1], R[2], R[3], R[4], R[5])
    if R[6]~=lo or R[7]~=hi then return end
    local value = (R[4] << 8) | R[5]
    if value>maxValue then
        lastTransportError = 242
        return
    end
    lastTransportError = 0
    GripStateBack(value) -- the meaning of this value depends on which info we are cheking
end

-- check the value it send over is validate
local function ValidPercent(value)
    return type(value)=="number" and value>=0 and value<=100 and value%1==0
end


While true do
    --based on official demo
    IwdgTaskHome()
    MainLoop()
    UpDownLoadHandle()
    SdoRwPara()
    EndErrClear()
    if LuaBreak()==1 then break end

    local Rcmd1, Rcmd2, Rcmd3, Rcmd4 = GetGripCmd()

    if Rcmd1==1 and Rcmd2==DEVICE_ID then

        if Rcmd3==0x01 then
            -- excute comfirmed, will not restart the device when it already working
            WriteRegister(T11, Rcmd2, 1)

        elseif Rcmd3==0x02 then
            --initialization
            WriteRegister(T1, Rcmd2, 1)

        elseif Rcmd3==0x03 then
            --set position to 0-100, the rotate percent is defined at ESP32
            if ValidPercent(Rcmd4) then
                WriteRegister(T2, Rcmd2, Rcmd4)
            else lastTransportError = 242 end

        elseif Rcmd3==0x04 then
            -- set speed to 0-100, the meaning is defined by esp32
            if ValidPercent(Rcmd4) then
                WriteRegister(T3, Rcmd2, Rcmd4)
            else lastTransportError = 242 end

        elseif Rcmd3==0x05 then
            -- MG90s do not have force control, but maybe change afterwards. Python MoveGripper's Force should set to 0 in this case
            -- will refuse the value apart from 0
            if Rcmd4==0 then WriteRegister(T4, Rcmd2, 0)
            else lastTransportError = 242 end

        elseif Rcmd3==0x07 then
            -- check the movement status, finished-1, no-finish-0
            ReadRegister(T6, Rcmd2, 1)

        elseif Rcmd3==0x08 then
            -- check the initialization status, ready-1, no-ready-0
            ReadRegister(T5, Rcmd2, 1)

        elseif Rcmd3==0x09 then
            -- check esp32 error code, not error code here
            ReadRegister(T8, Rcmd2, 255)

        elseif Rcmd3==0x0A then
            -- check the position from current output command 0-100
            ReadRegister(T7, Rcmd2, 100)

        elseif Rcmd3==0x0B then
            -- check the speed 
            ReadRegister(T9, Rcmd2, 100)

        elseif Rcmd==0x0C then
            -- check force, but now the case is alwas 0
            ReadRegister(T10, Rcmd2, 0)
        end
    end

    -- when there is an receive and send error, or the parameters error, controller may report timesout.
    LuaGc()
end



        




        


