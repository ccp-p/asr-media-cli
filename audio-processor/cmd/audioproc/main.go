package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"time"

	"github.com/fatih/color"
	"github.com/sirupsen/logrus"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/internal/watcher"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

var (
	mediaDir      = flag.String("media", "D:/download/", "媒体文件目录")
	outputDir     = flag.String("output", "D:/download/dest", "输出目录")
	configFile    = flag.String("config", "", "配置文件路径")
	logLevel      = flag.String("log-level", "info", "日志级别 (debug, info, warn, error)")
	logFile       = flag.String("log-file", "", "日志文件路径")
	noProgressBar = flag.Bool("no-progress", false, "禁用进度条")
	config        = models.NewDefaultConfig() // 配置对象
)

// 创建全局进度管理器
var progressManager *ui.ProgressManager

// 进度回调函数
func batchProgressCallback(current, total int, filename string, result *audio.BatchResult) {
	if result == nil {
		fmt.Printf("\n[%d/%d] 开始处理: %s\n", current, total, filename)
	} else {
		if result.Success {
			color.Green("\n[%d/%d] 处理成功: %s", current, total, filename)
			fmt.Printf("输出文件: %s\n", result.OutputPath)
			fmt.Printf("处理用时: %s\n", utils.FormatTimeDuration(result.ProcessTime.Seconds()))
		} else {
			color.Red("\n[%d/%d] 处理失败: %s - %v", current, total, filename, result.Error)
		}
	}
}

func processMedia() {
	// 创建临时目录
	tempDir, err := ioutil.TempDir("", "audio-processor")
	if err != nil {
		logrus.Fatalf("创建临时目录失败: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// 创建批处理器
	processor := audio.NewBatchProcessor(*mediaDir, *outputDir, tempDir, batchProgressCallback, config)
	processor.MaxConcurrency = 4 // 设置最大并发数

	// 设置进度管理器
	if progressManager != nil {
		processor.SetProgressManager(progressManager)
	}

	// 启动片段监控
	var stopMonitoring func()
	if progressManager != nil {
		progressManager.CreateProgressBar("segments_monitor", 100, "片段监控", "等待处理开始...")
		stopMonitoring = watcher.StartSegmentMonitoring(tempDir, progressManager)
		defer stopMonitoring() // 确保在函数结束时停止监控
	}

	// 处理所有文件
	startTime := time.Now()
	results, err := processor.ProcessVideoFiles()
	if err != nil {
		logrus.Fatalf("处理文件失败: %v", err)
	}

	// 停止片段监控
	if stopMonitoring != nil {
		stopMonitoring()
	}

	// 统计结果
	successCount := 0
	for _, result := range results {
		if result.Success {
			successCount++
		}
	}

	totalTime := time.Since(startTime)

	// 打印总结
	fmt.Println("\n处理完成!")
	fmt.Printf("总文件数: %d, 成功: %d, 失败: %d\n", len(results), successCount, len(results)-successCount)
	fmt.Printf("总耗时: %s\n", utils.FormatTimeDuration(totalTime.Seconds()))

	// 如果有失败的文件，打印它们
	if len(results) > successCount {
		fmt.Println("\n失败的文件:")
		for _, result := range results {
			if !result.Success {
				fmt.Printf("- %s: %v\n", filepath.Base(result.FilePath), result.Error)
			}
		}
	}
}

func main() {
	// 解析命令行参数
	flag.Parse()

	// 初始化日志
	utils.InitLogger(*logLevel, *logFile)

	// 初始化进度管理器
	progressManager = ui.NewProgressManager(!*noProgressBar)

	// 打印欢迎信息
	printWelcome()

	// 加载配置
	config = loadConfig()

	// 检查ffmpeg是否可用
	if !checkDependencies() {
		logrus.Fatal("缺少必要的依赖项，无法继续")
		os.Exit(1)
	}

	// 处理媒体文件
	processMedia()

	// 处理完成后，清理所有进度条
	if progressManager != nil {
		progressManager.CloseAll("已完成")
	}

	// 打印处理完成消息
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

func loadConfig() *models.Config {
	fmt.Print("加载配置... ")

	config := models.NewDefaultConfig()

	// 如果指定了配置文件，尝试加载
	if *configFile != "" {
		err := config.LoadFromFile(*configFile)
		if err != nil {
			color.Yellow("警告: 加载配置文件失败: %v", err)
			logrus.Warnf("配置加载失败: %v，将使用默认配置", err)
		} else {
			color.Green("成功")
		}
	} else {
		color.Yellow("未指定配置文件，使用默认配置")
	}

	// 覆盖配置中的目录设置
	if *mediaDir != "./media" {
		config.MediaFolder = *mediaDir
	}

	if *outputDir != "./output" {
		config.OutputFolder = *outputDir
	}

	// 确保目录存在
	os.MkdirAll(config.MediaFolder, 0755)
	os.MkdirAll(config.OutputFolder, 0755)

	return config
}
