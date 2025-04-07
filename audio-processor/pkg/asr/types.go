package asr

import "context"

// DataSegment 表示一个语音识别结果段落，对应Python中的ASRDataSeg
type DataSegment struct {
	Text      string  // 识别出的文本内容
	StartTime float64 // 开始时间（秒）
	EndTime   float64 // 结束时间（秒）
}

// ProgressCallback 是进度回调函数，用于通知识别过程的进度
type ProgressCallback func(percent int, message string)

// ASRService 定义了语音识别服务的接口，对应Python中的BaseASR
type ASRService interface {
	// GetResult 执行识别并返回结果
	GetResult(ctx context.Context, callback ProgressCallback) ([]DataSegment, error)
}
