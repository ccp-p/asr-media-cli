package adapters

import (
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// RenameHandler 文件重命名处理函数类型
type RenameHandler func(oldPath, newPath string)

// MediaProcessor 是处理媒体文件的接口
type MediaProcessor interface {
	ProcessFile(filePath string) bool
	IsRecognizedFile(filePath string) bool
}


type BatchProcessorAdapter struct {
    processor     *audio.BatchProcessor
    renameHandler RenameHandler
}

// ProcessFile 处理文件
func (a *BatchProcessorAdapter) ProcessFile(filePath string) bool {
	result := a.processor.ProcessSingleFile(filePath)
	return result.Success
}

// IsRecognizedFile 检查文件是否已处理
func (a *BatchProcessorAdapter) IsRecognizedFile(filePath string) bool {
	// 调用批处理器的检查方法
	return a.processor.IsRecognizedFile(filePath)
}

// NewBatchProcessorAdapter 创建新的批处理器适配器
func NewBatchProcessorAdapter(processor *audio.BatchProcessor) *BatchProcessorAdapter {
	return &BatchProcessorAdapter{
		processor: processor,
	}
}
// SetRenameHandler 设置文件重命名处理函数
func (a *BatchProcessorAdapter) SetRenameHandler(handler RenameHandler) {
    a.renameHandler = handler
}

// HandleRename 处理文件重命名事件
func (a *BatchProcessorAdapter) HandleRename(oldPath, newPath string) {
    if a.renameHandler != nil {
        a.renameHandler(oldPath, newPath)
    } else {
        utils.Debug("未设置文件重命名处理函数")
    }
}
