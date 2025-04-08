package watcher

import (
	"path/filepath"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/adapters"
	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// MediaWatcher 媒体文件监控器
type MediaWatcher struct {
	mediaMonitor    *FolderMonitor
	outputMonitor   *FolderMonitor
	progressManager *ui.ProgressManager
	processor       *audio.BatchProcessor
	stopFuncs       []func()
}

// NewMediaWatcher 创建媒体文件监控器
func NewMediaWatcher(config *models.Config, progressManager *ui.ProgressManager) (*MediaWatcher, error) {
	// 创建处理器适配器
	processor := audio.NewBatchProcessor(
		config.MediaFolder,
		config.OutputFolder,
		filepath.Join(config.TempDir, "watch_temp"),
		nil, // 不使用回调，依赖进度条系统
		config,
	)
	
	// 设置进度管理器
	processor.SetProgressManager(progressManager)
	
	// 创建媒体文件监控器
	return &MediaWatcher{
		progressManager: progressManager,
		processor:       processor,
		stopFuncs:       make([]func(), 0),
	}, nil
}

// Start 启动监控
func (w *MediaWatcher) Start() error {
	// 创建处理器适配器
	processorAdapter := adapters.NewBatchProcessorAdapter(w.processor)
	
	// 启动媒体文件夹监控
	stopMedia, err := StartMediaFolderMonitoring(
		w.processor.MediaDir,
		processorAdapter,
		w.progressManager,
	)
	if err != nil {
		return err
	}
	w.stopFuncs = append(w.stopFuncs, stopMedia)
	
	// 启动输出文件夹监控（将输出文件夹中的媒体文件移动到媒体文件夹）
	stopOutput, err := StartFolderMonitoring(
		w.processor.OutputDir,
		w.processor.MediaDir,
	)
	if err != nil {
		return err
	}
	w.stopFuncs = append(w.stopFuncs, stopOutput)
	
	utils.Info("媒体文件监控已启动")
	return nil
}

// Stop 停止监控
func (w *MediaWatcher) Stop() {
	for _, stop := range w.stopFuncs {
		stop()
	}
	utils.Info("媒体文件监控已停止")
}

// WatchManager 监控管理器，管理所有监控活动
type WatchManager struct {
	mediaWatcher    *MediaWatcher
	segmentMonitor  *SegmentProgressMonitor
	progressManager *ui.ProgressManager
	config          *models.Config
}

// NewWatchManager 创建监控管理器
func NewWatchManager(config *models.Config, progressManager *ui.ProgressManager) (*WatchManager, error) {
	mediaWatcher, err := NewMediaWatcher(config, progressManager)
	if err != nil {
		return nil, err
	}
	
	segmentMonitor := NewSegmentProgressMonitor(config.TempDir, progressManager)
	
	return &WatchManager{
		mediaWatcher:    mediaWatcher,
		segmentMonitor:  segmentMonitor,
		progressManager: progressManager,
		config:          config,
	}, nil
}

// Start 启动所有监控
func (m *WatchManager) Start() error {
	// 启动段落监控
	m.segmentMonitor.Start()
	
	// 启动媒体文件监控
	if err := m.mediaWatcher.Start(); err != nil {
		m.segmentMonitor.Stop()
		return err
	}
	
	utils.Info("所有监控任务已启动")
	
	// 创建状态更新定时器
	go m.periodicStatusUpdate()
	
	return nil
}

// Stop 停止所有监控
func (m *WatchManager) Stop() {
	m.segmentMonitor.Stop()
	m.mediaWatcher.Stop()
	utils.Info("所有监控任务已停止")
}

// periodicStatusUpdate 定期更新状态
func (m *WatchManager) periodicStatusUpdate() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	for range ticker.C {
		m.progressManager.PrintStatus()
	}
}
