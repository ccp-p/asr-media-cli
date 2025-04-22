package audio

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/asr"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// BatchResult 存储批处理结果
type BatchResult struct {
	FilePath    string
	Success     bool
	OutputPath  string
	Error       error
	ProcessTime time.Duration
}

// BatchProgressCallback 批处理进度回调
type BatchProgressCallback func(current, total int, filename string, result *BatchResult)

// ProcessedRecord 表示已处理文件的记录
type ProcessedRecord struct {
	LastProcessedTime string            `json:"last_processed_time"`
	Completed         bool              `json:"completed"`
	Filename          string            `json:"filename"`
	TotalDuration     float64           `json:"total_duration"`
	TotalParts        int               `json:"total_parts,omitempty"`
	Parts             map[string]Part   `json:"parts,omitempty"`
}

// Part 表示文件处理的一部分
type Part struct {
	Completed      bool   `json:"completed"`
	OutputFile     string `json:"output_file"`
	CompletedTime  string `json:"completed_time"`
}

// BatchProcessor 批量处理器
type BatchProcessor struct {
	MediaDir           string
	OutputDir          string
	TempDir            string
	MaxConcurrency     int
	VideoExtensions    []string
	Extractor          *AudioExtractor
	ProgressCallback   BatchProgressCallback
	config             *models.Config
	ProgressManager    *ui.ProgressManager
	ASRSelector        *asr.ASRSelector
	ctx                context.Context
	processedRecordFile string
	processedRecords    map[string]ProcessedRecord
}

// SetASRSelector
func (p *BatchProcessor) SetASRSelector(selector *asr.ASRSelector) {
	p.ASRSelector = selector
}

// SetContext 设置上下文
func (p *BatchProcessor) SetContext(ctx context.Context) {
	p.ctx = ctx
}

// NewBatchProcessor 创建批处理器
func NewBatchProcessor(mediaDir, outputDir, tempDir string, callback BatchProgressCallback, config *models.Config) *BatchProcessor {
	// 确保目录存在
	os.MkdirAll(outputDir, 0755)
	os.MkdirAll(tempDir, 0755)

	tempSegmentsDir := filepath.Join(tempDir, "segments")
	os.MkdirAll(tempSegmentsDir, 0755)

	processor := &BatchProcessor{
		MediaDir:           mediaDir,
		OutputDir:          outputDir,
		TempDir:            tempDir,
		MaxConcurrency:     4, // 默认并发数
		VideoExtensions:    []string{".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"},
		Extractor:          NewAudioExtractor(tempSegmentsDir, nil, config),
		config:             config,
		ProgressCallback:   callback,
		processedRecordFile: filepath.Join(outputDir, "processed_records.json"),
		processedRecords:    make(map[string]ProcessedRecord),
	}

	// 加载处理记录
	processor.loadProcessedRecords()

	return processor
}

// loadProcessedRecords 从文件加载处理记录
func (p *BatchProcessor) loadProcessedRecords() {
	data, err := utils.LoadJSONFile(p.processedRecordFile, make(map[string]ProcessedRecord))
	if err != nil {
		utils.Warn("加载处理记录失败: %v, 将使用空记录", err)
		p.processedRecords = make(map[string]ProcessedRecord)
		return
	}

	if records, ok := data.(map[string]interface{}); ok {
		// 解析记录
		for path, record := range records {
			if recordMap, ok := record.(map[string]interface{}); ok {
				processed := ProcessedRecord{
					Filename:      utils.GetStringValue(recordMap, "filename", filepath.Base(path)),
					Completed:     utils.GetBoolValue(recordMap, "completed", false),
					TotalDuration: utils.GetFloat64Value(recordMap, "total_duration", 0),
					TotalParts:    int(utils.GetFloat64Value(recordMap, "total_parts", 0)),
				}

				// 解析时间
				processed.LastProcessedTime = utils.GetStringValue(recordMap, "last_processed_time", "")

				// 解析parts
				if partsData, ok := recordMap["parts"].(map[string]interface{}); ok {
					processed.Parts = make(map[string]Part)
					for partKey, partData := range partsData {
						if partMap, ok := partData.(map[string]interface{}); ok {
							part := Part{
								Completed:     utils.GetBoolValue(partMap, "completed", false),
								OutputFile:    utils.GetStringValue(partMap, "output_file", ""),
								CompletedTime: utils.GetStringValue(partMap, "completed_time", ""),
							}
							processed.Parts[partKey] = part
						}
					}
				}

				p.processedRecords[path] = processed
			}
		}
	} else {
		utils.Warn("处理记录格式错误，将使用空记录")
		p.processedRecords = make(map[string]ProcessedRecord)
	}

	utils.Info("已加载处理记录: %d 个文件", len(p.processedRecords))
}

// saveProcessedRecords 保存处理记录到文件
func (p *BatchProcessor) saveProcessedRecords() error {
	err := utils.SaveJSONFile(p.processedRecordFile, p.processedRecords)
	if err != nil {
		utils.Error("保存处理记录失败: %v", err)
		return fmt.Errorf("保存处理记录失败: %w", err)
	}
	return nil
}

// SetProgressManager 设置进度管理器
func (p *BatchProcessor) SetProgressManager(manager *ui.ProgressManager) {
	p.ProgressManager = manager
	// 同时设置提取器的进度管理器
	p.Extractor.SetProgressManager(manager)
}

// ProcessVideoFiles 并发处理多个视频文件
func (p *BatchProcessor) ProcessVideoFiles() ([]BatchResult, error) {
	// 获取所有视频文件
	files, err := p.scanMediaDirectory()
	if err != nil {
		return nil, err
	}

	if len(files) == 0 {
		return []BatchResult{}, nil
	}

	// 创建总进度条
	if p.ProgressManager != nil {
		p.ProgressManager.CreateProgressBar("batch_overall", len(files),
			"总体进度", fmt.Sprintf("0/%d 文件已处理", len(files)))
	}

	// 创建结果通道
	results := make(chan BatchResult, len(files))

	// 使用协程池处理文件
	var wg sync.WaitGroup
	sem := make(chan struct{}, p.MaxConcurrency) // 信号量限制并发

	for i, filePath := range files {
		wg.Add(1)
		sem <- struct{}{} // 获取信号量

		go func(index int, path string) {
			defer wg.Done()
			defer func() { <-sem }() // 释放信号量

			filename := filepath.Base(path)
			startTime := time.Now()

			// 通知处理开始
			if p.ProgressCallback != nil {
				p.ProgressCallback(index+1, len(files), filename, nil)
			}

			// 处理单个文件
			result := p.processSingleFile(path)
			result.ProcessTime = time.Since(startTime)

			// 通知处理结束
			if p.ProgressCallback != nil {
				p.ProgressCallback(index+1, len(files), filename, &result)
			}

			// 更新总进度条
			if p.ProgressManager != nil {
				p.ProgressManager.UpdateProgressBar("batch_overall", index+1,
					fmt.Sprintf("%d/%d 文件已处理", index+1, len(files)))
			}

			results <- result
		}(i, filePath)
	}

	// 等待所有文件处理完成
	wg.Wait()
	close(results)

	// 完成总进度条
	if p.ProgressManager != nil {
		p.ProgressManager.CompleteProgressBar("batch_overall", "所有文件处理完成")
	}

	// 收集所有结果
	allResults := make([]BatchResult, 0, len(files))
	for result := range results {
		allResults = append(allResults, result)
	}

	// 在批处理完成后，更新处理记录
	for _, result := range allResults {
		p.updateProcessedRecord(result.FilePath, &result)
	}

	// 保存处理记录
	if err := p.saveProcessedRecords(); err != nil {
		utils.Warn("保存处理记录失败: %v", err)
	}

	return allResults, nil
}

// ProcessSingleFile 处理单个文件
func (p *BatchProcessor) ProcessSingleFile(filePath string) BatchResult {
	result := p.processSingleFile(filePath)

	// 更新处理记录
	p.updateProcessedRecord(filePath, &result)

	return result
}

// IsRecognizedFile 检查文件是否已处理
func (p *BatchProcessor) IsRecognizedFile(filePath string) bool {
	// 获取不含路径和扩展名的基本文件名
	baseName := filepath.Base(filePath)
	baseName = baseName[:len(baseName)-len(filepath.Ext(baseName))]

	// 方法1: 检查是否存在对应的输出文件
	outputPath := filepath.Join(p.OutputDir, baseName+".txt")
	if _, err := os.Stat(outputPath); err == nil {
		return true
	}

	// 方法2: 检查part目录
	partDir := filepath.Join(p.OutputDir, baseName)
	if _, err := os.Stat(partDir); err == nil {
		// 检查是否有index.txt或part文件
		indexPath := filepath.Join(partDir, "index.txt")
		if _, err := os.Stat(indexPath); err == nil {
			return true
		}

		// 检查是否有part文件
		matches, err := filepath.Glob(filepath.Join(partDir, "part_*.txt"))
		if err == nil && len(matches) > 0 {
			return true
		}
	}

	// 方法3: 检查处理记录
	normalizedPath := filepath.Clean(filePath)
	if _, exists := p.processedRecords[normalizedPath]; exists {
		return true
	}

	// 方法4: 检查处理记录中是否有同名文件
	fileBaseName := filepath.Base(filePath)
	for recordPath, record := range p.processedRecords {
		if filepath.Base(recordPath) == fileBaseName || record.Filename == fileBaseName {
			return true
		}
	}

	return false
}

// updateProcessedRecord 更新处理记录
func (p *BatchProcessor) updateProcessedRecord(filePath string, result *BatchResult) {
	normalizedPath := filepath.Clean(filePath)

	// 获取或创建记录
	record, exists := p.processedRecords[normalizedPath]
	if !exists {
		record = ProcessedRecord{
			Filename: filepath.Base(filePath),
		}
	}

	// 更新记录
	record.LastProcessedTime = time.Now().Format("2006-01-02 15:04:05")
	record.Completed = result.Success

	if result.Success && result.OutputPath != "" {
		// 可以添加更多信息，如处理时长等
	}

	// 保存回记录表
	p.processedRecords[normalizedPath] = record

	// 保存到文件
	if err := p.saveProcessedRecords(); err != nil {
		utils.Warn("保存处理记录失败: %v", err)
	}
}

// UpdateProcessedRecordOnRename 当文件重命名时更新处理记录
func (p *BatchProcessor) UpdateProcessedRecordOnRename(oldPath, newPath string) {
	oldNormalized := filepath.Clean(oldPath)
	newNormalized := filepath.Clean(newPath)

	// 检查旧路径是否在记录中
	if record, exists := p.processedRecords[oldNormalized]; exists {
		// 删除旧记录，添加新记录
		delete(p.processedRecords, oldNormalized)
		p.processedRecords[newNormalized] = record

		// 更新文件名
		record.Filename = filepath.Base(newPath)
		p.processedRecords[newNormalized] = record

		// 保存更新后的记录
		if err := p.saveProcessedRecords(); err != nil {
			utils.Warn("保存处理记录失败: %v", err)
		}

		utils.Info("已更新处理记录: %s -> %s", oldPath, newPath)
	}
}

// 处理单个文件 - 主控制流程
func (p *BatchProcessor) processSingleFile(filePath string) BatchResult {
	// 第一步：提取音频
	result := p.extractAudioFromFile(filePath)

	// 如果音频提取成功且需要执行ASR处理
	if result.Success  {
		p.performASROnAudio(&result)
	}

	return result
}

// performASROnAudio 对提取的音频执行ASR处理
func (p *BatchProcessor) performASROnAudio(result *BatchResult) error {
	if result == nil || !result.Success || result.OutputPath == "" {
		return fmt.Errorf("无效的处理结果或音频路径")
	}

	audioPath := result.OutputPath
	filename := filepath.Base(result.FilePath)
	fileID := filename[:len(filename)-len(filepath.Ext(filename))]

	// 更新进度条
	if p.ProgressManager != nil {
		p.ProgressManager.UpdateProgressBar("file_"+fileID, 85, "执行语音识别...")
	}

	utils.Info("开始对文件进行语音识别: %s (路径: %s)", filepath.Base(audioPath), audioPath)

	// 检查文件是否存在
	if _, err := os.Stat(audioPath); os.IsNotExist(err) {
		utils.Error("音频文件不存在: %s", audioPath)
		if p.ProgressManager != nil {
			p.ProgressManager.CompleteProgressBar("file_"+fileID, "失败：文件不存在")
		}
		return fmt.Errorf("音频文件不存在: %s", audioPath)
	}

	// 创建进度条ID
	barID := "asr_" + filepath.Base(audioPath)
	p.ProgressManager.CreateProgressBar(barID, 100, "ASR识别 "+filepath.Base(audioPath), "准备中...")

	// 进度回调
	progressCallback := func(percent int, message string) {
		p.ProgressManager.UpdateProgressBar(barID, percent, message)
		utils.Debug("ASR进度 [%d%%]: %s", percent, message)
	}

	// 创建上下文
	ctx, cancel := context.WithTimeout(p.ctx, 15*time.Minute) // 增加超时时间
	defer cancel()

	// 执行ASR识别
	utils.Info("使用ASR服务: %s", p.config.ASRService)
	segments, _, outputFiles, err := p.ASRSelector.RunWithService(
		ctx,
		audioPath,
		p.config.ASRService,
		false,
		p.config,
		progressCallback,
	)

	if err != nil {
		utils.Error("ASR识别失败: %v", err)
		p.ProgressManager.CompleteProgressBar(barID, "识别失败: "+err.Error())
		
		// 即使识别失败，我们也标记文件为已处理，避免反复处理
		result.Success = true
		result.Error = err
		return err
	}

	// 检查识别结果
	if len(segments) == 0 {
		utils.Warn("ASR识别未返回任何文本段落，可能是音频中没有语音内容或识别失败")
		p.ProgressManager.CompleteProgressBar(barID, "识别完成但未找到文本")
	} else {
		p.ProgressManager.CompleteProgressBar(barID, "识别成功，共"+fmt.Sprintf("%d", len(segments))+"段文本")
	}

	// 输出结果信息
	if len(outputFiles) > 0 {
		utils.Info("生成的字幕文件:")
		for fileType, filePath := range outputFiles {
			utils.Info("- %s: %s", fileType, filepath.Base(filePath))
		}
	} else {
		utils.Warn("未生成任何输出文件")
	}

	utils.Info("文件 %s 识别完成，共 %d 段文本", filepath.Base(audioPath), len(segments))

	// 完成文件进度条
	if p.ProgressManager != nil {
		p.ProgressManager.CompleteProgressBar("file_"+fileID, "处理完成")
	}
	return nil
}

// extractAudioFromFile 从文件中提取音频
func (p *BatchProcessor) extractAudioFromFile(filePath string) BatchResult {
	result := BatchResult{
		FilePath: filePath,
		Success:  false,
	}

	filename := filepath.Base(filePath)
	fileID := filename[:len(filename)-len(filepath.Ext(filename))]

	// 创建文件进度条
	if p.ProgressManager != nil {
		p.ProgressManager.CreateProgressBar("file_"+fileID, 100,
			fmt.Sprintf("处理 %s", filename), "准备中")
	}

	// 为每个文件单独设置进度回调
	segmentCallback := func(current, total int, message string) {
		utils.Info("[%s] 进度: %d/%d - %s", filename, current, total, message)
	}

	// 设置提取器的回调
	p.Extractor.ProgressCallback = segmentCallback

	// 检查文件类型
	ext := filepath.Ext(filePath)
	isVideo := false
	for _, videoExt := range p.VideoExtensions {
		if videoExt == ext {
			isVideo = true
			break
		}
	}

	var audioPath string
	var err error

	// 根据文件类型处理
	if isVideo {
		// 从视频提取音频
		if p.ProgressManager != nil {
			p.ProgressManager.UpdateProgressBar("file_"+fileID, 20, "提取音频中")
		}

		audioPath, _, err = p.Extractor.ExtractAudioFromVideo(filePath, p.OutputDir)
		if err != nil {
			if p.ProgressManager != nil {
				p.ProgressManager.CompleteProgressBar("file_"+fileID, fmt.Sprintf("失败: %v", err))
			}

			result.Error = fmt.Errorf("从视频提取音频失败: %w", err)
			return result
		}

		if p.ProgressManager != nil {
			p.ProgressManager.UpdateProgressBar("file_"+fileID, 80, "音频提取完成")
		}
	} else if ext == ".mp3" || ext == ".wav" || ext == ".m4a" {
		// 直接使用音频文件
		audioPath = filePath

		if p.ProgressManager != nil {
			p.ProgressManager.UpdateProgressBar("file_"+fileID, 50, "处理音频文件")
		}
	} else {
		if p.ProgressManager != nil {
			p.ProgressManager.CompleteProgressBar("file_"+fileID, fmt.Sprintf("不支持的格式: %s", ext))
		}

		result.Error = fmt.Errorf("不支持的文件格式: %s", ext)
		return result
	}

	// 输出路径
	result.OutputPath = audioPath
	result.Success = true

	// 注意：不在这里完成进度条，因为可能还有ASR处理
	return result
}

// 扫描媒体目录
func (p *BatchProcessor) scanMediaDirectory() ([]string, error) {
	var files []string

	// 检查目录是否存在
	if _, err := os.Stat(p.MediaDir); os.IsNotExist(err) {
		return nil, fmt.Errorf("媒体目录不存在: %s", p.MediaDir)
	}

	entries, err := os.ReadDir(p.MediaDir)
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		ext := filepath.Ext(entry.Name())
		isSupported := false

		// 检查是否为支持的视频格式
		for _, videoExt := range p.VideoExtensions {
			if ext == videoExt {
				isSupported = true
				break
			}
		}

		// 添加音频格式
		if ext == ".mp3" || ext == ".wav" {
			isSupported = true
		}

		if isSupported {
			files = append(files, filepath.Join(p.MediaDir, entry.Name()))
		}
	}

	return files, nil
}
