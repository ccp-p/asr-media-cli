package export

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// SRTExporter 负责将ASR结果导出为SRT字幕文件
type SRTExporter struct {
	OutputFolder string
}

// NewSRTExporter 创建一个新的SRT导出器
func NewSRTExporter(outputFolder string) *SRTExporter {
	return &SRTExporter{
		OutputFolder: outputFolder,
	}
}

// FormatSRTTime 将秒数格式化为SRT时间格式 (HH:MM:SS,mmm)
func (e *SRTExporter) FormatSRTTime(seconds float64) string {
	hours := int(seconds / 3600)
	minutes := int(math.Mod(seconds, 3600) / 60)
	secs := int(seconds) % 60
	milliseconds := int((seconds - float64(int(seconds))) * 1000)
	
	return fmt.Sprintf("%02d:%02d:%02d,%03d", hours, minutes, secs, milliseconds)
}

// GenerateSRTContent 生成SRT格式内容
func (e *SRTExporter) GenerateSRTContent(segments []models.DataSegment) string {
	var srtLines []string
	
	for i, segment := range segments {
		text := strings.TrimSpace(segment.Text)
		if text == "" || text == "[无法识别的音频片段]" {
			continue
		}
		
		startTime := segment.StartTime
		endTime := segment.EndTime
		
		if endTime <= startTime {
			// 确保结束时间大于开始时间，至少5秒
			endTime = startTime + 5.0
		}
		
		// 格式化SRT条目
		srtStart := e.FormatSRTTime(startTime)
		srtEnd := e.FormatSRTTime(endTime)
		
		// 添加序号、时间范围和文本
		srtLines = append(srtLines, fmt.Sprintf("%d", i+1))
		srtLines = append(srtLines, fmt.Sprintf("%s --> %s", srtStart, srtEnd))
		srtLines = append(srtLines, text)
		srtLines = append(srtLines, "") // 空行分隔
	}
	
	return strings.Join(srtLines, "\n")
}

// ExportSRT 导出SRT格式字幕文件
func (e *SRTExporter) ExportSRT(segments []models.DataSegment, filename string, partNum *int) (string, error) {
	// 创建输出文件夹
	if err := os.MkdirAll(e.OutputFolder, 0755); err != nil {
		return "", fmt.Errorf("创建输出目录失败: %w", err)
	}
	
	// 构建文件名
	baseName := filepath.Base(filename)
	baseName = strings.TrimSuffix(baseName, filepath.Ext(baseName))
	
	var outputFile string
	if partNum != nil {
		// 创建子文件夹
		outputSubfolder := filepath.Join(e.OutputFolder, baseName)
		if err := os.MkdirAll(outputSubfolder, 0755); err != nil {
			return "", fmt.Errorf("创建子目录失败: %w", err)
		}
		outputFile = filepath.Join(outputSubfolder, fmt.Sprintf("%s_part%d.srt", baseName, *partNum))
	} else {
		outputFile = filepath.Join(e.OutputFolder, fmt.Sprintf("%s.srt", baseName))
	}
	
	// 生成SRT内容
	srtContent := e.GenerateSRTContent(segments)
	
	// 写入文件
	if err := os.WriteFile(outputFile, []byte(srtContent), 0644); err != nil {
		return "", fmt.Errorf("写入SRT文件失败: %w", err)
	}
	
	utils.Info("已导出SRT字幕: %s", outputFile)
	return outputFile, nil
}
