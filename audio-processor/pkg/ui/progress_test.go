package ui

import (
	"bytes"
	"io"
	"os"
	"strings"
	"testing"
	"time"
)

// 捕获标准输出的辅助函数
func captureOutput(f func()) string {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	
	outC := make(chan string)
	go func() {
		var buf bytes.Buffer
		io.Copy(&buf, r)
		outC <- buf.String()
	}()
	
	f()
	
	w.Close()
	os.Stdout = old
	return <-outC
}

func TestNewProgressBar(t *testing.T) {
	// 创建新进度条
	bar := NewProgressBar(100, "测试", "初始状态")
	
	// 验证初始状态
	if bar.Total != 100 {
		t.Errorf("进度条总数不匹配: 期望 100, 实际 %d", bar.Total)
	}
	
	if bar.Current != 0 {
		t.Errorf("进度条当前值不匹配: 期望 0, 实际 %d", bar.Current)
	}
	
	if bar.Prefix != "测试" {
		t.Errorf("进度条前缀不匹配: 期望 '测试', 实际 '%s'", bar.Prefix)
	}
	
	if bar.Suffix != "初始状态" {
		t.Errorf("进度条后缀不匹配: 期望 '初始状态', 实际 '%s'", bar.Suffix)
	}
}

func TestUpdate(t *testing.T) {
	// 创建新进度条
	bar := NewProgressBar(100, "测试", "")
	
	// 更新进度条
	output := captureOutput(func() {
		bar.Update(50, "半程")
	})
	
	// 验证进度已更新
	if bar.Current != 50 {
		t.Errorf("进度条当前值不匹配: 期望 50, 实际 %d", bar.Current)
	}
	
	if bar.Suffix != "半程" {
		t.Errorf("进度条后缀不匹配: 期望 '半程', 实际 '%s'", bar.Suffix)
	}
	
	// 检查输出包含进度信息
	if len(output) == 0 {
		t.Error("进度条未产生输出")
	}
	
	// 测试负值处理
	bar.Update(-10, "")
	if bar.Current != 50 {
		t.Errorf("负值更新后进度不正确: 期望 50, 实际 %d", bar.Current)
	}
	
	// 测试超过最大值处理
	bar.Update(150, "")
	if bar.Current != 100 {
		t.Errorf("超出最大值更新后进度不正确: 期望 100, 实际 %d", bar.Current)
	}
}

func TestIncrement(t *testing.T) {
	// 创建新进度条
	bar := NewProgressBar(100, "测试", "")
	
	// 递增进度
	_ = captureOutput(func() {
		bar.Increment("递增测试")
	})
	
	// 验证进度已递增
	if bar.Current != 1 {
		t.Errorf("进度条递增后值不匹配: 期望 1, 实际 %d", bar.Current)
	}
	
	if bar.Suffix != "递增测试" {
		t.Errorf("进度条后缀不匹配: 期望 '递增测试', 实际 '%s'", bar.Suffix)
	}
	
	// 多次递增
	for i := 0; i < 5; i++ {
		_ = captureOutput(func() {
			bar.Increment("")
		})
	}
	
	if bar.Current != 6 {
		t.Errorf("多次递增后进度不正确: 期望 6, 实际 %d", bar.Current)
	}
}

func TestComplete(t *testing.T) {
	// 创建新进度条
	bar := NewProgressBar(100, "测试", "")
	
	// 更新到一半
	_ = captureOutput(func() {
		bar.Update(50, "")
	})
	
	// 完成进度条
	output := captureOutput(func() {
		bar.Complete("完成")
	})
	
	// 验证进度已完成
	if bar.Current != 100 {
		t.Errorf("进度条完成后值不匹配: 期望 100, 实际 %d", bar.Current)
	}
	
	if bar.Suffix != "完成" {
		t.Errorf("进度条后缀不匹配: 期望 '完成', 实际 '%s'", bar.Suffix)
	}
	
	// 检查输出包含换行符（完成时应添加换行）
	if len(output) == 0 || !strings.Contains(output, "\n") {
		t.Error("完成进度条时未添加换行符")
	}
}

func TestDrawWithTimers(t *testing.T) {
	// 创建新进度条
	bar := NewProgressBar(100, "测试", "")
	
	// 设置起始时间为过去
	bar.StartTime = time.Now().Add(-10 * time.Second)
	
	// 更新进度条并捕获输出
	output := captureOutput(func() {
		bar.Update(20, "")
	})
	
	// 检查输出包含时间信息
	if !strings.Contains(output, ":") {
		t.Error("进度条输出中未包含时间信息")
	}
}
