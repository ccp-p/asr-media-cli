package watcher

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/sirupsen/logrus"
)

// SegmentProgressMonitor 监控片段处理进度
type SegmentProgressMonitor struct {
	TempDir        string
	ProgressManager *ui.ProgressManager
	StopChan       chan struct{}
	Interval       time.Duration
}

// NewSegmentProgressMonitor 创建新的片段进度监控器
func NewSegmentProgressMonitor(tempDir string, progressManager *ui.ProgressManager) *SegmentProgressMonitor {
	return &SegmentProgressMonitor{
		TempDir:        tempDir,
		ProgressManager: progressManager,
		StopChan:       make(chan struct{}),
		Interval:       2 * time.Second, // 默认2秒检查一次
	}
}

// Start 开始监控
func (m *SegmentProgressMonitor) Start() {
	go m.monitorRoutine()
}

// Stop 停止监控
func (m *SegmentProgressMonitor) Stop() {
	close(m.StopChan)
}

// monitorRoutine 监控协程
func (m *SegmentProgressMonitor) monitorRoutine() {
	ticker := time.NewTicker(m.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.checkSegments()
		case <-m.StopChan:
			return
		}
	}
}

// checkSegments 检查片段处理状态
func (m *SegmentProgressMonitor) checkSegments() {
	if m.ProgressManager == nil {
		return
	}

	// 创建监控进度条
	progressID := "segments_monitor"
	
	// 检查临时目录中的片段文件
	segmentsDir := filepath.Join(m.TempDir, "segments")
	
	// 确保目录存在
	if _, err := os.Stat(segmentsDir); os.IsNotExist(err) {
		return
	}
	
	// 获取目录下的所有文件
	files, err := os.ReadDir(segmentsDir)
	if err != nil {
		logrus.Debugf("监控临时片段目录失败: %v", err)
		return
	}
	
	// 按类型统计文件
	wavCount := 0
	for _, file := range files {
		if !file.IsDir() && filepath.Ext(file.Name()) == ".wav" {
			wavCount++
		}
	}
	
	// 只有当有片段时才更新进度条
	if wavCount > 0 {
		m.ProgressManager.UpdateProgressBar(progressID, wavCount, 
			fmt.Sprintf("已生成 %d 个音频片段", wavCount))
	}
}

// StartMonitoring 便捷函数：开始监控并返回停止函数
func StartSegmentMonitoring(tempDir string, progressManager *ui.ProgressManager) func() {
	monitor := NewSegmentProgressMonitor(tempDir, progressManager)
	monitor.Start()
	return monitor.Stop
}
