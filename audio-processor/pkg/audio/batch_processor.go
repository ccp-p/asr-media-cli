package audio

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/asr"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
	"github.com/google/uuid"
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
		p.PerformASROnAudio(&result)
	}

	return result
}

// performASROnAudio 对提取的音频执行ASR处理并返回识别结果
func (p *BatchProcessor) PerformASROnAudio(result *BatchResult) ([]models.DataSegment, map[string]string, error) {
    if result == nil || !result.Success || result.OutputPath == "" {
        return nil, nil, fmt.Errorf("无效的处理结果或音频路径")
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
    fileInfo, err := os.Stat(audioPath)
    if os.IsNotExist(err) {
        utils.Error("音频文件不存在: %s", audioPath)
        if p.ProgressManager != nil {
            p.ProgressManager.CompleteProgressBar("file_"+fileID, "失败：文件不存在")
        }
        return nil, nil, fmt.Errorf("音频文件不存在: %s", audioPath)
    }
    
    // 检查文件大小
    if fileInfo.Size() == 0 {
        utils.Error("音频文件大小为0: %s", audioPath)
        if p.ProgressManager != nil {
            p.ProgressManager.CompleteProgressBar("file_"+fileID, "失败：文件大小为0")
        }
        return nil, nil, fmt.Errorf("音频文件大小为0: %s", audioPath)
    }

    // 创建进度条ID
    barID := "asr_" + filepath.Base(audioPath)
    if p.ProgressManager != nil {
        p.ProgressManager.CreateProgressBar(barID, 100, "ASR识别 "+filepath.Base(audioPath), "准备中...")
    }

    // 进度回调
    progressCallback := func(percent int, message string) {
        if p.ProgressManager != nil {
            p.ProgressManager.UpdateProgressBar(barID, percent, message)
        }
        utils.Debug("ASR进度 [%d%%]: %s", percent, message)
    }

    // 创建上下文，带有超时控制
    ctx, cancel := context.WithTimeout(p.ctx, 150*time.Minute) // 增加超时时间
    defer cancel()

    // 执行ASR识别，添加重试机制
    utils.Info("使用ASR服务: %s", p.config.ASRService)
    segments, serviceName, outputFiles, err := p.ASRSelector.RunWithService(
        ctx,
        audioPath,
        p.config.ASRService,
        false,
        p.config,
        progressCallback,
    )
    
    if err != nil {
        // 更多详细的错误信息
        utils.Error("ASR识别失败: %v (文件: %s, 服务: %s)", err, audioPath, serviceName)
        if p.ProgressManager != nil {
            p.ProgressManager.CompleteProgressBar(barID, "识别失败: "+err.Error())
        }
        
        // 即使识别失败，我们也标记文件为已处理，避免反复处理
        result.Success = false
        result.Error = err
        return nil, nil, err
    }

    // 检查识别结果
    if len(segments) == 0 {
        utils.Warn("ASR识别未返回任何文本段落，可能是音频中没有语音内容或识别失败")
        if p.ProgressManager != nil {
            p.ProgressManager.CompleteProgressBar(barID, "识别完成但未找到文本")
        }
    } else {
        if p.ProgressManager != nil {
            p.ProgressManager.CompleteProgressBar(barID, "识别成功，共"+fmt.Sprintf("%d", len(segments))+"段文本")
        }
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
    
    // 清理临时文件
    if result.Success && strings.ToLower(filepath.Ext(audioPath)) == ".mp3" {
        utils.Info("识别完成，删除提取的MP3文件: %s", audioPath)
        if err := os.Remove(audioPath); err != nil {
            utils.Warn("无法删除MP3文件: %v", err)
        } 
    }
    
    return segments, outputFiles, nil
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
	lowerExt := strings.ToLower(ext)
	isVideo := false
	for _, videoExt := range p.VideoExtensions {
		// lowercase扩展名以进行比较
		lowerVideoExt := strings.ToLower(videoExt)
    
	    if lowerVideoExt == lowerExt {
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



// WebResult 存储Web请求的处理结果
type WebResult struct {
    Success      bool             `json:"success"`
    ErrorMessage string           `json:"error_message,omitempty"`
    Segments     []models.DataSegment `json:"segments,omitempty"`
    OutputFiles  map[string]string `json:"output_files,omitempty"`
    ProcessTime  time.Duration    `json:"process_time_ms"`
}

// WebProcessor Web处理器
type WebProcessor struct {
    UploadDir   string
    TempDir     string
    OutputDir   string 
    Processor   *BatchProcessor
    MaxFileSize int64 // 最大文件大小（字节）
    Config      *models.Config
}

// NewWebProcessor 创建Web处理器
func NewWebProcessor(uploadDir, tempDir, outputDir string, config *models.Config) *WebProcessor {
    // 确保目录存在
    os.MkdirAll(uploadDir, 0755)
    os.MkdirAll(tempDir, 0755)
    os.MkdirAll(outputDir, 0755)

    // 创建批处理器
    processor := NewBatchProcessor("", outputDir, tempDir, nil, config)

    return &WebProcessor{
        UploadDir:   uploadDir,
        TempDir:     tempDir,
        OutputDir:   outputDir,
        Processor:   processor,
        MaxFileSize: 1024 * 1024 * 512, // 默认512MB
        Config:      config,
    }
}

// ProcessUploadedFile 处理上传的文件
func (w *WebProcessor) ProcessUploadedFile(file io.Reader, filename string) (*WebResult, error) {
    startTime := time.Now()
    
    // 生成唯一的文件名
    uniqueID := uuid.New().String()
    fileExt := filepath.Ext(filename)
    uniqueFilename := fmt.Sprintf("%s%s", uniqueID, fileExt)
    
    // 创建文件保存路径
    filePath := filepath.Join(w.UploadDir, uniqueFilename)
    
    // 创建临时文件
    tempFile, err := os.Create(filePath)
    if err != nil {
        return &WebResult{
            Success:      false,
            ErrorMessage: fmt.Sprintf("创建文件失败: %v", err),
            ProcessTime:  time.Since(startTime),
        }, err
    }
    defer tempFile.Close()
    
    // 写入文件内容
    _, err = io.Copy(tempFile, file)
    if err != nil {
        os.Remove(filePath) // 清理临时文件
        return &WebResult{
            Success:      false,
            ErrorMessage: fmt.Sprintf("保存文件失败: %v", err),
            ProcessTime:  time.Since(startTime),
        }, err
    }
    
    // 关闭文件以确保内容已完全写入
    tempFile.Close()
    
    // 检查文件类型
    ext := strings.ToLower(filepath.Ext(filename))
    isSupported := false
    
    // 检查视频格式
    for _, videoExt := range w.Processor.VideoExtensions {
        if strings.ToLower(videoExt) == ext {
            isSupported = true
            break
        }
    }
    
    // 检查音频格式
    if ext == ".mp3" || ext == ".wav" || ext == ".m4a" {
        isSupported = true
    }
    
    if !isSupported {
        os.Remove(filePath) // 清理临时文件
        return &WebResult{
            Success:      false,
            ErrorMessage: fmt.Sprintf("不支持的文件格式: %s", ext),
            ProcessTime:  time.Since(startTime),
        }, fmt.Errorf("不支持的文件格式: %s", ext)
    }
    
    // 设置上下文
    ctx := context.Background()
    w.Processor.SetContext(ctx)
    
    // 第一步：提取音频
    result := w.Processor.extractAudioFromFile(filePath)
    
    if !result.Success {
        os.Remove(filePath) // 清理上传的文件
        return &WebResult{
            Success:      false,
            ErrorMessage: fmt.Sprintf("提取音频失败: %v", result.Error),
            ProcessTime:  time.Since(startTime),
        }, result.Error
    }
    
    // 第二步：执行ASR识别
    segments, outputFiles, err := w.Processor.PerformASROnAudio(&result)
    
    // 清理临时文件
    os.Remove(filePath) // 删除上传的原始文件
    
    if err != nil {
        return &WebResult{
            Success:      false,
            ErrorMessage: fmt.Sprintf("语音识别失败: %v", err),
            ProcessTime:  time.Since(startTime),
        }, err
    }
    
    // 返回结果
    return &WebResult{
        Success:     true,
        Segments:    segments,
        OutputFiles: outputFiles,
        ProcessTime: time.Since(startTime),
    }, nil
}

// CleanupOldFiles 清理旧文件
func (w *WebProcessor) CleanupOldFiles(maxAge time.Duration) error {
    // 清理上传目录
    if err := cleanupDir(w.UploadDir, maxAge); err != nil {
        return err
    }
    
    // 清理临时目录
    if err := cleanupDir(w.TempDir, maxAge); err != nil {
        return err
    }
    
    return nil
}

// cleanupDir 清理指定目录中超过最大存活时间的文件
func cleanupDir(dir string, maxAge time.Duration) error {
    entries, err := os.ReadDir(dir)
    if err != nil {
        return err
    }
    
    now := time.Now()
    
    for _, entry := range entries {
        if entry.IsDir() {
            continue
        }
        
        info, err := entry.Info()
        if err != nil {
            continue
        }
        
        // 检查文件是否过期
        if now.Sub(info.ModTime()) > maxAge {
            filePath := filepath.Join(dir, entry.Name())
            os.Remove(filePath)
            utils.Info("已清理过期文件: %s", filePath)
        }
    }
    
    return nil
}