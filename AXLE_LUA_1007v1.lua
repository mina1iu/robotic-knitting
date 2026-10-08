local T11 = {1,6,1,5,0,0,0,0}
local T1 = {1,6,1,0,0,0,0,0}
local T2 = {1,6,1,3,0,0,0,0}
local T3 = {1,6,1,4,0,0,0,0}
local T4 = {1,6,1,1,0,0,0,0}
local T6 = {1,3,2,1,0,1,0,0}
local T5 = {1,3,2,0,0,1,0,0}
local T8 = {1,3,2,3,0,1,0,0}
local T7 = {1,3,2,2,0,1,0,0}
local T9 = {1,3,2,4,0,1,0,0}
local T10 = {1,3,2,5,0,1,0,0}

-- DRV8214 DC motor control register 0x0106
local T12 = {2,6,1,6,0,0,0,0}

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
        DelayMs(3)

        if(Rcmd3 == 0x01) then
            T11[1] = Rcmd2
            local X = 1
            T11[6] = X%256
            T11[5] = (X-T11[6])/256
            T11[7],T11[8] = CrcValue(T11[1],T11[2],T11[3],T11[4],T11[5],T11[6])
            EndTxGripData(T11[1],T11[2],T11[3],T11[4],T11[5],T11[6],T11[7],T11[8])
            DelayMs(35)
            IwdgTaskHandle()
            local Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            GripStateBack(Rxd3)
        end

        if(Rcmd3 == 0x02) then
            T1[1] = Rcmd2
            local X = 1
            T1[6] = X%256
            T1[5] = (X-T1[6])/256
            T1[7],T1[8] = CrcValue(T1[1],T1[2],T1[3],T1[4],T1[5],T1[6])
            EndTxGripData(T1[1],T1[2],T1[3],T1[4],T1[5],T1[6],T1[7],T1[8])
            DelayMs(35)
            IwdgTaskHandle()
            local Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            GripStateBack(Rxd3)
        end

        -- MG90S: FAIRINO gripper ID 1
        if((Rcmd2 == 1) and (Rcmd3 == 0x03)) then
            T2[1] = 1
            local X = Rcmd4
            T2[6] = X%256
            T2[5] = (X-T2[6])/256
            T2[7],T2[8] = CrcValue(T2[1],T2[2],T2[3],T2[4],T2[5],T2[6])
            EndTxGripData(T2[1],T2[2],T2[3],T2[4],T2[5],T2[6],T2[7],T2[8])
            DelayMs(35)
            IwdgTaskHandle()
            local Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            GripStateBack(Rxd3)
        end

        -- DRV8214 DC motor: FAIRINO gripper ID 2
        -- Rcmd4:
        -- 0 = stop
        -- 1 = forward
        -- 2 = reverse
        if((Rcmd2 == 2) and (Rcmd3 == 0x03)) then
            T12[1] = Rcmd2
            local X = Rcmd4
            T12[6] = X%256
            T12[5] = (X-T12[6])/256
            T12[7],T12[8] = CrcValue(T12[1],T12[2],T12[3],T12[4],T12[5],T12[6])
            EndTxGripData(T12[1],T12[2],T12[3],T12[4],T12[5],T12[6],T12[7],T12[8])
            DelayMs(35)
            IwdgTaskHandle()
            local Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            GripStateBack(Rxd3)
        end

        if(Rcmd3 == 0x04) then
            T3[1] = Rcmd2
            local X = Rcmd4
            T3[6] = X%256
            T3[5] = (X-T3[6])/256
            T3[7],T3[8] = CrcValue(T3[1],T3[2],T3[3],T3[4],T3[5],T3[6])
            EndTxGripData(T3[1],T3[2],T3[3],T3[4],T3[5],T3[6],T3[7],T3[8])
            DelayMs(35)
            IwdgTaskHandle()
            local Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            GripStateBack(Rxd3)
        end

        if(Rcmd3 == 0x05) then
            T4[1] = Rcmd2
            local X = Rcmd4
            T4[6] = X%256
            T4[5] = (X-T4[6])/256
            T4[7],T4[8] = CrcValue(T4[1],T4[2],T4[3],T4[4],T4[5],T4[6])
            EndTxGripData(T4[1],T4[2],T4[3],T4[4],T4[5],T4[6],T4[7],T4[8])
            DelayMs(35)
            IwdgTaskHandle()
            local Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            GripStateBack(Rxd3)
        end

        if(Rcmd3 == 0x07) then
            T6[1] = Rcmd2
            T6[7],T6[8] = CrcValue(T6[1],T6[2],T6[3],T6[4],T6[5],T6[6])
            EndTxGripData(T6[1],T6[2],T6[3],T6[4],T6[5],T6[6],T6[7],T6[8])
            DelayMs(35)
            IwdgTaskHandle()
            local a,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            if((a == 8) and (Rxd1 == Rcmd2) and (Rxd2 == 0x03) and (Rxd3 == 0x02)) then
                GripStateBack(Rxd4*256+Rxd5)
            end
        end

        if(Rcmd3 == 0x08) then
            T5[1] = Rcmd2
            T5[7],T5[8] = CrcValue(T5[1],T5[2],T5[3],T5[4],T5[5],T5[6])
            EndTxGripData(T5[1],T5[2],T5[3],T5[4],T5[5],T5[6],T5[7],T5[8])
            DelayMs(35)
            IwdgTaskHandle()
            local a,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            if((a == 8) and (Rxd1 == Rcmd2) and (Rxd2 == 0x03) and (Rxd3 == 0x02)) then
                GripStateBack(Rxd4*256+Rxd5)
            end
        end

        if(Rcmd3 == 0x09) then
            T8[1] = Rcmd2
            T8[7],T8[8] = CrcValue(T8[1],T8[2],T8[3],T8[4],T8[5],T8[6])
            EndTxGripData(T8[1],T8[2],T8[3],T8[4],T8[5],T8[6],T8[7],T8[8])
            DelayMs(35)
            IwdgTaskHandle()
            local a,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            if((a == 8) and (Rxd1 == Rcmd2) and (Rxd2 == 0x03) and (Rxd3 == 0x02)) then
                GripStateBack(Rxd4*256+Rxd5)
            end
        end

        if(Rcmd3 == 0x0A) then
            T7[1] = Rcmd2
            T7[7],T7[8] = CrcValue(T7[1],T7[2],T7[3],T7[4],T7[5],T7[6])
            EndTxGripData(T7[1],T7[2],T7[3],T7[4],T7[5],T7[6],T7[7],T7[8])
            DelayMs(35)
            IwdgTaskHandle()
            local a,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            if((a == 8) and (Rxd1 == Rcmd2) and (Rxd2 == 0x03) and (Rxd3 == 0x02)) then
                GripStateBack(Rxd4*256+Rxd5)
            end
        end

        if(Rcmd3 == 0x0B) then
            T9[1] = Rcmd2
            T9[7],T9[8] = CrcValue(T9[1],T9[2],T9[3],T9[4],T9[5],T9[6])
            EndTxGripData(T9[1],T9[2],T9[3],T9[4],T9[5],T9[6],T9[7],T9[8])
            DelayMs(35)
            IwdgTaskHandle()
            local a,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            if((a == 8) and (Rxd1 == Rcmd2) and (Rxd2 == 0x03) and (Rxd3 == 0x02)) then
                GripStateBack(Rxd4*256+Rxd5)
            end
        end

        if(Rcmd3 == 0x0C) then
            T10[1] = Rcmd2
            T10[7],T10[8] = CrcValue(T10[1],T10[2],T10[3],T10[4],T10[5],T10[6])
            EndTxGripData(T10[1],T10[2],T10[3],T10[4],T10[5],T10[6],T10[7],T10[8])
            DelayMs(35)
            IwdgTaskHandle()
            local a,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5 = EndRxGripData()
            if((a == 8) and (Rxd1 == Rcmd2) and (Rxd2 == 0x03) and (Rxd3 == 0x02)) then
                GripStateBack(Rxd4*256+Rxd5)
            end
        end
    end

    LuaGc()
end