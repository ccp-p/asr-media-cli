package utils

import (
	"os"
	"testing"

	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/assert"
)

func TestInitLogger(t *testing.T) {
	// 测试控制台日志
	err := InitLogger(LogLevelNormal, "")
	assert.NoError(t, err)
	assert.Equal(t, logrus.InfoLevel, Log.GetLevel())
	
	// 测试文件日志
	tempLogFile := "./test.log"
	defer os.Remove(tempLogFile) // 测试后清理
	
	err = InitLogger(LogLevelVerbose, tempLogFile)
	assert.NoError(t, err)
	assert.Equal(t, logrus.DebugLevel, Log.GetLevel())
	
	// 验证日志文件是否创建
	_, err = os.Stat(tempLogFile)
	assert.NoError(t, err)
}

func TestLogLevels(t *testing.T) {
	// 重定向日志输出以测试
	tempLogFile := "./level_test.log"
	defer os.Remove(tempLogFile)
	
	// 初始化日志到文件
	err := InitLogger(LogLevelVerbose, tempLogFile)
	assert.NoError(t, err)
	
	// 记录不同级别的日志
	Debug("Debug message")
	Info("Info message")
	Warn("Warning message")
	Error("Error message")
	
	// 这里我们只测试是否有错误发生
	// 在实际情况下，我们可能需要读取日志文件内容进行验证
	// 但这会使测试变得更复杂
}

func TestWithFieldLogging(t *testing.T) {
	// 设置日志
	err := InitLogger(LogLevelNormal, "")
	assert.NoError(t, err)
	
	// 测试WithField和WithFields
	WithField("key", "value").Info("Test with field")
	WithFields(logrus.Fields{
		"key1": "value1",
		"key2": "value2",
	}).Info("Test with fields")
	
	// 同样，这里只测试是否能正常执行，不验证输出内容
}
