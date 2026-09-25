-- 0921 logic, expanded into the official demo's per-command style.
-- No user-defined helper functions. Retains the standalone runtime loop.
-- Position: 0..100 directly; force: zero only; write feedback: FC06 (6).
-- ACK semantics are unchanged and still require controller verification.
-- One RX call after 35 ms; no retries, stream assembly or stale-frame recovery.
local DEVICE_ID = 1
local RESPONSE_WAIT_MS = 10
LastTransportError = 0
LastModbusException = 0
LastRxMeta = nil
-- Errors: 240 invalid/missing reply, 241 exception, 242 range,
--         243 unsupported command, 244 wrong device ID.
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

while(1)
do
    IwdgTaskHandle()
    MainLoop()
    UpDownLoadHandle()
    SdoRwPara()
    EndErrClear()
    local BFlag = LuaBreak()
    if(BFlag == 1) then break end
    local Rcmd1,Rcmd2,Rcmd3,Rcmd4 = GetGripCmd()
    if(Rcmd1 == 1) then
        if(Rcmd2 ~= DEVICE_ID) then
            LastTransportError = 244
        else
            DelayMs(3)
            LastModbusException = 0
            -- Execute confirmation
            if(Rcmd3 == 0x01) then
                T11[6] = 1%256
                T11[5] = (1-T11[6])/256
                LastTransportError = 240
                LastModbusException = 0
                T11[1] = Rcmd2
                T11[7],T11[8] = CrcValue(T11[1],T11[2],T11[3],T11[4],T11[5],T11[6])
                EndTxGripData(T11[1],T11[2],T11[3],T11[4],T11[5],T11[6],T11[7],T11[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,8 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T11[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid then
                    for i=1,8 do
                        if R[i]~=T11[i] then valid = false end
                    end
                    if valid then
                        LastTransportError = 0
                        GripStateBack(Rxd2) -- FC06 (6), same as original R[2].
                    end
                end
            end
            -- Initialize
            if(Rcmd3 == 0x02) then
                T1[6] = 1%256
                T1[5] = (1-T1[6])/256
                LastTransportError = 240
                LastModbusException = 0
                T1[1] = Rcmd2
                T1[7],T1[8] = CrcValue(T1[1],T1[2],T1[3],T1[4],T1[5],T1[6])
                EndTxGripData(T1[1],T1[2],T1[3],T1[4],T1[5],T1[6],T1[7],T1[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,8 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T1[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid then
                    for i=1,8 do
                        if R[i]~=T1[i] then valid = false end
                    end
                    if valid then
                        LastTransportError = 0
                        GripStateBack(Rxd2) -- FC06 (6), same as original R[2].
                    end
                end
            end
            -- Position percent
            if(Rcmd3 == 0x03) then
                if type(Rcmd4)=="number" and Rcmd4>=0 and Rcmd4<=100 and Rcmd4%1==0 then
                T2[6] = Rcmd4%256
                T2[5] = (Rcmd4-T2[6])/256
                LastTransportError = 240
                LastModbusException = 0
                T2[1] = Rcmd2
                T2[7],T2[8] = CrcValue(T2[1],T2[2],T2[3],T2[4],T2[5],T2[6])
                EndTxGripData(T2[1],T2[2],T2[3],T2[4],T2[5],T2[6],T2[7],T2[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,8 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T2[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid then
                    for i=1,8 do
                        if R[i]~=T2[i] then valid = false end
                    end
                    if valid then
                        LastTransportError = 0
                        GripStateBack(Rxd2) -- FC06 (6), same as original R[2].
                    end
                end
                else
                    LastTransportError = 242
                end
            end
            -- Speed percent
            if(Rcmd3 == 0x04) then
                if type(Rcmd4)=="number" and Rcmd4>=0 and Rcmd4<=100 and Rcmd4%1==0 then
                T3[6] = Rcmd4%256
                T3[5] = (Rcmd4-T3[6])/256
                LastTransportError = 240
                LastModbusException = 0
                T3[1] = Rcmd2
                T3[7],T3[8] = CrcValue(T3[1],T3[2],T3[3],T3[4],T3[5],T3[6])
                EndTxGripData(T3[1],T3[2],T3[3],T3[4],T3[5],T3[6],T3[7],T3[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,8 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T3[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid then
                    for i=1,8 do
                        if R[i]~=T3[i] then valid = false end
                    end
                    if valid then
                        LastTransportError = 0
                        GripStateBack(Rxd2) -- FC06 (6), same as original R[2].
                    end
                end
                else
                    LastTransportError = 242
                end
            end
            -- Force placeholder
            if(Rcmd3 == 0x05) then
                if Rcmd4 == 0 then
                T4[6] = 0%256
                T4[5] = (0-T4[6])/256
                LastTransportError = 240
                LastModbusException = 0
                T4[1] = Rcmd2
                T4[7],T4[8] = CrcValue(T4[1],T4[2],T4[3],T4[4],T4[5],T4[6])
                EndTxGripData(T4[1],T4[2],T4[3],T4[4],T4[5],T4[6],T4[7],T4[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,8 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T4[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid then
                    for i=1,8 do
                        if R[i]~=T4[i] then valid = false end
                    end
                    if valid then
                        LastTransportError = 0
                        GripStateBack(Rxd2) -- FC06 (6), same as original R[2].
                    end
                end
                else
                    LastTransportError = 242
                end
            end
            -- Motion completion
            if(Rcmd3 == 0x07) then
                LastTransportError = 240
                LastModbusException = 0
                T6[1] = Rcmd2
                T6[7],T6[8] = CrcValue(T6[1],T6[2],T6[3],T6[4],T6[5],T6[6])
                EndTxGripData(T6[1],T6[2],T6[3],T6[4],T6[5],T6[6],T6[7],T6[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,7 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T6[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid and R[1]==Rcmd2 and R[2]==0x03 and R[3]==2 then
                    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
                    if R[6]==lo and R[7]==hi then
                        local value = Rxd4*256+Rxd5
                        if value>1 then
                            LastTransportError = 242
                        else
                            LastTransportError = 0
                            GripStateBack(value) -- Zero is valid; software feedback only.
                        end
                    end
                end
            end
            -- Initialization status
            if(Rcmd3 == 0x08) then
                LastTransportError = 240
                LastModbusException = 0
                T5[1] = Rcmd2
                T5[7],T5[8] = CrcValue(T5[1],T5[2],T5[3],T5[4],T5[5],T5[6])
                EndTxGripData(T5[1],T5[2],T5[3],T5[4],T5[5],T5[6],T5[7],T5[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,7 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T5[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid and R[1]==Rcmd2 and R[2]==0x03 and R[3]==2 then
                    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
                    if R[6]==lo and R[7]==hi then
                        local value = Rxd4*256+Rxd5
                        if value>1 then
                            LastTransportError = 242
                        else
                            LastTransportError = 0
                            GripStateBack(value) -- Zero is valid; software feedback only.
                        end
                    end
                end
            end
            -- Device error
            if(Rcmd3 == 0x09) then
                LastTransportError = 240
                LastModbusException = 0
                T8[1] = Rcmd2
                T8[7],T8[8] = CrcValue(T8[1],T8[2],T8[3],T8[4],T8[5],T8[6])
                EndTxGripData(T8[1],T8[2],T8[3],T8[4],T8[5],T8[6],T8[7],T8[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,7 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T8[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid and R[1]==Rcmd2 and R[2]==0x03 and R[3]==2 then
                    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
                    if R[6]==lo and R[7]==hi then
                        local value = Rxd4*256+Rxd5
                        if value>255 then
                            LastTransportError = 242
                        else
                            LastTransportError = 0
                            GripStateBack(value) -- Zero is valid; software feedback only.
                        end
                    end
                end
            end
            -- Commanded position percent
            if(Rcmd3 == 0x0A) then
                LastTransportError = 240
                LastModbusException = 0
                T7[1] = Rcmd2
                T7[7],T7[8] = CrcValue(T7[1],T7[2],T7[3],T7[4],T7[5],T7[6])
                EndTxGripData(T7[1],T7[2],T7[3],T7[4],T7[5],T7[6],T7[7],T7[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,7 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T7[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid and R[1]==Rcmd2 and R[2]==0x03 and R[3]==2 then
                    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
                    if R[6]==lo and R[7]==hi then
                        local value = Rxd4*256+Rxd5
                        if value>100 then
                            LastTransportError = 242
                        else
                            LastTransportError = 0
                            GripStateBack(value) -- Zero is valid; software feedback only.
                        end
                    end
                end
            end
            -- Speed percent
            if(Rcmd3 == 0x0B) then
                LastTransportError = 240
                LastModbusException = 0
                T9[1] = Rcmd2
                T9[7],T9[8] = CrcValue(T9[1],T9[2],T9[3],T9[4],T9[5],T9[6])
                EndTxGripData(T9[1],T9[2],T9[3],T9[4],T9[5],T9[6],T9[7],T9[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,7 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T9[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid and R[1]==Rcmd2 and R[2]==0x03 and R[3]==2 then
                    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
                    if R[6]==lo and R[7]==hi then
                        local value = Rxd4*256+Rxd5
                        if value>100 then
                            LastTransportError = 242
                        else
                            LastTransportError = 0
                            GripStateBack(value) -- Zero is valid; software feedback only.
                        end
                    end
                end
            end
            -- Force placeholder
            if(Rcmd3 == 0x0C) then
                LastTransportError = 240
                LastModbusException = 0
                T10[1] = Rcmd2
                T10[7],T10[8] = CrcValue(T10[1],T10[2],T10[3],T10[4],T10[5],T10[6])
                EndTxGripData(T10[1],T10[2],T10[3],T10[4],T10[5],T10[6],T10[7],T10[8])
                DelayMs(RESPONSE_WAIT_MS)
                IwdgTaskHandle()
                local A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()
                LastRxMeta = A
                local R = {Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8}
                local valid5,valid = true,true
                for i=1,7 do
                    if type(R[i])~="number" or R[i]<0 or R[i]>255 or R[i]%1~=0 then
                        valid = false
                        if i<=5 then valid5 = false end
                    end
                end
                if valid5 and R[1]==Rcmd2 and R[2]==T10[2]+0x80 then
                    local lo,hi = CrcValue(R[1],R[2],R[3])
                    if R[4]==lo and R[5]==hi then
                        LastTransportError = 241
                        LastModbusException = R[3]
                    end
                elseif valid and R[1]==Rcmd2 and R[2]==0x03 and R[3]==2 then
                    local lo,hi = CrcValue(R[1],R[2],R[3],R[4],R[5])
                    if R[6]==lo and R[7]==hi then
                        local value = Rxd4*256+Rxd5
                        if value>0 then
                            LastTransportError = 242
                        else
                            LastTransportError = 0
                            GripStateBack(value) -- Zero is valid; software feedback only.
                        end
                    end
                end
            end
            if Rcmd3~=0x01 and Rcmd3~=0x02 and Rcmd3~=0x03 and Rcmd3~=0x04
               and Rcmd3~=0x05 and Rcmd3~=0x07 and Rcmd3~=0x08 and Rcmd3~=0x09
               and Rcmd3~=0x0A and Rcmd3~=0x0B and Rcmd3~=0x0C then
                LastTransportError = 243
            end
        end
    end
    LuaGc()
end
-- FC03 replies carry no register address. Late replies remain ambiguous.
-- MG90S position/completion here are commanded/estimated, not measured.
