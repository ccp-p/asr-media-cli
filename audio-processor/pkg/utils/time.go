package utils

import (
	"fmt"
	"math"
	"time"
)

// FormatTime 将秒数格式化为 mm:ss 或 hh:mm:ss 格式
func FormatTime(seconds float64) string {
	h := int(seconds / 3600)
    m := int(math.Mod(seconds, 3600) / 60)
    s := int(math.Mod(seconds, 60))
	
	if h > 0 {
		return fmt.Sprintf("%02d:%02d:%02d", h, m, s)
	}
	return fmt.Sprintf("%02d:%02d", m, s)
}

// FormatTimeDuration 格式化时间长度为易读格式
func FormatTimeDuration(seconds float64) string {
	h := int(seconds / 3600)
    m := int(math.Mod(seconds, 3600) / 60)
    s := int(math.Mod(seconds, 60))
	
	if h > 0 {
		return fmt.Sprintf("%d小时%d分钟%d秒", h, m, s)
	}
	if m > 0 {
		return fmt.Sprintf("%d分钟%d秒", m, s)
	}
	return fmt.Sprintf("%d秒", s)
}

// FormatChineseTimeDuration 格式化时间长度为中文格式
func FormatChineseTimeDuration(seconds float64) string {
	hours := int(seconds) / 3600
	minutes := (int(seconds) % 3600) / 60
	secs := int(seconds) % 60
	
	if hours > 0 {
		return fmt.Sprintf("%d时%d分%d秒", hours, minutes, secs)
	} else if minutes > 0 {
		return fmt.Sprintf("%d分%d秒", minutes, secs)
	}
	return fmt.Sprintf("%d秒", secs)
}

// GetCurrentTimeString 获取当前时间的字符串表示
func GetCurrentTimeString() string {
	return time.Now().Format("2006-01-02 15:04:05")
}

// FormatFileSize 将字节大小格式化为人类可读格式
func FormatFileSize(sizeBytes int64) string {
	const (
		B  int64 = 1
		KB int64 = 1024 * B
		MB int64 = 1024 * KB
		GB int64 = 1024 * MB
		TB int64 = 1024 * GB
	)
	
	var (
		unit     string
		unitSize int64
	)
	
	switch {
	case sizeBytes >= TB:
		unit = "TB"
		unitSize = TB
	case sizeBytes >= GB:
		unit = "GB"
		unitSize = GB
	case sizeBytes >= MB:
		unit = "MB"
		unitSize = MB
	case sizeBytes >= KB:
		unit = "KB"
		unitSize = KB
	default:
		unit = "B"
		unitSize = B
	}
	
	return fmt.Sprintf("%.2f %s", float64(sizeBytes)/float64(unitSize), unit)
}