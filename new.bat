@echo off
setlocal enabledelayedexpansion

rem 定义需要创建文件的路径数组
set "filePaths[0]=audio-processor/cmd/processor/main.go"
set "filePaths[1]=audio-processor/internal/audio/splitter.go"
set "filePaths[2]=audio-processor/internal/audio/extractor.go"
set "filePaths[3]=audio-processor/internal/asr/manager.go"
set "filePaths[4]=audio-processor/internal/asr/service.go"
set "filePaths[5]=audio-processor/internal/asr/google.go"
set "filePaths[6]=audio-processor/internal/asr/bcut.go"
set "filePaths[7]=audio-processor/internal/asr/jianying.go"
set "filePaths[8]=audio-processor/internal/asr/kuaishou.go"
set "filePaths[9]=audio-processor/internal/text/processor.go"
set "filePaths[10]=audio-processor/internal/text/formatter.go"
set "filePaths[11]=audio-processor/internal/subtitle/srt.go"
set "filePaths[12]=audio-processor/internal/progress/bar.go"
set "filePaths[13]=audio-processor/internal/watcher/monitor.go"
set "filePaths[14]=audio-processor/internal/controller/processor.go"
set "filePaths[15]=audio-processor/pkg/utils/file.go"
set "filePaths[16]=audio-processor/pkg/utils/time.go"
set "filePaths[17]=audio-processor/pkg/utils/ffmpeg.go"
set "filePaths[18]=audio-processor/pkg/models/config.go"
set "filePaths[19]=audio-processor/pkg/models/result.go"

rem 遍历路径数组，创建文件
for /L %%i in (0,1,19) do (
    set "path=!filePaths[%%i]!"
    rem 提取目录路径
    for %%p in ("!path!") do set "directory=%%~dp"
    rem 如果目录不存在，则创建目录
    if not exist "!directory!" (
        mkdir "!directory!"
    )
    rem 创建文件
    type nul > "!path!"
    echo 创建文件: !path!
)

endlocal