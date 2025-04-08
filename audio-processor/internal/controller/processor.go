package controller

import (
	"context"
	"fmt"
	"io/ioutil"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
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

// ProcessorController 处理器控制器，协调各个组件工作
type ProcessorController struct {
    // 配置
    Config *models.Config

    // UI组件
    ProgressManager *ui.ProgressManager
    
    // 处理组件
    BatchProcessor *audio.BatchProcessor
    ASRSelector   *asr.ASRSelector
    
    // 监控组件
    SegmentMonitor func()
    
    // 上下文控制
    ctx           context.Context
    cancelFunc    context.CancelFunc
    
    // 状态数据
    Stats struct {
        StartTime       time.Time
        TotalFiles      int
        SuccessfulFiles int
        FailedFiles     int
    }
    
    // 资源管理
    TempDir       string
    cleanup       []func() // 清理函数列表
    mu            sync.Mutex
}

func (pc *ProcessorController) batchProgressCallback(current, total int, filename string, result *audio.BatchResult) {
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

// NewProcessorController 创建处理器控制器
func NewProcessorController(configFile string, logLevel string, logFile string) (*ProcessorController, error) {
    // 创建上下文，支持取消
    ctx, cancel := context.WithCancel(context.Background())
    
    // 初始化控制器
    pc := &ProcessorController{
        Config:         models.NewDefaultConfig(),
        ctx:            ctx,
        cancelFunc:     cancel,
    }
    
    // 初始化日志
    if err := utils.InitLogger(logLevel, logFile); err != nil {
        return nil, fmt.Errorf("初始化日志失败: %v", err)
    }
        // 日志初始化后再创建ProgressManager
    pc.ProgressManager = ui.NewProgressManager()
    // 加载配置
    if configFile != "" {
        if err := pc.Config.LoadFromFile(configFile); err != nil {
            utils.Warn("配置加载失败: %v，将使用默认配置", err)
        }
    }
    
    // 创建临时目录
    tempDir, err := ioutil.TempDir("", "audio-processor")
    if err != nil {
        return nil, fmt.Errorf("创建临时目录失败: %v", err)
    }
    pc.TempDir = tempDir
    pc.addCleanup(func() { os.RemoveAll(tempDir) })
    
    // 初始化组件
    pc.initComponents()
    
    // 注册信号处理
    pc.setupSignalHandlers()
    
    return pc, nil
}

// 初始化所有组件
func (pc *ProcessorController) initComponents() {
    // 初始化批处理器
    pc.BatchProcessor = audio.NewBatchProcessor(
        pc.Config.MediaFolder, 
        pc.Config.OutputFolder, 
        pc.TempDir,
        pc.batchProgressCallback, 
        pc.Config,
    )
    pc.BatchProcessor.SetProgressManager(pc.ProgressManager)
    pc.BatchProcessor.SetContext(pc.ctx) // 设置上下文
    // 初始化ASR选择器
    pc.ASRSelector = asr.NewASRSelector()
    pc.BatchProcessor.SetASRSelector(pc.ASRSelector)
    pc.registerASRServices()
    
    // 启动片段监控
    pc.ProgressManager.CreateProgressBar("segments_monitor", 100, "片段监控", "等待处理开始...")
    stopMonitoring := watcher.StartSegmentMonitoring(pc.TempDir, pc.ProgressManager)
    pc.SegmentMonitor = stopMonitoring
    pc.addCleanup(stopMonitoring)
}

// 处理媒体文件
func (pc *ProcessorController) ProcessMedia() ([]audio.BatchResult, error) {
    pc.Stats.StartTime = time.Now()
    
    // 处理所有文件
    results, err := pc.BatchProcessor.ProcessVideoFiles()
    if err != nil {
        return nil, err
    }
    
    // 更新统计数据
    pc.updateStats(results)
    
    return results, nil
}

func (pc *ProcessorController) StartWatchMode() error {
    // 确保目录存在
    os.MkdirAll(pc.Config.OutputFolder, 0755)
    os.MkdirAll(pc.Config.MediaFolder, 0755)
    
    // 创建处理器适配器，并添加文件重命名处理
    processorAdapter := adapters.NewBatchProcessorAdapter(pc.BatchProcessor)
    processorAdapter.SetRenameHandler(func(oldPath, newPath string) {
        pc.BatchProcessor.UpdateProcessedRecordOnRename(oldPath, newPath)
    })
    
    // 监控下载目录
    stopDownloadMonitor, err := watcher.StartFolderMonitoring(
        pc.Config.OutputFolder, 
        pc.Config.MediaFolder,
    )
    if err != nil {
        return err
    }
    pc.addCleanup(stopDownloadMonitor)
    
    // 监控媒体目录
    stopMediaMonitor, err := watcher.StartMediaFolderMonitoring(
        pc.Config.MediaFolder, 
        processorAdapter, 
        pc.ProgressManager,
    )
    if err != nil {
        return err
    }
    pc.addCleanup(stopMediaMonitor)
    
    utils.Info("监控已启动，按Ctrl+C退出...")
    
    // 等待终止信号
    return pc.waitForTermination()
}

func (pc *ProcessorController) RunASRService(results []audio.BatchResult) {
    // 对每个成功处理的文件进行ASR识别
    for _, result := range results {
        if !result.Success {
            continue // 跳过处理失败的文件
        }

        // 获取处理后的文件路径
        audioPath := result.OutputPath
        
        // 执行识别
        ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
        defer cancel()
        
        utils.Info("开始识别文件: %s", audioPath)
        
        start := time.Now()
		
		progressCallback := func(percent int, message string) {
			utils.Info("进度 [%d%%] %s", percent, message)
		}

        segments, serviceName, outputFiles, err := pc.ASRSelector.RunWithService(
            ctx, audioPath, pc.Config.ASRService, false, pc.Config, progressCallback)
        
        if err != nil {
            utils.Error("识别失败: %v", err)
            continue
        }
        
        duration := time.Since(start)
        utils.Info("使用 %s 服务识别完成，耗时 %.2f 秒", serviceName, duration.Seconds())
        
        // 输出结果文件信息
        if len(outputFiles) > 0 {
            utils.Info("生成的文件:")
            for fileType, filePath := range outputFiles {
                utils.Info("- %s: %s", fileType, filePath)
            }
        }
        
        // 输出结果
        if len(segments) == 0 {
            utils.Info("未识别出任何内容")
            continue
        }
        
        utils.Info("识别结果 (%d 段):", len(segments))
        for i, seg := range segments {
            utils.Info("[%02d] %.2f-%.2f: %s", i+1, seg.StartTime, seg.EndTime, seg.Text)
        }
    }
    
    // 输出服务统计信息
    stats := pc.ASRSelector.GetStats()
    utils.Info("ASR服务统计信息:")
    for name, stat := range stats {
        utils.Info("%s: 调用次数=%d, 成功率=%s, 可用=%v", 
            name, stat["count"], stat["success_rate"], stat["available"])
    }
}
// 添加清理函数
func (pc *ProcessorController) addCleanup(cleanup func()) {
    pc.mu.Lock()
    defer pc.mu.Unlock()
    pc.cleanup = append(pc.cleanup, cleanup)
}

// 执行所有清理
func (pc *ProcessorController) Cleanup() {
    pc.mu.Lock()
    defer pc.mu.Unlock()
    
    // 逆序执行清理函数
    for i := len(pc.cleanup) - 1; i >= 0; i-- {
        pc.cleanup[i]()
    }
    
    // 清理进度条
    if pc.ProgressManager != nil {
        pc.ProgressManager.CloseAll("已完成")
    }
    
    // 恢复日志设置
    utils.DisableTerminalProgress()
}

// 注册ASR服务
func (pc *ProcessorController) registerASRServices() {
    pc.ASRSelector.RegisterService("kuaishou", 
        func(audioPath string, useCache bool) (asr.ASRService, error) {
            return asr.NewKuaiShouASR(audioPath, useCache)
        }, 
        10,
    )
    
    pc.ASRSelector.RegisterService("bcut", 
        func(audioPath string, useCache bool) (asr.ASRService, error) {
            return asr.NewBcutASR(audioPath, useCache)
        }, 
        30,
    )
}

// 设置中断处理
func (pc *ProcessorController) setupSignalHandlers() {
    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt, syscall.SIGTERM)
    
    go func() {
        <-c
        utils.Info("接收到中断信号，正在停止...")
        pc.cancelFunc() // 取消上下文
    }()
}

// 等待终止信号
func (pc *ProcessorController) waitForTermination() error {
    <-pc.ctx.Done()
    return nil
}

// 统计处理结果
func (pc *ProcessorController) updateStats(results []audio.BatchResult) {
    pc.Stats.TotalFiles = len(results)
    
    for _, result := range results {
        if result.Success {
            pc.Stats.SuccessfulFiles++
        } else {
            pc.Stats.FailedFiles++
        }
    }
}

// ProcessAudioWithASR 处理单个音频文件的ASR识别
func (pc *ProcessorController) ProcessAudioWithASR(audioPath string) error {
    if  audioPath == "" {
        return nil // ASR未启用或无音频文件，直接返回
    }
    
    utils.Info("开始对文件进行语音识别: %s", filepath.Base(audioPath))
    
    // 创建进度条ID
    barID := "asr_" + filepath.Base(audioPath)
    pc.ProgressManager.CreateProgressBar(barID, 100, "ASR识别 "+filepath.Base(audioPath), "准备中...")
    
    // 进度回调
    progressCallback := func(percent int, message string) {
        pc.ProgressManager.UpdateProgressBar(barID, percent, message)
    }
    
    // 创建上下文
    ctx, cancel := context.WithTimeout(pc.ctx, 10*time.Minute)
    defer cancel()
    
    // 执行ASR识别
    segments, _, outputFiles, err := pc.ASRSelector.RunWithService(
        ctx, 
        audioPath, 
        pc.Config.ASRService, 
        false,
        pc.Config,
        progressCallback,
    )
    
    if err != nil {
        pc.ProgressManager.CompleteProgressBar(barID, "识别失败")
        return fmt.Errorf("ASR识别失败: %w", err)
    }
    
    // 输出结果信息
    if len(outputFiles) > 0 {
        utils.Info("生成的字幕文件:")
        for fileType, filePath := range outputFiles {
            utils.Info("- %s: %s", fileType, filepath.Base(filePath))
        }
    }
    
    pc.ProgressManager.CompleteProgressBar(barID, "识别完成")
    utils.Info("文件 %s 识别完成，共 %d 段文本", filepath.Base(audioPath), len(segments))
    
    return nil
}