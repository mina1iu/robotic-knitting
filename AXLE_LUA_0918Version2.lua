WRITE_ACK = 2
while(1)
do
    IwdgTaskHandle()
    MainLoop()
    UpDownLoadHandle()
    SdoRwPara()
    EndErrClear()
    local BFlag = LuaBreak()
    if(BFlag == 1) then
        break
    end

    Rcmd1, Rcmd2, Rcmd3, Rcmd4 = GetGripCmd()
    if(Rcmd1 == 1 and Rcmd2 == 1) then
        DelayMs(3)
        T = nil
        IsRead = 0
        Limit = 0
        if(Rcmd3 == 0x01) then
            T = {Rcmd2,0x06,0x01,0x05,0,1,0,0}
        elseif(Rcmd3 == 0x02) then
            T = {Rcmd2,0x06,0x01,0x00,0,1,0,0}
        elseif(Rcmd3 == 0x03) then
            if(Rcmd4 ~= nil and Rcmd4 >= 0 and Rcmd4 <= 100 and Rcmd4 % 1 == 0) then
                T = {Rcmd2,0x06,0x01,0x03,0,Rcmd4,0,0}
            end
        elseif(Rcmd3 == 0x04) then
            if(Rcmd4 ~= nil and Rcmd4 >= 0 and Rcmd4 <= 100 and Rcmd4 % 1 == 0) then
                T = {Rcmd2,0x06,0x01,0x04,0,Rcmd4,0,0}
            end
        elseif(Rcmd3 == 0x05) then
            if(Rcmd4 == 0) then
                T = {Rcmd2,0x06,0x01,0x01,0,0,0,0}
            end
        elseif(Rcmd3 == 0x07) then
            T = {Rcmd2,0x03,0x02,0x01,0,1,0,0}
            IsRead = 1
            Limit = 1
        elseif(Rcmd3 == 0x08) then
            T = {Rcmd2,0x03,0x02,0x00,0,1,0,0}
            IsRead = 1
            Limit = 1
        elseif(Rcmd3 == 0x09) then
            T = {Rcmd2,0x03,0x02,0x03,0,1,0,0}
            IsRead = 1
            Limit = 255
        elseif(Rcmd3 == 0x0A) then
            T = {Rcmd2,0x03,0x02,0x02,0,1,0,0}
            IsRead = 1
            Limit = 100
        elseif(Rcmd3 == 0x0B) then
            T = {Rcmd2,0x03,0x02,0x04,0,1,0,0}
            IsRead = 1
            Limit = 100
        elseif(Rcmd3 == 0x0C) then
            T = {Rcmd2,0x03,0x02,0x05,0,1,0,0}
            IsRead = 1
            Limit = 0
        end

        if(T ~= nil) then
            T[7],T[8] = CrcValue(T[1],T[2],T[3],T[4],T[5],T[6])
            EndTxGripData(T[1],T[2],T[3],T[4],T[5],T[6],T[7],T[8])
            DelayMs(35)
            IwdgTaskHandle()

            A,Rxd1,Rxd2,Rxd3,Rxd4,Rxd5,Rxd6,Rxd7,Rxd8 = EndRxGripData()

            if(IsRead == 0) then
                -- FC06: compare all eight echoed bytes, including CRC.
                if(Rxd1 == T[1] and Rxd2 == T[2] and
                   Rxd3 == T[3] and Rxd4 == T[4] and
                   Rxd5 == T[5] and Rxd6 == T[6] and
                   Rxd7 == T[7] and Rxd8 == T[8]) then
                    GripStateBack(WRITE_ACK)
                end
            else
                -- FC03: seven-byte reply, with exactly two data bytes.
                if(Rxd1 == Rcmd2 and Rxd2 == 0x03 and Rxd3 == 2 and
                   Rxd4 ~= nil and Rxd5 ~= nil and
                   Rxd6 ~= nil and Rxd7 ~= nil) then
                    CrcLo,CrcHi = CrcValue(Rxd1,Rxd2,Rxd3,Rxd4,Rxd5)
                    if(Rxd6 == CrcLo and Rxd7 == CrcHi) then
                        Value = Rxd4 * 256 + Rxd5
                        if(Value >= 0 and Value <= Limit) then
                            GripStateBack(Value)
                        end
                    end
                end
            end
            -- Missing, invalid or exception responses never produce success.
        end
    end
    LuaGc()
end
