package controller

import (
    "fmt"
    "github.com/sirupsen/logrus"
    "os"

    "github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
    "github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// ProcessorController 处理器控制器，协调各个组件工作
type ProcessorController struct {
    Config *models.Config
    // 其他字段将在后续实现...
}

// NewProcessorController 创建一个新的处理器控制器
func NewProcessorController(configFile string, configParams map[string]interface{}) (*ProcessorController, error) {
    // 初始化配置
    config := models.NewDefaultConfig()

    // 如果提供了配置文件，尝试加载
    if configFile != "" && utils.CheckFileExists(configFile) {
        if err := config.LoadFromFile(configFile); err != nil {
            return nil, fmt.Errorf("加载配置文件失败: %w", err)
        }
    }

    // 如果提供了配置参数，更新配置
    if len(configParams) > 0 {
        if err := config.Update(configParams); err != nil {
            return nil, fmt.Errorf("更新配置失败: %w", err)
        }
    }

    // 确保配置有效
    if err := config.Validate(); err != nil {
        return nil, err
    }

    // 设置日志
    setupLogging(config.LogLevel, config.LogFile)

    controller := &ProcessorController{
        Config: config,
        // 其他字段将在后续实现...
    }

    // 打印配置
    config.PrintConfig()

    return controller, nil
}

// setupLogging 设置日志配置
func setupLogging(level string, logFile string) {
    // 设置日志级别
    logLevel, err := logrus.ParseLevel(level)
    if err != nil {
        logrus.Warnf("无效的日志级别: %s，将使用默认级别 info", level)
        logLevel = logrus.InfoLevel
    }
    logrus.SetLevel(logLevel)

    // 设置日志格式
    logrus.SetFormatter(&logrus.TextFormatter{
        FullTimestamp:   true,
        TimestampFormat: "2006-01-02 15:04:05",
    })

    if logFile != "" {
        // 确保日志目录存在
        logDir := utils.EnsureDirExists(logFile)
        if logDir != nil {
            logrus.Warn("警告: 无法创建日志目录，将使用标准输出")
        } else {
            // 打开或创建日志文件
            file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
            if err != nil {
                logrus.Warnf("警告: 无法打开日志文件，将使用标准输出: %v", err)
            } else {
                logrus.SetOutput(file)
            }
        }
    }

    // 设置日志前缀
    logrus.SetFormatter(&logrus.TextFormatter{
        ForceColors:     true,
        FullTimestamp:   true,
        TimestampFormat: "2006-01-02 15:04:05",
        DisableSorting:  true,
        QuoteEmptyFields: true,
        FieldMap: logrus.FieldMap{
            logrus.FieldKeyMsg: "msg",
            logrus.FieldKeyLevel: "level",
            logrus.FieldKeyTime: "time",
        },
    })
    logrus.WithField("prefix", "[Audio-Processor]")
}
