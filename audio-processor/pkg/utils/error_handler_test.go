package utils

import (
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNewErrorHandler(t *testing.T) {
	handler := NewErrorHandler(3, 0.1)
	assert.Equal(t, 3, handler.MaxRetries)
	assert.Equal(t, 0.1, handler.RetryDelay)
	assert.NotNil(t, handler.ErrorStats)
}

func TestRetry(t *testing.T) {
	// 初始化日志
	InitLogger(LogLevelNormal, "")
	
	handler := NewErrorHandler(3, 0.01) // 使用很小的延迟以加速测试
	
	// 测试成功的情况
	callCount := 0
	err := handler.Retry("test_success", func() error {
		callCount++
		return nil
	})
	
	assert.NoError(t, err)
	assert.Equal(t, 1, callCount) // 应该只调用一次就成功
	
	// 测试失败后重试直到成功的情况
	callCount = 0
	err = handler.Retry("test_retry_success", func() error {
		callCount++
		if callCount < 2 {
			return errors.New("预期错误")
		}
		return nil
	})
	
	assert.NoError(t, err)
	assert.Equal(t, 2, callCount) // 应该在第二次调用时成功
	
	// 测试总是失败的情况
	callCount = 0
	testErr := errors.New("总是失败")
	err = handler.Retry("test_always_fail", func() error {
		callCount++
		return testErr
	})
	
	assert.Error(t, err)
	assert.Equal(t, handler.MaxRetries, callCount) // 应该尝试了最大次数
	
	// 验证错误统计
	stats := handler.GetErrorStats()
	assert.Equal(t, 3, len(stats)) // 应该有3个操作
	assert.Equal(t, 1, stats["test_retry_success"]["预期错误"])
	assert.Equal(t, handler.MaxRetries, stats["test_always_fail"]["总是失败"])
}

func TestSafeExecute(t *testing.T) {
	// 初始化日志
	InitLogger(LogLevelNormal, "")
	
	handler := NewErrorHandler(3, 0.01)
	
	// 测试成功执行且不需要清理
	executed := false
	cleaned := false
	
	err := handler.SafeExecute("test_safe_success", func() error {
		executed = true
		return nil
	}, func() {
		cleaned = true
	})
	
	assert.NoError(t, err)
	assert.True(t, executed)
	assert.False(t, cleaned) // 成功执行不应该调用清理函数
	
	// 测试失败执行并需要清理
	executed = false
	cleaned = false
	testErr := errors.New("预期错误")
	
	err = handler.SafeExecute("test_safe_fail", func() error {
		executed = true
		return testErr
	}, func() {
		cleaned = true
	})
	
	assert.Error(t, err)
	assert.True(t, executed)
	assert.True(t, cleaned) // 失败执行应该调用清理函数
	
	// 验证错误统计
	stats := handler.GetErrorStats()
	assert.Equal(t, 1, stats["test_safe_fail"]["预期错误"])
}

func TestErrorStats(t *testing.T) {
	// 初始化日志
	InitLogger(LogLevelNormal, "")
	
	handler := NewErrorHandler(3, 0.01)
	
	// 产生一些错误统计
	handler.updateErrorStats("op1", "err1")
	handler.updateErrorStats("op1", "err1") // 重复错误
	handler.updateErrorStats("op1", "err2") // 同一操作不同错误
	handler.updateErrorStats("op2", "err3") // 不同操作
	
	// 验证统计
	stats := handler.GetErrorStats()
	assert.Equal(t, 2, len(stats))          // 2个操作
	assert.Equal(t, 2, stats["op1"]["err1"]) // op1的err1出现2次
	assert.Equal(t, 1, stats["op1"]["err2"]) // op1的err2出现1次
	assert.Equal(t, 1, stats["op2"]["err3"]) // op2的err3出现1次
	
	// 测试打印错误统计
	handler.PrintErrorStats() // 这仅测试方法是否正常运行
}
