package export

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// TranscriptSegment 表示字幕的一个片段
type TranscriptSegment struct {
    Start float64 `json:"start"`  // 开始时间（秒）
    End   float64 `json:"end"`    // 结束时间（秒）
    Text  string  `json:"text"`   // 该段文字
}

// TranscriptResult 表示整个转录结果
type TranscriptResult struct {
    Language string              `json:"language,omitempty"` // 检测语言（如 "zh"、"en"）
    FullText string              `json:"full_text"`          // 完整合并后的文本（用于摘要）
    Segments []TranscriptSegment `json:"segments"`           // 分段结构，适合前端显示时间轴字幕等
    Raw      interface{}         `json:"raw,omitempty"`      // 原始响应数据，便于调试或平台特性处理
}

// JSONExporter 负责将ASR结果导出为JSON文件
type JSONExporter struct {
    OutputFolder string
}

// NewJSONExporter 创建一个新的JSON导出器
func NewJSONExporter(outputFolder string) *JSONExporter {
    return &JSONExporter{
        OutputFolder: outputFolder,
    }
}

// GenerateJSONContent 根据数据段生成TranscriptResult结构
func (e *JSONExporter) GenerateJSONContent(segments []models.DataSegment) TranscriptResult {
    // 创建TranscriptResult
    result := TranscriptResult{
        Language: "zh", // 默认为自动检测，实际应用中应该从识别结果中获取
        Segments: make([]TranscriptSegment, 0),
    }

    // 构建完整文本和分段
    var fullTextBuilder strings.Builder
    
    for _, segment := range segments {
        text := strings.TrimSpace(segment.Text)
        if text == "" || text == "[无法识别的音频片段]" {
            continue
        }
        
        // 添加到完整文本
        if fullTextBuilder.Len() > 0 {
            fullTextBuilder.WriteString(" ")
        }
        fullTextBuilder.WriteString(text)
        
        // 确保结束时间大于开始时间
        endTime := segment.EndTime
        if endTime <= segment.StartTime {
            endTime = segment.StartTime + 5.0
        }
        
        // 添加到分段
        result.Segments = append(result.Segments, TranscriptSegment{
            Start: segment.StartTime,
            End:   endTime,
            Text:  text,
        })
    }
    
    result.FullText = fullTextBuilder.String()
    
    return result
}

// ExportJSON 导出JSON格式文件
func (e *JSONExporter) ExportJSON(segments []models.DataSegment, filename string, partNum *int) (string, error) {
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
        outputFile = filepath.Join(outputSubfolder, fmt.Sprintf("%s_part%d_json.txt", baseName, *partNum))
    } else {
        outputFile = filepath.Join(e.OutputFolder, fmt.Sprintf("%s_json.txt", baseName))
    }
    
    // 生成JSON内容
    jsonContent := e.GenerateJSONContent(segments)
    
    // 转换为JSON字符串
    jsonData, err := json.MarshalIndent(jsonContent, "", "  ")
    if err != nil {
        return "", fmt.Errorf("JSON编码失败: %w", err)
    }
    
    // 写入文件
    if err := os.WriteFile(outputFile, jsonData, 0644); err != nil {
        return "", fmt.Errorf("写入JSON文件失败: %w", err)
    }
    
    utils.Info("已导出JSON文件: %s", outputFile)
    return outputFile, nil
}