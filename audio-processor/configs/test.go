package main

import (
	"context"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/fatih/color"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/adapters"
	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/internal/watcher"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/asr"
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

func processMedia() []audio.BatchResult {
	// 创建临时目录
	tempDir, err := ioutil.TempDir("", "audio-processor")
	if err != nil {
		utils.Fatal("创建临时目录失败: %v", err)
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
		utils.Fatal("处理文件失败: %v", err)
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
	return results
}

// startWatchMode 启动监听模式，同时监控下载目录和媒体目录
func startWatchMode(config *models.Config) {
	// 确保目录存在
	downloadDir := config.OutputFolder // 下载目录，通常是输出目录
	mediaDir := config.MediaFolder     // 媒体目录

	os.MkdirAll(downloadDir, 0755)
	os.MkdirAll(mediaDir, 0755)

	// 创建临时目录
	tempDir, err := ioutil.TempDir("", "audio-processor-watch")
	if err != nil {
		utils.Fatal("创建临时目录失败: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// 创建批处理器
	processor := audio.NewBatchProcessor(
		config.MediaFolder,
		config.OutputFolder,
		tempDir,
		batchProgressCallback,
		config,
	)

	// 设置进度管理器
	if progressManager != nil {
		processor.SetProgressManager(progressManager)
	}

	// 创建处理器适配器
	processorAdapter := adapters.NewBatchProcessorAdapter(processor)

	fmt.Println("启动监听模式...")

	// 启动片段监控
	var stopSegmentMonitoring func()
	if progressManager != nil {
		progressManager.CreateProgressBar("segments_monitor", 100, "片段监控", "等待处理开始...")
		stopSegmentMonitoring = watcher.StartSegmentMonitoring(tempDir, progressManager)
	}

	// 1. 启动下载目录监控，将文件移动到媒体目录
	fmt.Printf("监控下载目录: %s -> %s\n", config.OutputFolder, config.MediaFolder)
	stopDownloadMonitor, err := watcher.StartFolderMonitoring(config.OutputFolder, config.MediaFolder)
	if err != nil {
		utils.Fatal("启动下载目录监控失败: %v", err)
	}

	// 2. 启动媒体目录监控，处理媒体文件
	fmt.Printf("监控媒体目录: %s\n", config.MediaFolder)
	stopMediaMonitor, err := watcher.StartMediaFolderMonitoring(config.MediaFolder, processorAdapter, progressManager)
	if err != nil {
		stopDownloadMonitor() // 如果失败，停止之前启动的监控
		if stopSegmentMonitoring != nil {
			stopSegmentMonitoring()
		}
		utils.Fatal("启动媒体目录监控失败: %v", err)
	}

	// 提示用户如何退出
	fmt.Println("\n监控已启动，按Ctrl+C退出...")

	// 等待用户中断
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	fmt.Println("\n正在停止监控...")
	stopDownloadMonitor()
	stopMediaMonitor()
	if stopSegmentMonitoring != nil {
		stopSegmentMonitoring()
	}
	fmt.Println("监控已停止")
}

func main() {
	// 解析命令行参数
	flag.Parse()

	// 初始化日志
	utils.InitLogger(*logLevel, *logFile)

	// 初始化进度管理器
	progressManager = ui.NewProgressManager()

	// 打印欢迎信息
	printWelcome()

	// 加载配置
	config = loadConfig()

	// 检查ffmpeg是否可用
	if !checkDependencies() {
		utils.Fatal("缺少必要的依赖项，无法继续")
		os.Exit(1)
	}

	// 检查是否启用监听模式
	if config.WatchMode {
		startWatchMode(config)
		return
	}
	// 处理媒体文件
	results:= processMedia()
	// 程序结束前恢复日志输出到控制台
	utils.DisableTerminalProgress()

	// 处理完成后，清理所有进度条
	if progressManager != nil {
		progressManager.CloseAll("已完成")
	}

	// 打印处理完成消息
	color.Green("\n所有处理任务已完成!")

	if config.ExportSRT{
		utils.Info("启用SRT字幕导出功能")
		selector := registerService()
		runAsrService(config,selector)
	}

}
func runAsrService(config *models.Config ,selector *asr.ASRSelector) {
		// 执行识别
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
		defer cancel()
		start := time.Now()
		segments, serviceName, outputFiles, err := selector.RunWithService(ctx, *audioPath, config.ASRService,false, config, progressCallback)
		if err != nil {
			utils.Log.Fatalf("识别失败: %v", err)
		}
		
		duration := time.Since(start)
		utils.Log.Infof("使用 %s 服务识别完成，耗时 %.2f 秒", serviceName, duration.Seconds())
		
		// 输出结果文件信息
		if len(outputFiles) > 0 {
			utils.Log.Info("生成的文件:")
			for fileType, filePath := range outputFiles {
				utils.Log.Infof("- %s: %s", fileType, filePath)
			}
		}
		
		// 输出结果
		if len(segments) == 0 {
			utils.Log.Info("未识别出任何内容")
			return
		}
		
		utils.Log.Infof("识别结果 (%d 段):", len(segments))
		for i, seg := range segments {
			utils.Log.Infof("[%02d] %.2f-%.2f: %s", i+1, seg.StartTime, seg.EndTime, seg.Text)
		}
		
		// 输出服务统计信息
		stats := selector.GetStats()
		utils.Log.Info("ASR服务统计信息:")
		for name, stat := range stats {
			utils.Log.Infof("%s: 调用次数=%d, 成功率=%s, 可用=%v", 
				name, stat["count"], stat["success_rate"], stat["available"])
		}
}
func registerService() *asr.ASRSelector {
	selector := asr.NewASRSelector()

	selector.RegisterService("kuaishou", func(audioPath string, useCache bool) (asr.ASRService, error) {
		// 调用原始函数，它返回 *KuaiShouASR
		service, err := asr.NewKuaiShouASR(audioPath, useCache)
		// 返回时，Go 会自动将 *KuaiShouASR 转换为 ASRService 接口
		return service, err
	}, 10)

	selector.RegisterService("bcut", func(audioPath string, useCache bool) (asr.ASRService, error) {
		service, err := asr.NewBcutASR(audioPath, useCache)
		return service, err
	}, 30)

	return selector 
	
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
		utils.Error("未检测到FFmpeg，请确保FFmpeg已安装并添加到系统路径")
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
			utils.Warn("配置加载失败: %v，将使用默认配置", err)
		} else {
			color.Green("成功")
			// 打印是否启用SRT导出
			if config.ExportSRT {
				utils.Info("已启用SRT字幕导出功能")
			}
			if config.ExportJSON{
				utils.Info("已启用JSON字幕导出功能")
			}
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
