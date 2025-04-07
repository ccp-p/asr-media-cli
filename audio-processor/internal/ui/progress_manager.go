package ui

import (
	"fmt"
	"sync"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// ProgressManager 管理多个进度条
type ProgressManager struct {
	progressBars map[string]*ProgressBar
	mutex        sync.Mutex
	enabled      bool
	terminal     *TerminalManager
}

// 在初始化时启用终端进度条模式
func NewProgressManager() *ProgressManager {
	// 启用终端进度条模式，将日志重定向到文件
	utils.EnableTerminalProgress()

	return &ProgressManager{
		progressBars: make(map[string]*ProgressBar),
		terminal:     GetTerminalManager(),
		enabled:      true,
	}
}

// CreateProgressBar 创建并注册一个新的进度条
func (pm *ProgressManager) CreateProgressBar(id string, total int, prefix string, suffix string) *ProgressBar {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	// 如果已经存在同名进度条，先完成它
	if bar, exists := pm.progressBars[id]; exists {
		bar.Complete("已被替换")
	}

	if !pm.enabled {
		return nil
	}
    // 创建新的进度条对象
    bar := NewProgressBar(total, prefix, suffix)
    
	pm.progressBars[id] = bar
	return bar
}

// GetProgressBar 获取已存在的进度条
func (pm *ProgressManager) GetProgressBar(id string) *ProgressBar {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	return pm.progressBars[id]
}

// 在 UpdateProgressBar 方法中使用终端管理器
func (pm *ProgressManager) UpdateProgressBar(id string, progress int, message string) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	// 使用终端管理器更新进度
	bar, exists := pm.progressBars[id]
	if !exists {
		bar = pm.CreateProgressBar(id, 100, "", message)
		pm.progressBars[id] = bar
	}

	bar.Update(progress, message)
	
	pm.terminal.UpdateProgress(fmt.Sprintf("%s | %s", bar.String(), message))
}

// CompleteProgressBar 完成进度条
// CompleteProgressBar 完成进度条
func (pm *ProgressManager) CompleteProgressBar(id string, suffix string) {
    if !pm.enabled {
        return
    }

    pm.mutex.Lock()
    bar, exists := pm.progressBars[id]
    pm.mutex.Unlock()

    if exists && bar != nil { // 添加非空检查
        // 安全设置进度为100%
        if bar.Total <= 0 {
            bar.Total = 100
        }
        bar.Current = bar.Total
        
        bar.Complete(suffix)

        // 完成后移除进度条
        pm.RemoveProgressBar(id)
    }
}

// RemoveProgressBar 移除进度条
func (pm *ProgressManager) RemoveProgressBar(id string) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	delete(pm.progressBars, id)
}

// CloseAll 完成所有进度条
func (pm *ProgressManager) CloseAll(suffix string) {
	if !pm.enabled {
		return
	}

	pm.mutex.Lock()
	bars := make([]*ProgressBar, 0, len(pm.progressBars))
	for _, bar := range pm.progressBars {
		bars = append(bars, bar)
	}
	pm.mutex.Unlock()

	for _, bar := range bars {
		bar.Complete(suffix)
	}

	// 清空进度条映射
	pm.mutex.Lock()
	pm.progressBars = make(map[string]*ProgressBar)
	pm.mutex.Unlock()
}

// PrintStatus 打印当前所有进度条的状态
func (pm *ProgressManager) PrintStatus() {
	if !pm.enabled {
		return
	}

	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	fmt.Println("\n当前进度状态:")
	for id, bar := range pm.progressBars {
		percent := float64(bar.Current) / float64(bar.Total) * 100
		fmt.Printf("- %s: %.1f%% (%d/%d) %s\n",
			id, percent, bar.Current, bar.Total, bar.Suffix)
	}
}
