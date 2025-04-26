@echo off
@chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================
echo    音频处理工具启动助手
echo ================================
echo.

:: 设置默认值
set CONFIG_FILE=config.json
set LOG_LEVEL=info
set LOG_FILE=audio-processor.log

:: 检查配置文件是否存在
if not exist "%~dp0\%CONFIG_FILE%" (
  echo 创建默认配置文件...
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
  echo 已创建默认配置文件: %CONFIG_FILE%
  echo 请根据需要修改配置文件后重新运行此脚本
  echo.
  pause
  exit /b
)

:: 确定可执行文件路径
set EXE_PATH="%~dp0\audio-processor\cmd\audioproc\audioproc.exe"
if not exist %EXE_PATH% (
  set EXE_PATH="%~dp0\audioproc.exe"
)
if not exist %EXE_PATH% (
  echo 查找可执行文件...
  for /r "%~dp0" %%i in (audioproc.exe) do (
    if exist "%%i" (
      set EXE_PATH="%%i"
      goto found_exe
    )
  )
  
  echo 错误: 找不到audioproc.exe可执行文件
  echo 请确保已编译音频处理程序，或将此批处理文件放在正确位置
  pause
  exit /b 1
  
  :found_exe
  echo 找到可执行文件: !EXE_PATH!
)

echo.
echo 使用配置文件: %CONFIG_FILE%
echo 日志级别: %LOG_LEVEL%
echo 日志文件: %LOG_FILE%
echo.
echo 正在启动音频处理器...
echo 按Ctrl+C可终止程序
echo.

:: 启动程序
%EXE_PATH% --config "%~dp0\%CONFIG_FILE%" --log-level %LOG_LEVEL% --log-file "%~dp0\%LOG_FILE%"

echo.
echo 程序已退出
pause
