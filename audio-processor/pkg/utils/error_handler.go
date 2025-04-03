package utils

import (
	"fmt"
	"time"
)

// AudioToolsError 是音频工具错误的基础类型
type AudioToolsError struct {
	Message string
	Cause   error
}

// Error 实现error接口
func (e *AudioToolsError) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("%s: %s", e.Message, e.Cause.Error())
	}
	return e.Message
}

// Unwrap 支持error chain
func (e *AudioToolsError) Unwrap() error {
	return e.Cause
}

// NewError 创建一个新的AudioToolsError
func NewError(message string, cause error) error {
	return &AudioToolsError{
		Message: message,
		Cause:   cause,
	}
}

// ErrorHandler 处理错误和重试
type ErrorHandler struct {
	MaxRetries int
	RetryDelay float64
	ErrorStats map[string]map[string]int // 操作 -> 错误信息 -> 计数
}

// NewErrorHandler 创建新的错误处理器
func NewErrorHandler(maxRetries int, retryDelay float64) *ErrorHandler {
	return &ErrorHandler{
		MaxRetries: maxRetries,
		RetryDelay: retryDelay,
		ErrorStats: make(map[string]map[string]int),
	}
}

// Retry 执行函数并在失败时重试
func (h *ErrorHandler) Retry(operation string, fn func() error) error {
	var lastErr error
	
	for attempt := 0; attempt < h.MaxRetries; attempt++ {
		err := fn()
		if err == nil {
			return nil // 成功执行
		}
		
		lastErr = err
		h.updateErrorStats(operation, err.Error())
		
		if attempt < h.MaxRetries-1 {
			delay := h.RetryDelay * float64(attempt+1)
			Warn("操作 %s 失败 (尝试 %d/%d): %s", operation, attempt+1, h.MaxRetries, err)
			Warn("等待 %.1f 秒后重试...", delay)
			time.Sleep(time.Duration(delay * float64(time.Second)))
		}
	}
	
	return NewError(fmt.Sprintf("操作 %s 重试 %d 次后仍然失败", operation, h.MaxRetries), lastErr)
}

// SafeExecute 安全地执行函数，并在失败时进行清理
func (h *ErrorHandler) SafeExecute(operation string, fn func() error, cleanup func()) error {
	err := fn()
	if err != nil {
		h.updateErrorStats(operation, err.Error())
		
		// 执行清理
		if cleanup != nil {
			Info("执行清理操作...")
			cleanup()
		}
		
		return NewError(fmt.Sprintf("操作 %s 失败", operation), err)
	}
	return nil
}

// 更新错误统计
func (h *ErrorHandler) updateErrorStats(operation string, errMsg string) {
	if h.ErrorStats[operation] == nil {
		h.ErrorStats[operation] = make(map[string]int)
	}
	h.ErrorStats[operation][errMsg]++
}

// GetErrorStats 获取错误统计信息
func (h *ErrorHandler) GetErrorStats() map[string]map[string]int {
	return h.ErrorStats
}

// PrintErrorStats 打印错误统计信息
func (h *ErrorHandler) PrintErrorStats() {
	if len(h.ErrorStats) == 0 {
		Info("没有错误记录")
		return
	}
	
	Info("\n错误统计:")
	for operation, errors := range h.ErrorStats {
		Info("\n操作: %s", operation)
		for errMsg, count := range errors {
			Info("  - %s: %d次", errMsg, count)
		}
	}
}
