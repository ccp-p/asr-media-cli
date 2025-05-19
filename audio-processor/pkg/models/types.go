package models


// DataSegment 表示一个语音识别结果段落，对应Python中的ASRDataSeg
type DataSegment struct {
	Text      string   `json:"text"` // 识别出的文本内容
	StartTime float64  `json:"start_time"` // 开始时间（秒）
	EndTime   float64  `json:"end_time"`   // 结束时间（秒）
}

