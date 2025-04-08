package audio

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/ui"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// ProgressCallback 是进度回调函数类型
type ProgressCallback func(current, total int, message string)

// AudioExtractor 音频提取器
type AudioExtractor struct {
	TempSegmentsDir string
	ProgressCallback ProgressCallback
	ProgressManager  *ui.ProgressManager
	concurrencyLimit int
}

// AudioSegment 表示一个音频片段
type AudioSegment struct {
	Index      int
	StartTime  int
	EndTime    int
	OutputPath string
}

// NewAudioExtractor 创建新的音频提取器
func NewAudioExtractor(tempSegmentsDir string, callback ProgressCallback,config *models.Config) *AudioExtractor {
	// 确保临时目录存在
	os.MkdirAll(tempSegmentsDir, 0755)
	
	return &AudioExtractor{
		TempSegmentsDir: tempSegmentsDir,
		ProgressCallback: callback,
		concurrencyLimit: config.MaxWorkers, // 默认并发数
	}
}

// SetConcurrencyLimit 设置并发限制
func (e *AudioExtractor) SetConcurrencyLimit(limit int) {
	if limit > 0 {
		e.concurrencyLimit = limit
	}
}

// SetProgressManager 设置进度管理器
func (e *AudioExtractor) SetProgressManager(manager *ui.ProgressManager) {
	e.ProgressManager = manager
}

// ExtractAudioFromVideo 从视频文件提取音频
func (e *AudioExtractor) ExtractAudioFromVideo(videoPath, outputFolder string) (string, bool, error) {
	videoFilename := filepath.Base(videoPath)
	baseName := videoFilename[:len(videoFilename)-len(filepath.Ext(videoFilename))]
	audioPath := filepath.Join(outputFolder, baseName+".mp3")
	
	// 检查音频文件是否已经存在
	if _, err := os.Stat(audioPath); err == nil {
		utils.Info("音频已存在: %s", audioPath)
		return audioPath, false, nil
	}
	
	// 准备进度条ID
	progressID := fmt.Sprintf("extract_%s", baseName)
	
	// 创建进度条（如果有进度管理器）
	if e.ProgressManager != nil {
		e.ProgressManager.CreateProgressBar(progressID, 100, fmt.Sprintf("提取 %s", videoFilename), "准备中")
	}
	
	// 准备进度回调
	if e.ProgressCallback != nil {
		e.ProgressCallback(0, 1, "准备提取音频")
	}
	
	// 使用FFmpeg提取音频
	cmd := exec.Command(
		"ffmpeg",
		"-i", videoPath,
		"-q:a", "0",
		"-map", "a",
		audioPath,
		"-y", // 覆盖已存在的文件
	)
	
	utils.Info("正在从视频提取音频: %s", videoFilename)
	
	// 更新进度条状态
	if e.ProgressManager != nil {
		e.ProgressManager.UpdateProgressBar(progressID, 30, "正在提取")
	}
	
	err := cmd.Run()
	if err != nil {
		// 更新失败状态
		if e.ProgressManager != nil {
			e.ProgressManager.CompleteProgressBar(progressID, fmt.Sprintf("失败: %v", err))
		}
		
		if e.ProgressCallback != nil {
			e.ProgressCallback(1, 1, fmt.Sprintf("提取失败: %v", err))
		}
		return "", false, fmt.Errorf("音频提取失败: %w", err)
	}
	
	// 检查文件是否成功生成
	if _, err := os.Stat(audioPath); err != nil {
		// 更新失败状态
		if e.ProgressManager != nil {
			e.ProgressManager.CompleteProgressBar(progressID, "失败: 文件不存在")
		}
		
		if e.ProgressCallback != nil {
			e.ProgressCallback(1, 1, "提取失败: 文件不存在")
		}
		return "", false, fmt.Errorf("提取的音频文件不存在: %s", audioPath)
	}
	
	utils.Info("音频提取成功: %s", audioPath)
	
	// 完成进度条
	if e.ProgressManager != nil {
		e.ProgressManager.CompleteProgressBar(progressID, "提取完成")
	}
	
	if e.ProgressCallback != nil {
		e.ProgressCallback(1, 1, "提取完成")
	}
	
	return audioPath, true, nil
}

// SplitAudioFile 将音频文件分割为较小片段，支持并发处理
func (e *AudioExtractor) SplitAudioFile(inputPath string, segmentLength int) ([]string, error) {
	filename := filepath.Base(inputPath)
	baseName := filename[:len(filename)-len(filepath.Ext(filename))]
	utils.Info("正在分割 %s 为小片段...", filename)
	
	// 获取音频总时长
	duration, err := e.getAudioDuration(inputPath)
	if err != nil {
		return nil, fmt.Errorf("获取音频时长失败: %w", err)
	}
	
	utils.Info("音频总时长: %d秒", duration)
	
	// 计算片段数量
	expectedSegments := (duration + segmentLength - 1) / segmentLength
	
	// 创建进度条
	progressID := fmt.Sprintf("split_%s", baseName)
	if e.ProgressManager != nil {
		e.ProgressManager.CreateProgressBar(progressID, expectedSegments, 
			fmt.Sprintf("分割 %s", filename), fmt.Sprintf("准备分割 %d 个片段", expectedSegments))
	}
	
	// 报告初始进度
	if e.ProgressCallback != nil {
		e.ProgressCallback(0, expectedSegments, "准备分割音频")
	}
	
	// 创建工作通道
	jobs := make(chan AudioSegment, expectedSegments)
	results := make(chan string, expectedSegments)
	errors := make(chan error, expectedSegments)
	progress := make(chan int, expectedSegments) // 进度通道
	
	// 启动工作协程池
	var wg sync.WaitGroup
	workerCount := e.concurrencyLimit
	if workerCount > expectedSegments {
		workerCount = expectedSegments
	}
	
	// 启动单独的进度更新协程
	wg.Add(1)
	go func() {
		defer wg.Done()
		completedCount := 0
		for range progress {
			completedCount++
			// 更新进度条
			if e.ProgressManager != nil {
				e.ProgressManager.UpdateProgressBar(progressID, completedCount, 
					fmt.Sprintf("已处理 %d/%d 个片段", completedCount, expectedSegments))
			}
			
			// 调用进度回调
			if e.ProgressCallback != nil {
				e.ProgressCallback(completedCount, expectedSegments, 
					fmt.Sprintf("导出片段 %d/%d", completedCount, expectedSegments))
			}
		}
	}()
	
	for w := 1; w <= workerCount; w++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			e.segmentWorker(id, jobs, results, errors, progress)
		}(w)
	}
	
	// 创建任务
	go func() {
		baseFilename := filename[:len(filename)-len(filepath.Ext(filename))]
		
		for i := 0; i < expectedSegments; i++ {
			startTime := i * segmentLength
			endTime := (i + 1) * segmentLength
			if endTime > duration {
				endTime = duration
			}
			
			outputFilename := fmt.Sprintf("%s_part%03d.wav", baseFilename, i+1)
			outputPath := filepath.Join(e.TempSegmentsDir, outputFilename)
			
			jobs <- AudioSegment{
				Index:      i,
				StartTime:  startTime,
				EndTime:    endTime,
				OutputPath: outputPath,
			}
		}
		close(jobs)
	}()
	
	// 等待所有工作完成
	go func() {
		wg.Wait()
		close(results)
		close(errors)
		close(progress)
	}()
	
	// 收集结果
	segmentFiles := make([]string, 0, expectedSegments)
	resultMap := make(map[int]string)
	errorOccurred := false
	
	// 处理错误
	for err := range errors {
		if err != nil {
			errorOccurred = true
			utils.Error("分割音频时出错: %v", err)
		}
	}
	
	if errorOccurred {
		// 完成进度条（出错状态）
		if e.ProgressManager != nil {
			e.ProgressManager.CompleteProgressBar(progressID, "分割失败")
		}
		
		return nil, fmt.Errorf("分割音频过程中发生错误")
	}
	
	// 处理结果
	for filename := range results {
		parts := filepath.Base(filename)
		resultMap[getSegmentIndex(parts)] = parts
	}
	
	// 按顺序组织结果
	for i := 0; i < expectedSegments; i++ {
		if filename, ok := resultMap[i]; ok {
			segmentFiles = append(segmentFiles, filename)
		}
	}
	
	// 完成进度条
	if e.ProgressManager != nil {
		e.ProgressManager.CompleteProgressBar(progressID, 
			fmt.Sprintf("完成 - %d 个片段", len(segmentFiles)))
	}
	
	// 完成进度
	if e.ProgressCallback != nil {
		e.ProgressCallback(
			expectedSegments,
			expectedSegments,
			fmt.Sprintf("完成 - %d 个片段", len(segmentFiles)),
		)
	}
	
	return segmentFiles, nil
}

// 工作协程函数，处理音频片段切分
func (e *AudioExtractor) segmentWorker(id int, jobs <-chan AudioSegment, 
	results chan<- string, errors chan<- error, progress chan<- int) {
	
	for job := range jobs {
		// 使用FFmpeg切分音频
		cmd := exec.Command(
			"ffmpeg",
			"-y",                                    // 覆盖输出文件
			"-i", job.OutputPath,                    // 输入文件
			"-ss", fmt.Sprintf("%d", job.StartTime), // 开始时间
			"-to", fmt.Sprintf("%d", job.EndTime),   // 结束时间
			"-ac", "1",                              // 单声道
			"-ar", "16000",                          // 16kHz采样率
			job.OutputPath,
		)
		
		err := cmd.Run()
		if err != nil {
			errors <- fmt.Errorf("片段 %d 导出失败: %w", job.Index+1, err)
			continue
		}
		
		utils.Debug("导出片段完成: %s", filepath.Base(job.OutputPath))
		results <- job.OutputPath
		progress <- 1 // 通知进度更新
	}
}

// 获取音频时长（秒）
func (e *AudioExtractor) getAudioDuration(audioPath string) (int, error) {
	cmd := exec.Command(
		"ffprobe",
		"-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1",
		audioPath,
	)
	
	output, err := cmd.Output()
	if err != nil {
		return 0, err
	}
	
	var duration float64
	_, err = fmt.Sscanf(string(output), "%f", &duration)
	if err != nil {
		return 0, err
	}
	
	return int(duration), nil
}

// 从文件名中提取片段索引
func getSegmentIndex(filename string) int {
	var index int
	_, err := fmt.Sscanf(filename, "part%03d.wav", &index)
	if err != nil {
		return 999 // 如果无法解析，返回一个大数值
	}
	return index - 1 // 转为0-based索引
}
