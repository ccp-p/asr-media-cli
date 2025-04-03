// 将更新序列化为JSON再反序列化到结构体中    // 这种方式处理map到struct的转换较为方便    updateBytes, err := json.Marshal(updates)    if err != nil {        return fmt.Errorf("序列化更新数据失败: %w", err)    }        err = json.Unmarshal(updateBytes, c)    if err != nil {        // 回滚配置        *c = tempConfig        return fmt.Errorf("应用配置更新失败: %w", err)    }        // 验证配置    if err := c.Validate(); err != nil {        // 回滚配置        *c = tempConfig        return err    }        return nil}// Reset 重置为默认配置func (c *Config) Reset() {    defaultConfig := NewDefaultConfig()    *c = *defaultConfig}// PrintConfig 打印当前配置func (c *Config) PrintConfig() {    fmt.Println("\n当前配置:")    bytes, _ := json.MarshalIndent(c, "", "  ")    fmt.Println(string(bytes))}// 确保目录存在，如果不存在则创建func ensureDirExists(path string) error {    if path == "" {        return nil // 空路径视为可选    }        if _, err := os.Stat(path); os.IsNotExist(err) {        return os.MkdirAll(path, 0755)    }        return nil}

package utils

import (
	"fmt"
	"time"
)

// FormatTimeDuration 格式化时间长度为易读格式
func FormatTimeDuration(seconds float64) string {
    hours := int(seconds) / 3600
    minutes := (int(seconds) % 3600) / 60
    secs := int(seconds) % 60
    
    if hours > 0 {
        return fmt.Sprintf("%dh %dm %ds", hours, minutes, secs)
    } else if minutes > 0 {
        return fmt.Sprintf("%dm %ds", minutes, secs)
    }
    return fmt.Sprintf("%ds", secs)
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