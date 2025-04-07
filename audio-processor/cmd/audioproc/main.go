package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/sirupsen/logrus"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/controller"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

var (
	configFile = flag.String("config", "", "配置文件路径")
	logLevel      = flag.String("log-level", "info", "日志级别 (debug, info, warn, error)")
	logFile    = flag.String("log-file", "", "日志文件路径")
)
func main() {
    // 解析命令行参数
    flag.Parse()
    
    // 创建处理器控制器
    controller, err := controller.NewProcessorController(*configFile, *logLevel, *logFile)
    if err != nil {
        fmt.Printf("初始化控制器失败: %v\n", err)
        os.Exit(1)
    }
    defer controller.Cleanup()
    
    // 打印欢迎信息
    printWelcome()
    
    // 检查依赖
    if !checkDependencies() {
        logrus.Fatal("缺少必要的依赖项，无法继续")
        os.Exit(1)
    }
    
    var results []audio.BatchResult
    
    // 根据模式执行不同的处理
    if controller.Config.WatchMode {
        if err := controller.StartWatchMode(); err != nil {
            logrus.Fatalf("监控模式运行失败: %v", err)
        }
    } else {
        results, err = controller.ProcessMedia()
        if err != nil {
            logrus.Fatalf("处理媒体文件失败: %v", err)
        }
        
        if controller.Config.ExportSRT && len(results) > 0 {
            controller.RunASRService(results)
        }
    }
    
    // 打印处理统计
    color.Green("\n所有处理任务已完成!")
}

func printWelcome() {
	// 使用彩色输出打印欢迎信息
	fmt.Println()
	color.Cyan("================================")
	color.Cyan("   音频处理工具 - Go 实现版本   ")
	color.Cyan("================================")
	fmt.Println()
}

func checkDependencies() bool {
	fmt.Print("检查系统依赖... ")

	// 检查ffmpeg
	if !utils.CheckFFmpeg() {
		color.Red("失败")
		logrus.Error("未检测到FFmpeg，请确保FFmpeg已安装并添加到系统路径")
		return false
	}

	color.Green("通过")
	return true
}
