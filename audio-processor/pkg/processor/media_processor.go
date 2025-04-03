package processor

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
	"github.com/sirupsen/logrus"
)

// MediaInfo 存储媒体文件的详细信息
type MediaInfo struct {
	Path       string  // 文件路径
	Name       string  // 文件名
	Format     string  // 文件格式
	Duration   float64 // 时长(秒)
	SampleRate int     // 采样率(Hz)
	Channels   int     // 声道数
	Bitrate    int     // 比特率(kbps)
	Size       int64   // 文件大小(字节)
}

// MediaProcessor 媒体处理器
type MediaProcessor struct {
	MediaDir     string              // 媒体文件目录
	OutputDir     string              // 输出目录
	ProcessedInfo map[string]struct{} // 已处理文件记录
}

// NewMediaProcessor 创建新的媒体处理器
func NewMediaProcessor(mediaDir , outputDir string) *MediaProcessor {
	// 确保目录存在
	os.MkdirAll(outputDir, 0755)
	
	return &MediaProcessor{
		OutputDir:     outputDir,
		MediaDir:     mediaDir,
		ProcessedInfo: make(map[string]struct{}),
	}
}

// CheckFFmpeg 检查FFmpeg是否可用
func (p *MediaProcessor) CheckFFmpeg() bool {
	cmd := exec.Command("ffmpeg", "-version")
	err := cmd.Run()
	return err == nil
}

// GetMediaInfo 获取媒体文件信息
func (p *MediaProcessor) GetMediaInfo(filePath string) (*MediaInfo, error) {
	cmd := exec.Command(
		"ffprobe",
		"-v", "error",
		"-show_entries", "format=duration,size,bit_rate:stream=sample_rate,channels",
		"-of", "default=noprint_wrappers=1:nokey=1",
		filePath,
	)
	
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("获取媒体信息失败: %w", err)
	}
	
	lines := strings.Split(string(output), "\n")
	if len(lines) < 4 {
		return nil, fmt.Errorf("无法解析媒体信息")
	}
	
	// 解析输出
	var (
		duration   float64
		sampleRate int
		channels   int
		bitrate    int
		size       int64
	)
	
	if s, err := strconv.ParseFloat(strings.TrimSpace(lines[0]), 64); err == nil {
		duration = s
	}
	
	if s, err := strconv.Atoi(strings.TrimSpace(lines[1])); err == nil {
		sampleRate = s
	}
	
	if s, err := strconv.Atoi(strings.TrimSpace(lines[2])); err == nil {
		channels = s
	}
	
	// 获取文件大小
	fileInfo, err := os.Stat(filePath)
	if err == nil {
		size = fileInfo.Size()
	}
	
	// 比特率可能是空的，需要特殊处理
	if len(lines) > 3 && strings.TrimSpace(lines[3]) != "N/A" {
		if s, err := strconv.Atoi(strings.TrimSpace(lines[3])); err == nil {
			bitrate = s / 1000 // 转换为kbps
		}
	}
	
	return &MediaInfo{
		Path:       filePath,
		Name:       filepath.Base(filePath),
		Format:     filepath.Ext(filePath)[1:], // 移除点号
		Duration:   duration,
		SampleRate: sampleRate,
		Channels:   channels,
		Bitrate:    bitrate,
		Size:       size,
	}, nil
}

// ProcessFile 处理单个文件，返回处理结果和错误
func (p *MediaProcessor) ProcessFile(filePath string) (string, error) {
	startTime := time.Now()
	
	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return "", fmt.Errorf("文件不存在: %s", filePath)
	}
	
	// 获取媒体信息
	_, err := p.GetMediaInfo(filePath)
	if err != nil {
		return "", err
	}
	
	
	// 将文件标记为已处理
	p.ProcessedInfo[filePath] = struct{}{}
	
	// 计算处理时间
	processingTime := time.Since(startTime).Seconds()
	
	return  fmt.Sprintf("处理用时: %s\n", utils.FormatChineseTimeDuration(processingTime)), nil
}

// ExtractAudioFromVideo 从视频文件提取音频
func (p *MediaProcessor) ExtractAudioFromVideo(videoPath string) (string, error) {
	// 创建输出文件路径
	baseName := strings.TrimSuffix(filepath.Base(videoPath), filepath.Ext(videoPath))
	audioPath := filepath.Join(p.MediaDir, baseName+".mp3")
	
	// 调用ffmpeg提取音频
	cmd := exec.Command(
		"ffmpeg",
		"-i", videoPath,
		"-q:a", "0",
		"-map", "a",
		audioPath,
		"-y", // 覆盖已存在的文件
	)
	
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("音频提取失败: %w", err)
	}
	
	logrus.Infof("成功从视频提取音频: %s -> %s", videoPath, audioPath)
	
	return audioPath, nil
}
