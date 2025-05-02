package asr

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/export"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// ASRProcessor 处理ASR结果和导出
type ASRProcessor struct {
	Config      *models.Config
	SRTExporter *export.SRTExporter
	JSONExporter *export.JSONExporter
}
// ProgressCallback 是进度回调函数，用于通知识别过程的进度
type ProgressCallback func(percent int, message string)

// ASRService 定义了语音识别服务的接口，对应Python中的BaseASR
type ASRService interface {
	// GetResult 执行识别并返回结果
	GetResult(ctx context.Context, callback ProgressCallback) ([]models.DataSegment, error)
}

// NewASRProcessor 创建新的ASR处理器
func NewASRProcessor(config *models.Config) *ASRProcessor {
	return &ASRProcessor{
		Config:      config,
		SRTExporter: export.NewSRTExporter(config.OutputFolder),
		JSONExporter: export.NewJSONExporter(config.OutputFolder),
	}
}

// ProcessResults 处理ASR结果并生成输出文件
func (p *ASRProcessor) ProcessResults(ctx context.Context, segments []models.DataSegment, audioPath string, partNum *int) (map[string]string, error) {
	outputFiles := make(map[string]string)
	
	// 1. 处理文本输出
	textPath, err := p.generateTextOutput(segments, audioPath, partNum)
	if err != nil {
		return nil, err
	}
	outputFiles["txt"] = textPath
	
	// 2. 如果配置指定，生成SRT字幕文件
	if p.Config.ExportSRT && len(segments) > 0 {
		srtPath, err := p.SRTExporter.ExportSRT(segments, audioPath, partNum)
		if err != nil {
			utils.Warn("导出SRT字幕失败: %v", err)
		} else {
			outputFiles["srt"] = srtPath
		}
	}
	// 3、 如果配置指定，生成JSON格式的文本文件
	if p.Config.ExportJSON && len(segments) > 0 {
		jsonPath, err := p.JSONExporter.ExportJSON(segments, audioPath, partNum)
		if err != nil {
			utils.Warn("导出JSON文件失败: %v", err)
		} else {
			outputFiles["json"] = jsonPath
		}
	}
	
	return outputFiles, nil
}

// generateTextOutput 生成文本输出
func (p *ASRProcessor) generateTextOutput(segments []models.DataSegment, audioPath string, partNum *int) (string, error) {
	var outputText strings.Builder
	
	// 1. 准备文件头信息
	baseName := filepath.Base(audioPath)
	baseName = strings.TrimSuffix(baseName, filepath.Ext(baseName))
	
	outputText.WriteString("# " + baseName)
	if partNum != nil {
		outputText.WriteString(fmt.Sprintf(" - 第 %d 部分", *partNum))
	}
	outputText.WriteString("\n# 处理时间: " + time.Now().Format("2006-01-02 15:04:05"))
	outputText.WriteString("\n\n")
	
	// 2. 格式化文本内容
	if p.Config.FormatText {
		formattedText := p.formatSegmentText(segments, p.Config.IncludeTimestamps)
		outputText.WriteString(formattedText)
	} else {
		// 简单合并所有文本段落
		for _, segment := range segments {
			if segment.Text != "" && segment.Text != "[无法识别的音频片段]" {
				outputText.WriteString(segment.Text)
				outputText.WriteString("\n\n")
			}
		}
	}
	
	// 3. 确定输出路径
	var outputFile string
	var outputMdFile string
	if partNum != nil {
		outputSubfolder := filepath.Join(p.Config.OutputFolder, baseName)
		if err := os.MkdirAll(outputSubfolder, 0755); err != nil {
			return "", fmt.Errorf("创建子目录失败: %w", err)
		}
		outputFile = filepath.Join(outputSubfolder, fmt.Sprintf("%s_part%d.txt", baseName, *partNum))
	} else {
		outputFile = filepath.Join(p.Config.OutputFolder, fmt.Sprintf("%s.txt", baseName))
		if(p.Config.ExportMD){
		  outputMdFile = filepath.Join(p.Config.OutputFolder, fmt.Sprintf("%s.md", baseName))
		}
	}

	if outputMdFile != "" {
		// 4. 写入Markdown文件
		if err := os.WriteFile(outputMdFile, []byte(outputText.String()), 0644); err != nil {
			return "", fmt.Errorf("写入Markdown文件失败: %w", err)
		}
	}
	// 4. 写入文件
	if err := os.WriteFile(outputFile, []byte(outputText.String()), 0644); err != nil {
		return "", fmt.Errorf("写入文本文件失败: %w", err)
	}
	
	return outputFile, nil
}

// formatSegmentText 格式化文本段落
func (p *ASRProcessor) formatSegmentText(segments []models.DataSegment, includeTimestamps bool) string {
	var formattedSegments []string
	
	for _, segment := range segments {
		if segment.Text == "" || segment.Text == "[无法识别的音频片段]" {
			continue
		}
		
		// 处理文本
		processedText := p.processSegmentText(segment.Text)
		
		// 添加时间戳（如果需要）
		if includeTimestamps {
			timeInfo := fmt.Sprintf("[%s-%s]", 
				utils.FormatTime(segment.StartTime), 
				utils.FormatTime(segment.EndTime))
			formattedSegments = append(formattedSegments, fmt.Sprintf("%s %s", timeInfo, processedText))
		} else {
			formattedSegments = append(formattedSegments, processedText)
		}
	}
	
	// 用新行分隔每个片段
	return strings.Join(formattedSegments, "\n\n")
}

// processSegmentText 处理文本片段
func (p *ASRProcessor) processSegmentText(text string) string {
	// 替换多个空格为一个
	text = strings.Join(strings.Fields(text), " ")
	
	// 中文内容中替换空格为逗号
	// 这需要正则表达式来实现，但简化起见，这里只是示例
	// 实际实现应该使用正则表达式匹配汉字之间的空格
	
	// 确保句尾有标点
	lastChar := ""
	if len(text) > 0 {
		lastChar = text[len(text)-1:]
	}
	if lastChar != "。" && lastChar != "！" && lastChar != "？" && 
	   lastChar != "." && lastChar != "!" && lastChar != "?" {
		text += "。" // 添加句号
	}
	
	return text
}
