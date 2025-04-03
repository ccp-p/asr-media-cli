package watcher

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
	"github.com/fsnotify/fsnotify"
)

// FileEventHandler 是处理文件事件的接口
type FileEventHandler interface {
	OnFileCreated(filePath string)
	OnFileModified(filePath string)
	OnFileDeleted(filePath string)
}

// FolderMonitor 监控文件夹变化
type FolderMonitor struct {
	watcher        *fsnotify.Watcher
	folderPath     string
	fileExtensions []string
	handler        FileEventHandler
	debounceTime   time.Duration
	pendingFiles   map[string]*time.Timer
	mutex          sync.Mutex
	stopChan       chan struct{}
	progressManager *ui.ProgressManager
}

// NewFolderMonitor 创建新的文件夹监控器
func NewFolderMonitor(folderPath string, extensions []string, handler FileEventHandler, debounceTime time.Duration) (*FolderMonitor, error) {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, fmt.Errorf("创建文件监控器失败: %w", err)
	}

	monitor := &FolderMonitor{
		watcher:        watcher,
		folderPath:     folderPath,
		fileExtensions: extensions,
		handler:        handler,
		debounceTime:   debounceTime,
		pendingFiles:   make(map[string]*time.Timer),
		stopChan:       make(chan struct{}),
	}

	return monitor, nil
}

// SetProgressManager 设置进度管理器
func (m *FolderMonitor) SetProgressManager(manager *ui.ProgressManager) {
	m.progressManager = manager
}

// Start 开始监控文件夹
func (m *FolderMonitor) Start() error {
	// 确保文件夹存在
	if err := os.MkdirAll(m.folderPath, 0755); err != nil {
		return fmt.Errorf("创建文件夹失败: %w", err)
	}

	// 添加要监控的文件夹
	if err := m.watcher.Add(m.folderPath); err != nil {
		return fmt.Errorf("添加监控文件夹失败: %w", err)
	}

	// 启动监控协程
	go m.watchLoop()

	utils.Info("开始监控文件夹: %s", m.folderPath)
	return nil
}

// Stop 停止监控
func (m *FolderMonitor) Stop() {
	close(m.stopChan)
	m.watcher.Close()
	utils.Info("停止监控文件夹: %s", m.folderPath)

	// 取消所有待处理的文件定时器
	m.mutex.Lock()
	defer m.mutex.Unlock()
	for _, timer := range m.pendingFiles {
		timer.Stop()
	}
}

// watchLoop 监控循环
func (m *FolderMonitor) watchLoop() {
	for {
		select {
		case <-m.stopChan:
			return
		case event, ok := <-m.watcher.Events:
			if !ok {
				return
			}
			m.handleFileEvent(event)
		case err, ok := <-m.watcher.Errors:
			if !ok {
				return
			}
			utils.Error("监控文件夹时出错: %v", err)
		}
	}
}

// 处理文件事件
func (m *FolderMonitor) handleFileEvent(event fsnotify.Event) {
	// 只处理创建和修改事件
	if event.Op&(fsnotify.Create|fsnotify.Write) == 0 {
		return
	}

	filePath := event.Name
	if !m.isTargetFile(filePath) {
		return
	}

	m.mutex.Lock()
	defer m.mutex.Unlock()

	// 取消已存在的定时器
	if timer, exists := m.pendingFiles[filePath]; exists {
		timer.Stop()
	}

	// 创建新的定时器
	m.pendingFiles[filePath] = time.AfterFunc(m.debounceTime, func() {
		m.processFile(filePath)
	})

	utils.Debug("检测到文件变化: %s", filePath)
}

// 判断是否为目标文件类型
func (m *FolderMonitor) isTargetFile(filePath string) bool {
	// 检查是否为常规文件
	fileInfo, err := os.Stat(filePath)
	if err != nil || fileInfo.IsDir() {
		return false
	}

	// 检查扩展名
	ext := strings.ToLower(filepath.Ext(filePath))
	for _, targetExt := range m.fileExtensions {
		if ext == targetExt {
			return true
		}
	}
	return false
}

// 处理文件
func (m *FolderMonitor) processFile(filePath string) {
	m.mutex.Lock()
	delete(m.pendingFiles, filePath)
	m.mutex.Unlock()

	// 检查文件是否仍然存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return
	}

	utils.Info("准备处理文件: %s", filePath)
	if m.handler != nil {
		m.handler.OnFileCreated(filePath)
	}
}

// FileMovementHandler 实现文件移动处理
type FileMovementHandler struct {
	targetFolder string
	processedFiles map[string]bool
	mutex sync.Mutex
}

// NewFileMovementHandler 创建文件移动处理器
func NewFileMovementHandler(targetFolder string) *FileMovementHandler {
	// 确保目标文件夹存在
	os.MkdirAll(targetFolder, 0755)

	return &FileMovementHandler{
		targetFolder: targetFolder,
		processedFiles: make(map[string]bool),
	}
}

// OnFileCreated 处理文件创建事件
func (h *FileMovementHandler) OnFileCreated(filePath string) {
	h.mutex.Lock()
	defer h.mutex.Unlock()

	// 检查文件是否已处理
	if h.processedFiles[filePath] {
		return
	}

	h.moveFile(filePath)
	h.processedFiles[filePath] = true
}

// OnFileModified 处理文件修改事件
func (h *FileMovementHandler) OnFileModified(filePath string) {
	// 对于修改事件，不做特殊处理
}

// OnFileDeleted 处理文件删除事件
func (h *FileMovementHandler) OnFileDeleted(filePath string) {
	h.mutex.Lock()
	defer h.mutex.Unlock()
	delete(h.processedFiles, filePath)
}

// moveFile 将文件移动到目标文件夹
func (h *FileMovementHandler) moveFile(sourcePath string) {
	filename := filepath.Base(sourcePath)
	targetPath := filepath.Join(h.targetFolder, filename)
	
	// 如果目标文件已存在，添加时间戳
	if _, err := os.Stat(targetPath); err == nil {
		ext := filepath.Ext(filename)
		name := filename[:len(filename)-len(ext)]
		timestamp := time.Now().Format("20060102150405")
		newFilename := fmt.Sprintf("%s_%s%s", name, timestamp, ext)
		targetPath = filepath.Join(h.targetFolder, newFilename)
	}

	// 移动文件
	if err := os.Rename(sourcePath, targetPath); err != nil {
		utils.Error("移动文件失败 %s -> %s: %v", sourcePath, targetPath, err)
		return
	}

	utils.Info("文件已移动: %s -> %s", sourcePath, targetPath)
}


// StartFolderMonitoring 开始监控文件夹并移动文件
func StartFolderMonitoring(sourceFolder, targetFolder string) (func(), error) {
	handler := NewFileMovementHandler(targetFolder)
	
	extensions := []string{".mp4", ".mp3", ".wav", ".m4a", ".mov", ".avi", ".mkv", ".flv"}
	monitor, err := NewFolderMonitor(sourceFolder, extensions, handler, 5*time.Second)
	if err != nil {
		return nil, err
	}
	
	if err := monitor.Start(); err != nil {
		return nil, err
	}
	
	// 返回停止函数
	return func() {
		monitor.Stop()
	}, nil
}
