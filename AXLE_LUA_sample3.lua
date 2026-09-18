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

    local Tcmd = {}
    local Rcmd = {}

    -- Python/controller -> ESP32
    local RxFlag = GetHostTransparentCmd(Tcmd)

    if(RxFlag == 1) then
        EndTxCustomData(Tcmd)
    end

    -- ESP32 -> Robot/controller
    EndRxCustomData(Rcmd)

    if(#Rcmd > 0) then
        BackHostTransparentCmd(Rcmd)
    end

    DelayMs(10)
    LuaGc()
end