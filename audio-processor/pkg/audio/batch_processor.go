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
	"github.com/sirupsen/logrus"
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

// BatchProcessor 批量处理器
type BatchProcessor struct {
	MediaDir        string
	OutputDir       string
	TempDir         string
	MaxConcurrency  int
	VideoExtensions []string
	Extractor       *AudioExtractor
	ProgressCallback BatchProgressCallback
	config 	   *models.Config
	ProgressManager *ui.ProgressManager
	ASRSelector	*asr.ASRSelector
	ctx context.Context
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

	return &BatchProcessor{
		MediaDir:       mediaDir,
		OutputDir:      outputDir,
		TempDir:        tempDir,
		MaxConcurrency: 4, // 默认并发数
		VideoExtensions: []string{".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"},
		Extractor:      NewAudioExtractor(tempSegmentsDir, nil, config),
		config: config,
		ProgressCallback: callback,
	}
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

	return allResults, nil
}

// ProcessSingleFile 处理单个文件
func (p *BatchProcessor) ProcessSingleFile(filePath string) BatchResult {
	return p.processSingleFile(filePath)
}

// IsRecognizedFile 检查文件是否已处理
func (p *BatchProcessor) IsRecognizedFile(filePath string) bool {
	// 获取不含路径和扩展名的基本文件名
	baseName := filepath.Base(filePath)
	baseName = baseName[:len(baseName)-len(filepath.Ext(baseName))]

	// 检查是否存在对应的输出文件
	outputPath := filepath.Join(p.OutputDir, baseName+".txt")
	if _, err := os.Stat(outputPath); err == nil {
		return true
	}

	// 检查part目录
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

	return false
}

// 处理单个文件
// 处理单个文件 - 主控制流程
func (p *BatchProcessor) processSingleFile(filePath string) BatchResult {
    // 第一步：提取音频
    result := p.extractAudioFromFile(filePath)
    
    // 如果音频提取成功且需要执行ASR处理
    if result.Success && p.config != nil && p.config.ExportSRT {
        p.performASROnAudio(&result)
    }
    
    return result
}

// performASROnAudio 对提取的音频执行ASR处理
func (p *BatchProcessor) performASROnAudio(result *BatchResult) (error) {
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
    

	utils.Log.Infof("开始对文件进行语音识别: %s", filepath.Base(audioPath))
    
    // 创建进度条ID
    barID := "asr_" + filepath.Base(audioPath)
    p.ProgressManager.CreateProgressBar(barID, 100, "ASR识别 "+filepath.Base(audioPath), "准备中...")
    
    // 进度回调
    progressCallback := func(percent int, message string) {
        p.ProgressManager.UpdateProgressBar(barID, percent, message)
    }
    
    // 创建上下文
    ctx, cancel := context.WithTimeout(p.ctx, 10*time.Minute)
    defer cancel()
    
    // 执行ASR识别
    segments, _, outputFiles, err := p.ASRSelector.RunWithService(
        ctx, 
        audioPath, 
        p.config.ASRService, 
        false, 
		p.config,
        progressCallback,
    )
    
    if err != nil {
        p.ProgressManager.CompleteProgressBar(barID, "识别失败")
		
        return fmt.Errorf("ASR识别失败: %w", err)
    }
    p.ProgressManager.CompleteProgressBar(barID, "识别完成")

   
    
    // 输出结果信息
    if len(outputFiles) > 0 {
        utils.Log.Info("生成的字幕文件:")
        for fileType, filePath := range outputFiles {
            utils.Log.Infof("- %s: %s", fileType, filepath.Base(filePath))
        }
    }
    
	
    utils.Log.Infof("文件 %s 识别完成，共 %d 段文本", filepath.Base(audioPath), len(segments))
    
  
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
        logrus.Infof("[%s] 进度: %d/%d - %s", filename, current, total, message)
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
    } else if ext == ".mp3" || ext == ".wav" {
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
