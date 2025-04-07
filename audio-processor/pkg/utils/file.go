package utils

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// LoadJSONFile 加载JSON文件，处理异常
func LoadJSONFile(filePath string, defaultVal interface{}) (interface{}, error) {
    if _, err := os.Stat(filePath); os.IsNotExist(err) {
        return defaultVal, nil
    }
    
    data, err := os.ReadFile(filePath)
    if err != nil {
        return defaultVal, fmt.Errorf("读取文件失败: %w", err)
    }
    
    var result interface{}
    if err := json.Unmarshal(data, &result); err != nil {
        return defaultVal, fmt.Errorf("解析JSON失败: %w", err)
    }
    
    return result, nil
}

// SaveJSONFile 保存数据到JSON文件
func SaveJSONFile(filePath string, data interface{}) error {
    // 确保目录存在
    dir := filepath.Dir(filePath)
    if err := os.MkdirAll(dir, 0755); err != nil {
        return fmt.Errorf("创建目录失败: %w", err)
    }
    
    jsonData, err := json.MarshalIndent(data, "", "  ")
    if err != nil {
        return fmt.Errorf("序列化JSON失败: %w", err)
    }
    
    if err := os.WriteFile(filePath, jsonData, 0644); err != nil {
        return fmt.Errorf("写入文件失败: %w", err)
    }
    
    return nil
}

// CheckFileExists 检查文件是否存在
func CheckFileExists(filePath string) bool {
    info, err := os.Stat(filePath)
    if os.IsNotExist(err) {
        return false
    }
    return !info.IsDir()
}

// CheckDirExists 检查目录是否存在
func CheckDirExists(dirPath string) bool {
    info, err := os.Stat(dirPath)
    if os.IsNotExist(err) {
        return false
    }
    return info.IsDir()
}

// EnsureDirExists 确保目录存在，如果不存在则创建
func EnsureDirExists(dirPath string) error {
    if dirPath == "" {
        return nil // 空路径视为可选
    }
    
    if !CheckDirExists(dirPath) {
        return os.MkdirAll(dirPath, 0755)
    }
    
    return nil
}

// GetStringValue 从map中获取字符串值，如果不存在或类型不匹配则返回默认值
func GetStringValue(m map[string]interface{}, key string, defaultVal string) string {
    if val, ok := m[key]; ok {
        if str, ok := val.(string); ok {
            return str
        }
    }
    return defaultVal
}

// GetBoolValue 从map中获取布尔值，如果不存在或类型不匹配则返回默认值
func GetBoolValue(m map[string]interface{}, key string, defaultVal bool) bool {
    if val, ok := m[key]; ok {
        if b, ok := val.(bool); ok {
            return b
        }
    }
    return defaultVal
}

// GetFloat64Value 从map中获取浮点值，如果不存在或类型不匹配则返回默认值
func GetFloat64Value(m map[string]interface{}, key string, defaultVal float64) float64 {
    if val, ok := m[key]; ok {
        switch v := val.(type) {
        case float64:
            return v
        case int:
            return float64(v)
        case int64:
            return float64(v)
        }
    }
    return defaultVal
}