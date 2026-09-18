-- Keep end-effector system running normally
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

    -- =====================================
    -- 1. Python / Robot -> ESP32
    -- =====================================
    local RxFlag = GetHostTransparentCmd(Tcmd)

    if(RxFlag == 1) then
        EndTxCustomData(Tcmd)
    end

    -- =====================================
    -- 2. ESP32 -> Robot / Python
    -- =====================================
    EndRxCustomData(Rcmd)

    if(#Rcmd > 0) then
        BackHostTransparentCmd(Rcmd)
    end

    DelayMs(10)
    LuaGc()
end