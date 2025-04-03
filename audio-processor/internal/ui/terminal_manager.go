package ui

import (
	"fmt"
	"io"
	"os"
	"sync"
)

// TerminalManager 管理终端输出，确保进度条和消息不会混乱
type TerminalManager struct {
    mu         sync.Mutex
    msgWriter  io.Writer
    progressWriter io.Writer
}

var (
    // 全局终端管理器实例
    globalTerminalManager *TerminalManager
    once sync.Once
)

// GetTerminalManager 获取全局终端管理器实例
func GetTerminalManager() *TerminalManager {
    once.Do(func() {
        globalTerminalManager = &TerminalManager{
            msgWriter:     os.Stdout,
            progressWriter: os.Stdout,
        }
    })
    return globalTerminalManager
}

// PrintMsg 安全地打印消息
func (tm *TerminalManager) PrintMsg(format string, args ...interface{}) {
    tm.mu.Lock()
    defer tm.mu.Unlock()
    
    // 清除当前行，以防止与进度条冲突
    fmt.Fprint(tm.msgWriter, "\033[2K\r")
    fmt.Fprintf(tm.msgWriter, format+"\n", args...)
}

// UpdateProgress 安全地更新进度显示
func (tm *TerminalManager) UpdateProgress(format string, args ...interface{}) {
    tm.mu.Lock()
    defer tm.mu.Unlock()
    
    	fmt.Fprint(tm.progressWriter, "\033[2K\r")
	    // 检查是否有args参数
		if len(args) > 0 {
			// 有参数，使用格式化
			fmt.Fprintf(tm.progressWriter, format, args...)
		} else {
			// 没有参数，直接打印文本，避免%造成的问题
			fmt.Fprint(tm.progressWriter, format)
		}
}