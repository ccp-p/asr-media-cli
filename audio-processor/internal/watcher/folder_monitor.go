package watcher

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/adapters"
	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/fsnotify/fsnotify"
	"github.com/sirupsen/logrus"
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
	processor      adapters.MediaProcessor
	debounceTime   time.Duration
	pendingFiles   map[string]*time.Timer
	processedFiles map[string]bool
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
		processedFiles: make(map[string]bool),
		stopChan:       make(chan struct{}),
	}

	return monitor, nil
}

// NewMediaFolderMonitor 创建媒体文件夹监控器
func NewMediaFolderMonitor(folderPath string, processor adapters.MediaProcessor, progressManager *ui.ProgressManager) (*FolderMonitor, error) {
	// 定义支持的媒体文件扩展名
	extensions := []string{
		".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", // 音频文件
		".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv",  // 视频文件
	}
	
	// 创建处理器
	handler := &MediaFileHandler{
		processor: processor,
	}
	
	// 创建监控器
	monitor, err := NewFolderMonitor(folderPath, extensions, handler, 5*time.Second)
	if err != nil {
		return nil, err
	}
	
	// 设置进度管理器
	monitor.SetProgressManager(progressManager)
	monitor.processor = processor
	
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
	
	// 处理已存在的文件
	if m.processor != nil {
		go m.processExistingFiles()
	}

	logrus.Infof("开始监控文件夹: %s", m.folderPath)
	return nil
}

// processExistingFiles 处理文件夹中已存在的文件
func (m *FolderMonitor) processExistingFiles() {
	entries, err := os.ReadDir(m.folderPath)
	if err != nil {
		logrus.Errorf("读取文件夹失败: %v", err)
		return
	}
	
	var mediaFiles []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		
		filePath := filepath.Join(m.folderPath, entry.Name())
		if m.isTargetFile(filePath) {
			mediaFiles = append(mediaFiles, filePath)
		}
	}
	
	logrus.Infof("找到 %d 个现有媒体文件", len(mediaFiles))
	
	// 创建进度条
	if m.progressManager != nil {
		m.progressManager.CreateProgressBar("existing_files", len(mediaFiles), 
			"处理现有文件", "开始处理")
	}
	
	// 处理文件
	for i, filePath := range mediaFiles {
		// 检查是否已处理
		if m.processor != nil && m.processor.IsRecognizedFile(filePath) {
			logrus.Infof("跳过已处理的文件: %s", filepath.Base(filePath))
			continue
		}
		
		// 更新进度
		if m.progressManager != nil {
			m.progressManager.UpdateProgressBar("existing_files", i+1,
				fmt.Sprintf("处理 %d/%d: %s", i+1, len(mediaFiles), filepath.Base(filePath)))
		}
		
		// 处理文件
		m.processFile(filePath)
	}
	
	// 完成进度条
	if m.progressManager != nil {
		m.progressManager.CompleteProgressBar("existing_files", "现有文件处理完成")
	}
}

// Stop 停止监控
func (m *FolderMonitor) Stop() {
	close(m.stopChan)
	m.watcher.Close()
	logrus.Info("停止监控文件夹: %s", m.folderPath)

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
			logrus.Errorf("监控文件夹时出错: %v", err)
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

	logrus.Debugf("检测到文件变化: %s", filePath)
}

// 判断是否为目标文件类型
func (m *FolderMonitor) isTargetFile(filePath string) bool {
	// 检查是否为常规文件
	fileInfo, err := os.Stat(filePath)
	if err != nil || fileInfo.IsDir() {
		return false
	}

	// 检查是否为隐藏文件
	basename := filepath.Base(filePath)
	if strings.HasPrefix(basename, ".") {
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
	// 检查是否已处理过
	if m.processedFiles[filePath] {
		m.mutex.Unlock()
		return
	}
	
	// 标记为已处理
	m.processedFiles[filePath] = true
	delete(m.pendingFiles, filePath)
	m.mutex.Unlock()

	// 检查文件是否仍然存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return
	}

	logrus.Infof("准备处理文件: %s", filePath)
	
	// 使用处理器处理文件
	if m.processor != nil {
		go func() {
			// 等待文件写入完成
			time.Sleep(2 * time.Second)
			
			if m.processor.ProcessFile(filePath) {
				logrus.Infof("文件处理成功: %s", filePath)
			} else {
				logrus.Errorf("文件处理失败: %s", filePath)
			}
		}()
		return
	}
	
	// 如果没有处理器，使用事件处理器
	if m.handler != nil {
		m.handler.OnFileCreated(filePath)
	}
}

// MediaFileHandler 实现媒体文件处理
type MediaFileHandler struct {
	processor adapters.MediaProcessor
}

// OnFileCreated 处理文件创建事件
func (h *MediaFileHandler) OnFileCreated(filePath string) {
	if h.processor != nil {
		h.processor.ProcessFile(filePath)
	}
}

// OnFileModified 处理文件修改事件
func (h *MediaFileHandler) OnFileModified(filePath string) {
	// 调用创建处理方法，逻辑相同
	h.OnFileCreated(filePath)
}

// OnFileDeleted 处理文件删除事件
func (h *MediaFileHandler) OnFileDeleted(filePath string) {
	// 不处理删除事件
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
		logrus.Errorf("移动文件失败 %s -> %s: %v", sourcePath, targetPath, err)
		return
	}

	logrus.Infof("文件已移动: %s -> %s", sourcePath, targetPath)
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

// StartMediaFolderMonitoring 开始监控媒体文件夹并处理文件
func StartMediaFolderMonitoring(mediaFolder string, processor adapters.MediaProcessor, progressManager *ui.ProgressManager) (func(), error) {
	monitor, err := NewMediaFolderMonitor(mediaFolder, processor, progressManager)
	if err != nil {
		return nil, fmt.Errorf("创建媒体文件夹监控器失败: %w", err)
	}
	
	if err := monitor.Start(); err != nil {
		return nil, fmt.Errorf("启动媒体文件夹监控器失败: %w", err)
	}
	
	logrus.Infof("媒体文件夹监控已启动: %s", mediaFolder)
	
	// 返回停止函数
	return func() {
		monitor.Stop()
	}, nil
}
