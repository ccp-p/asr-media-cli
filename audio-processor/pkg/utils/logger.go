package utils

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/sirupsen/logrus"
)

// 日志级别常量
const (
	LogLevelVerbose = "VERBOSE"
	LogLevelNormal  = "INFO"
	LogLevelQuiet   = "WARN"
)

var (
	// Log 全局日志实例
	Log *logrus.Logger
	// 定义一个全局变量，用于标记是否启用了终端进度条
	terminalProgressEnabled bool
)

// InitLogger 初始化日志系统
// level: 日志级别 (VERBOSE/INFO/WARN/ERROR)
// logFile: 日志文件路径，空字符串表示仅输出到控制台
func InitLogger(level string, logFile string) error {
	// 创建logger实例
	Log = logrus.New()
	
	// 设置日志格式
	Log.SetFormatter(&logrus.TextFormatter{
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05",
	})
	
	// 设置日志输出
	if terminalProgressEnabled {
		// 如果没有指定日志文件，则创建一个临时日志文件
		if logFile == "" {
			tempDir := os.TempDir()
			logFile = filepath.Join(tempDir, "audio-processor.log")
		}
		
		// 打开日志文件
		file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err == nil {
			Log.SetOutput(file)
		}
	} else if logFile != "" {
		// 确保日志目录存在
		logDir := filepath.Dir(logFile)
		if err := os.MkdirAll(logDir, 0755); err != nil {
			return fmt.Errorf("创建日志目录失败: %w", err)
		}
		
		// 打开日志文件
		file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err != nil {
			return fmt.Errorf("打开日志文件失败: %w", err)
		}
		
		// 同时输出到文件和控制台
		mw := io.MultiWriter(os.Stdout, file)
		Log.SetOutput(mw)
	} else {
		Log.SetOutput(os.Stdout)
	}
	
	// 设置日志级别
	switch level {
	case LogLevelVerbose:
		Log.SetLevel(logrus.DebugLevel)
	case LogLevelNormal:
		Log.SetLevel(logrus.InfoLevel)
	case LogLevelQuiet:
		Log.SetLevel(logrus.WarnLevel)
	default:
		Log.SetLevel(logrus.InfoLevel)
	}
	
	return nil
}

// EnableTerminalProgress 启用终端进度条模式 - 调用此函数后日志将不再输出到终端
func EnableTerminalProgress() {
	terminalProgressEnabled = true
	// 重新初始化日志，应用设置
	currentLevel := Log.GetLevel().String()
	InitLogger(currentLevel, "")
}

// DisableTerminalProgress 禁用终端进度条模式 - 调用此函数后日志将恢复到终端输出
func DisableTerminalProgress() {
	terminalProgressEnabled = false
	// 将输出恢复到标准输出
	Log.SetOutput(os.Stdout)
}

// Debug 输出调试日志
func Debug(format string, args ...interface{}) {
	if Log != nil {
		if len(args) > 0 {
			Log.Debugf(format, args...)
		} else {
			Log.Debug(format)
		}
	}
}

// Info 输出信息日志
func Info(format string, args ...interface{}) {
	if Log != nil {
		if len(args) > 0 {
			Log.Infof(format, args...)
		} else {
			Log.Info(format)
		}
	}
}

// Warn 输出警告日志
func Warn(format string, args ...interface{}) {
	if Log != nil {
		if len(args) > 0 {
			Log.Warnf(format, args...)
		} else {
			Log.Warn(format)
		}
	}
}

// Error 输出错误日志
func Error(format string, args ...interface{}) {
	if Log != nil {
		if len(args) > 0 {
			Log.Errorf(format, args...)
		} else {
			Log.Error(format)
		}
	}
}

// Fatal 输出致命错误日志并退出
func Fatal(format string, args ...interface{}) {
	if Log != nil {
		if len(args) > 0 {
			Log.Fatalf(format, args...)
		} else {
			Log.Fatal(format)
		}
	}
}

// WithField 创建带字段的日志条目
func WithField(key string, value interface{}) *logrus.Entry {
	if Log != nil {
		return Log.WithField(key, value)
	}
	return nil
}

// WithFields 创建带多个字段的日志条目
func WithFields(fields logrus.Fields) *logrus.Entry {
	if Log != nil {
		return Log.WithFields(fields)
	}
	return nil
}
