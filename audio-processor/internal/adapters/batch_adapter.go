package adapters

import (
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
)

// MediaProcessor 是处理媒体文件的接口
type MediaProcessor interface {
	ProcessFile(filePath string) bool
	IsRecognizedFile(filePath string) bool
}

// BatchProcessorAdapter 批处理器适配器，实现MediaProcessor接口
type BatchProcessorAdapter struct {
	Processor *audio.BatchProcessor
}


// ProcessFile 处理文件
func (a *BatchProcessorAdapter) ProcessFile(filePath string) bool {
	result := a.Processor.ProcessSingleFile(filePath)
	return result.Success
}

// IsRecognizedFile 检查文件是否已处理
func (a *BatchProcessorAdapter) IsRecognizedFile(filePath string) bool {
	// 调用批处理器的检查方法
	return a.Processor.IsRecognizedFile(filePath)
}

// NewBatchProcessorAdapter 创建新的批处理器适配器
func NewBatchProcessorAdapter(processor *audio.BatchProcessor) *BatchProcessorAdapter {
	return &BatchProcessorAdapter{
		Processor: processor,
	}
}
