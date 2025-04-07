package models


// DataSegment 表示一个语音识别结果段落，对应Python中的ASRDataSeg
type DataSegment struct {
	Text      string  // 识别出的文本内容
	StartTime float64 // 开始时间（秒）
	EndTime   float64 // 结束时间（秒）
}

