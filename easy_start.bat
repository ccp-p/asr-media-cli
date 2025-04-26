@echo off
@chcp 65001 >nul
setlocal enabledelayedexpansion
title 音频处理工具启动助手

:: 设置颜色
set ESC=
set BLUE=%ESC%[36m
set GREEN=%ESC%[32m
set RED=%ESC%[31m
set YELLOW=%ESC%[33m
set RESET=%ESC%[0m

echo %BLUE%================================%RESET%
echo %BLUE%    音频处理工具启动助手 v1.0    %RESET%
echo %BLUE%================================%RESET%
echo.

:: 设置默认值
set CONFIG_FILE=config.json
set LOG_LEVEL=info
set LOG_FILE=audio-processor.log

:: 检查配置文件是否存在
if not exist "%~dp0\%CONFIG_FILE%" (
  echo %YELLOW%配置文件不存在，创建默认配置...%RESET%
  echo {> "%~dp0\%CONFIG_FILE%"
  echo   "MediaFolder": "D:\\download",>> "%~dp0\%CONFIG_FILE%"
  echo   "OutputFolder": "D:\\download\\dest",>> "%~dp0\%CONFIG_FILE%"
  echo   "TempDir": "D:\\temp",>> "%~dp0\%CONFIG_FILE%"
  echo   "WatchMode": true,>> "%~dp0\%CONFIG_FILE%"
  echo   "ExportSRT": true,>> "%~dp0\%CONFIG_FILE%"
  echo   "ExportJSON": true,>> "%~dp0\%CONFIG_FILE%"
  echo   "FormatText": true,>> "%~dp0\%CONFIG_FILE%"
  echo   "IncludeTimestamps": true,>> "%~dp0\%CONFIG_FILE%"
  echo   "ASRService": "auto",>> "%~dp0\%CONFIG_FILE%"
  echo   "MaxWorkers": 2>> "%~dp0\%CONFIG_FILE%"
  echo }>> "%~dp0\%CONFIG_FILE%"
  echo %GREEN%已创建默认配置文件: %CONFIG_FILE%%RESET%
  echo 您可以根据需要编辑该文件设置默认路径和选项
  echo.
)

:: 确定可执行文件路径
set EXE_PATH="%~dp0\audio-processor\cmd\audioproc\audioproc.exe"
if not exist %EXE_PATH% (
  set EXE_PATH="%~dp0\audioproc.exe"
)
if not exist %EXE_PATH% (
  echo %YELLOW%查找可执行文件...%RESET%
  for /r "%~dp0" %%i in (audioproc.exe) do (
    if exist "%%i" (
      set EXE_PATH="%%i"
      goto found_exe
    )
  )
  
  echo %RED%错误: 找不到audioproc.exe可执行文件%RESET%
  echo 请确保已编译音频处理程序，或将此批处理文件放在正确位置
  pause
  exit /b 1
  
  :found_exe
  echo %GREEN%找到可执行文件: !EXE_PATH!%RESET%
)

:: 显示菜单
:menu
cls
echo %BLUE%================================%RESET%
echo %BLUE%    音频处理工具启动助手 v1.0    %RESET%
echo %BLUE%================================%RESET%
echo.
echo  [1] 启动文件监控模式 (自动处理新增文件)
echo  [2] 处理单个文件 
echo  [3] 编辑配置文件
echo  [4] 查看使用帮助
echo  [5] 退出
echo.
echo %YELLOW%请选择操作 (1-5):%RESET%

choice /c 12345 /n
set choice=%errorlevel%

if %choice%==1 goto watch_mode
if %choice%==2 goto process_single
if %choice%==3 goto edit_config
if %choice%==4 goto show_help
if %choice%==5 goto end

:watch_mode
echo.
echo %YELLOW%启动监控模式...%RESET%
echo 将自动处理添加到以下目录的媒体文件:
type "%~dp0\%CONFIG_FILE%" | findstr "MediaFolder"
echo.
echo 按Ctrl+C结束程序
echo.
%EXE_PATH% --config "%~dp0\%CONFIG_FILE%" --log-level %LOG_LEVEL% --log-file "%~dp0\%LOG_FILE%"
echo.
echo %GREEN%程序已退出%RESET%
pause
goto menu

:process_single
echo.
echo %YELLOW%处理单个文件%RESET%
echo 请将媒体文件拖放到此窗口:
set /p file=
if "%file%"=="" goto menu
echo.
echo %YELLOW%开始处理文件: %file%%RESET%
echo.

:: 临时修改配置
copy "%~dp0\%CONFIG_FILE%" "%~dp0\%CONFIG_FILE%.bak" >nul
type "%~dp0\%CONFIG_FILE%.bak" | findstr /v "WatchMode" > "%~dp0\temp_config.json"
echo   "WatchMode": false,>> "%~dp0\temp_config.json"
move /y "%~dp0\temp_config.json" "%~dp0\%CONFIG_FILE%" >nul

:: 处理文件
%EXE_PATH% --config "%~dp0\%CONFIG_FILE%" --log-level %LOG_LEVEL% --log-file "%~dp0\%LOG_FILE%"

:: 恢复配置
move /y "%~dp0\%CONFIG_FILE%.bak" "%~dp0\%CONFIG_FILE%" >nul

echo.
echo %GREEN%处理完成%RESET%
pause
goto menu

:edit_config
echo.
echo %YELLOW%正在打开配置文件...%RESET%
start notepad "%~dp0\%CONFIG_FILE%"
timeout /t 1 >nul
goto menu

:show_help
echo.
echo %BLUE%=== 使用帮助 ===%RESET%
echo.
echo %YELLOW%1. 监控模式:%RESET%
echo    自动监控指定目录中新增的媒体文件并进行处理
echo    适合持续添加多个文件的场景
echo.
echo %YELLOW%2. 单文件处理:%RESET%
echo    选择并处理单个音频或视频文件
echo.
echo %YELLOW%3. 配置文件设置:%RESET%
echo    MediaFolder: 监控的媒体文件夹
echo    OutputFolder: 处理结果输出文件夹
echo    ExportSRT: 是否导出SRT字幕文件
echo    ASRService: 使用的ASR服务 (auto, kuaishou, bcut)
echo.
echo %GREEN%按任意键返回主菜单%RESET%
pause >nul
goto menu

:end
echo.
echo %BLUE%感谢使用音频处理工具!%RESET%
echo.
timeout /t 2 >nul
