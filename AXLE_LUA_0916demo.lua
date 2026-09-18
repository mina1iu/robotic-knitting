-- while(1)
-- do

--     IwdgTaskHandle()
--     MainLoop()
--     UpDownLoadHandle()
--     SdoRwPara()
--     EndErrClear()

--     local BFlag = LuaBreak()

--     if(BFlag == 1) then
--         break
--     end


--     -- Get command from FAIRINO controller
--     Rcmd1, Rcmd2, Rcmd3, Rcmd4 = GetGripCmd()


--     -- New command received
--     if(Rcmd1 == 1) then

--         DelayMs(3)


--         -- ========================================
--         -- POSITION CONTROL
--         -- Rcmd3 = 0x03
--         -- ========================================

--         if(Rcmd3 == 0x03) then

--             -- Send:
--             --
--             -- AA 03 [POSITION] 55
--             --
--             -- Example:
--             -- position = 50
--             -- AA 03 32 55

--             EndTxGripData(
--                 0xAA,
--                 0x03,
--                 Rcmd4,
--                 0x55
--             )

--         end

--     end


--     LuaGc()

-- end

-- THIS DEMO CAN WORK ONE TIME AND THEN TIMEOUT

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


    if(Rcmd1 == 1) then

        DelayMs(3)

        -- ========================================
        -- POSITION COMMAND
        -- ========================================

        if(Rcmd3 == 0x03) then

            -- Send:
            -- AA 03 POSITION 55

            EndTxGripData(
                0xAA,
                0x03,
                Rcmd4,
                0x55
            )


            -- Give ESP32 time to reply
            DelayMs(10)


            -- Receive:
            -- BB 03 POSITION 66

            A,
            Rxd1,
            Rxd2,
            Rxd3,
            Rxd4,
            Rxd5,
            Rxd6,
            Rxd7 = EndRxGripData()


            -- For our test:
            --
            -- Rxd1 = BB
            -- Rxd2 = 03
            -- Rxd3 = POSITION
            -- Rxd4 = 66
            --
            -- Return position/state to controller

            if(
                Rxd1 == 0xBB and
                Rxd2 == 0x03 and
                Rxd4 == 0x66
            ) then

                GripStateBack(Rxd3)

            end

        end

    end


    LuaGc()

end