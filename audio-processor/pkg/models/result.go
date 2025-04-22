package models


// Result 结果统计信息
type Result struct {
	FilePath      string            `json:"file_path"`    // 处理的文件路径
	Service       string            `json:"service"`      // 使用的ASR服务
	OutputFiles   map[string]string `json:"output_files"` // 输出文件路径
	SegmentCount  int               `json:"segment_count"`// 识别的文本段数
	DurationMs    int64             `json:"duration_ms"`  // 音频时长（毫秒）
	ProcessTimeMs int64             `json:"process_time_ms"` // 处理时间（毫秒）
}