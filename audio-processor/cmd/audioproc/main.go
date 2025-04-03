package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/fatih/color"
	"github.com/sirupsen/logrus"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/processor"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/scanner"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

var (
	outputDir  = flag.String("output", "D:/download/dest", "输出目录")
	tempDir    = flag.String("temp", "./temp", "临时文件目录")
	configFile = flag.String("config", "", "配置文件路径")
	logLevel   = flag.String("log-level", "info", "日志级别 (debug, info, warn, error)")
	logFile    = flag.String("log-file", "", "日志文件路径")
)

func main() {
	// 解析命令行参数
	flag.Parse()
	
	// 初始化日志
	_, err := logrus.ParseLevel(*logLevel)
	if err != nil {
		  *logLevel = "info"
	}
	
	utils.InitLogger(*logLevel, *logFile)
	
	// 打印欢迎信息
	printWelcome()
	
	// 加载配置
	config := loadConfig()
	
	// 检查ffmpeg是否可用
	if !checkDependencies() {
		logrus.Fatal("缺少必要的依赖项，无法继续")
		os.Exit(1)
	}
	
	// 创建处理器
	mediaProc := processor.NewMediaProcessor(config.OutputFolder, *tempDir)
	
	// 扫描媒体文件
	mediaScanner := scanner.NewMediaScanner()
	files, err := mediaScanner.ScanDirectory(config.MediaFolder)
	if err != nil {
		logrus.Fatalf("扫描媒体目录失败: %v", err)
	}
	
	if len(files) == 0 {
		logrus.Info("没有找到媒体文件，程序退出")
		return
	}
	
	// 打印媒体文件信息
	fmt.Println("\n找到以下媒体文件:")
	fmt.Println("--------------------")
	for i, file := range files {
		fileType := "音频"
		if file.IsVideo {
			fileType = "视频"
		}
		fmt.Printf("%d. [%s] %s (%.2f MB)\n", 
			i+1, fileType, file.Name, float64(file.Size)/(1024*1024))
	}
	fmt.Println("--------------------")
	
	// 处理所有文件
	for i, file := range files {
		fmt.Printf("\n[%d/%d] 处理文件: %s\n", i+1, len(files), file.Name)
		
		startTime := time.Now()
		
		var result string
		var err error
		
		// 根据文件类型进行不同处理
		if file.IsVideo && config.ProcessVideo {
			fmt.Println("检测到视频文件，正在提取音频...")
			audioPath, err := mediaProc.ExtractAudioFromVideo(file.Path)
			if err != nil {
				logrus.Errorf("提取音频失败: %v", err)
				continue
			}
			
			fmt.Println("音频提取成功，正在分析...")
			result, err = mediaProc.ProcessFile(audioPath)
			if err != nil {
				logrus.Errorf("分析音频失败: %v", err)
				continue
			}
		} else if file.IsAudio {
			fmt.Println("正在分析音频文件...")
			result, err = mediaProc.ProcessFile(file.Path)
		} else {
			fmt.Println("跳过不支持的文件类型")
			continue
		}
		
		if err != nil {
			logrus.Errorf("处理失败: %v", err)
			continue
		}
		
		// 打印结果
		color.Green("\n%s", result)
		
		// 显示处理时间
		duration := time.Since(startTime)
		fmt.Printf("处理用时: %s\n", utils.FormatTimeDuration(duration.Seconds()))
	}
	
	fmt.Println("\n所有文件处理完成!")
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
	cmd := processor.NewMediaProcessor("", "")
	if !cmd.CheckFFmpeg() {
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
