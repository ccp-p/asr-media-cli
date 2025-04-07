package models

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/sirupsen/logrus"
)

// Config 表示应用程序的配置
type Config struct {
    MediaFolder       string  `json:"media_folder"`        // 媒体文件所在文件夹
    OutputFolder      string  `json:"output_folder"`       // 输出结果文件夹
    MaxRetries        int     `json:"max_retries"`         // 最大重试次数
    MaxWorkers        int     `json:"max_workers"`         // 线程池工作线程数
    UseJianyingFirst  bool    `json:"use_jianying_first"`  // 是否优先使用剪映ASR
    UseKuaishou       bool    `json:"use_kuaishou"`        // 是否使用快手ASR
    UseBcut           bool    `json:"use_bcut"`            // 是否使用B站ASR
    FormatText        bool    `json:"format_text"`         // 是否格式化输出文本
    IncludeTimestamps bool    `json:"include_timestamps"`  // 在格式化文本中包含时间戳
    ShowProgress      bool    `json:"show_progress"`       // 显示进度条
    ProcessVideo      bool    `json:"process_video"`       // 处理视频文件
    ExtractAudioOnly  bool    `json:"extract_audio_only"`  // 仅提取音频而不处理成文本
    WatchMode         bool    `json:"watch_mode"`          // 是否启用监听模式
    SegmentLength     int     `json:"segment_length"`      // 音频片段长度（秒）
    MaxSegmentLength  int     `json:"max_segment_length"`  // 最大段落长度
    MinSegmentLength  int     `json:"min_segment_length"`  // 最小段落长度
    RetryDelay        float64 `json:"retry_delay"`         // 重试延迟（秒）
    TempDir           string  `json:"temp_dir"`            // 临时目录
    LogLevel          string  `json:"log_level"`           // 日志级别
    LogFile           string  `json:"log_file"`            // 日志文件
    MaxPartTime       int     `json:"max_part_time"`       // 最大部分时间（分钟）
    ExportSRT         bool    `json:"export_srt"`          // 是否导出SRT字幕文件
    // asr-service
    ASRService string `json:"asr_service"` // ASR服务名称 ASR服务选择 (kuaishou, bcut, auto)
}

// ConfigValidationError 表示配置验证错误
type ConfigValidationError struct {
    Field   string
    Message string
}

func (e ConfigValidationError) Error() string {
    msg := fmt.Sprintf("配置验证错误: %s - %s", e.Field, e.Message)
    logrus.Error(msg)  // 记录日志
    return msg         // 返回错误信息
}

// NewDefaultConfig 创建默认配置
func NewDefaultConfig() *Config {
    return &Config{
        MediaFolder:       "D:\\download",
        OutputFolder:      "D:\\download\\dest",
        MaxRetries:        3,
        MaxWorkers:        8,
        UseJianyingFirst:  true,
        UseKuaishou:       true,
        UseBcut:           true,
        FormatText:        true,
        IncludeTimestamps: true,
        ShowProgress:      true,
        ProcessVideo:      true,
        ExtractAudioOnly:  false,
        WatchMode:         true,
        SegmentLength:     30,
        MaxSegmentLength:  2000,
        MinSegmentLength:  10,
        RetryDelay:        1.0,
        TempDir:           "",
        LogLevel:          "INFO",
        LogFile:           "",
        MaxPartTime:       20,
        ExportSRT:         true,
        ASRService:       "auto",
    }
}

// Validate 验证配置是否有效
func (c *Config) Validate() error {
    // 验证文件夹路径
    if err := ensureDirExists(c.MediaFolder); err != nil {
        return &ConfigValidationError{"MediaFolder", err.Error()}
    }

    if err := ensureDirExists(c.OutputFolder); err != nil {
        return &ConfigValidationError{"OutputFolder", err.Error()}
    }

    // 验证数值范围
    if c.MaxRetries < 1 || c.MaxRetries > 10 {
        return &ConfigValidationError{"MaxRetries", "必须在1-10之间"}
    }

    if c.MaxWorkers < 1 || c.MaxWorkers > 16 {
        return &ConfigValidationError{"MaxWorkers", "必须在1-16之间"}
    }

    if c.SegmentLength < 10 || c.SegmentLength > 300 {
        return &ConfigValidationError{"SegmentLength", "必须在10-300秒之间"}
    }

    if c.MaxSegmentLength < 100 || c.MaxSegmentLength > 5000 {
        return &ConfigValidationError{"MaxSegmentLength", "必须在100-5000之间"}
    }

    if c.MinSegmentLength < 5 || c.MinSegmentLength > 100 {
        return &ConfigValidationError{"MinSegmentLength", "必须在5-100之间"}
    }

    if c.RetryDelay < 0.1 || c.RetryDelay > 10.0 {
        return &ConfigValidationError{"RetryDelay", "必须在0.1-10.0秒之间"}
    }

    return nil
}

// LoadFromFile 从文件加载配置
func (c *Config) LoadFromFile(path string) error {
    data, err := os.ReadFile(path)
    if err != nil {
        logrus.Errorf("读取配置文件失败: %v", err)
        return err
    }

    err = json.Unmarshal(data, c)
    if err != nil {
        logrus.Errorf("解析配置文件失败: %v", err)
        return err
    }

    if err := c.Validate(); err != nil {
        logrus.Errorf("配置验证失败: %v", err)
        return err
    }

    return nil
}

// SaveToFile 保存配置到文件
func (c *Config) SaveToFile(path string) error {
    // 确保目录存在
    dir := filepath.Dir(path)
    if err := os.MkdirAll(dir, 0755); err != nil {
        logrus.Errorf("创建目录失败: %v", err)
        return err
    }

    data, err := json.MarshalIndent(c, "", "  ")
    if err != nil {
        logrus.Errorf("序列化配置失败: %v", err)
        return err
    }

    err = os.WriteFile(path, data, 0644)
    if err != nil {
        logrus.Errorf("写入配置文件失败: %v", err)
        return err
    }

    return nil
}

// Update 批量更新配置
func (c *Config) Update(updates map[string]interface{}) error {
    // 创建临时配置并保存当前配置（用于回滚）
    tempConfig := *c

    // 将更新序列化为JSON再反序列化到结构体中
    // 这种方式处理map到struct的转换较为方便
    updateBytes, err := json.Marshal(updates)
    if err != nil {
        logrus.Errorf("序列化更新数据失败: %v", err)
        return err
    }

    err = json.Unmarshal(updateBytes, c)
    if err != nil {
        // 回滚配置
        *c = tempConfig
        logrus.Errorf("应用配置更新失败: %v", err)
        return err
    }

    // 验证配置
    if err := c.Validate(); err != nil {
        // 回滚配置
        *c = tempConfig
        logrus.Errorf("配置验证失败: %v", err)
        return err
    }

    return nil
}

// Reset 重置为默认配置
func (c *Config) Reset() {
    defaultConfig := NewDefaultConfig()
    *c = *defaultConfig
}

// PrintConfig 打印当前配置
func (c *Config) PrintConfig() {
    logrus.Info("\n当前配置:")
    bytes, err := json.MarshalIndent(c, "", "  ")
    if err != nil {
        logrus.Errorf("序列化配置失败: %v", err)
        return
    }
    logrus.Info(string(bytes))
}

// 确保目录存在，如果不存在则创建
func ensureDirExists(path string) error {
    if path == "" {
        return nil // 空路径视为可选
    }

    if _, err := os.Stat(path); os.IsNotExist(err) {
        return os.MkdirAll(path, 0755)
    }

    return nil
}