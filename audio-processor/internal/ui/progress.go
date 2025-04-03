package ui

import (
	"fmt"
	"strings"
	"time"

	"github.com/fatih/color"
)

// ProgressBar 进度条结构
type ProgressBar struct {
	Total      int       // 总步数
	Current    int       // 当前进度
	Prefix     string    // 前缀
	Suffix     string    // 后缀
	Width      int       // 进度条宽度
	FillChar   string    // 填充字符
	EmptyChar  string    // 空白字符
	StartTime  time.Time // 开始时间
	LastUpdate time.Time // 上次更新时间
}

// NewProgressBar 创建新的进度条
func NewProgressBar(total int, prefix string, suffix string) *ProgressBar {
	return &ProgressBar{
		Total:      total,
		Current:    0,
		Prefix:     prefix,
		Suffix:     suffix,
		Width:      30,
		FillChar:   "█",
		EmptyChar:  "░",
		StartTime:  time.Now(),
		LastUpdate: time.Now(),
	}
}

// Update 更新进度
func (p *ProgressBar) Update(current int, suffix string) {
	if current < 0 {
		return
	}
	
	if current > p.Total {
		current = p.Total
	}
	
	p.Current = current
	
	if suffix != "" {
		p.Suffix = suffix
	}
	
	p.LastUpdate = time.Now()
	p.draw()
}

// Increment 增加进度
func (p *ProgressBar) Increment(suffix string) {
	p.Update(p.Current+1, suffix)
}

// Complete 完成进度条
func (p *ProgressBar) Complete(suffix string) {
	p.Update(p.Total, suffix)
	fmt.Println() // 添加换行
}

// 绘制进度条
func (p *ProgressBar) draw() {
	percent := float64(p.Current) / float64(p.Total)
	filled := int(percent * float64(p.Width))
	
	// 确保filled在有效范围内
	if filled > p.Width {
		filled = p.Width
	}
	
	// 构建进度条
	bar := strings.Repeat(p.FillChar, filled) + strings.Repeat(p.EmptyChar, p.Width-filled)
	
	// 计算经过的时间
	elapsed := time.Since(p.StartTime)
	
	// 估计剩余时间
	var remaining time.Duration
	if p.Current > 0 {
		remaining = time.Duration(float64(elapsed) / percent * (1 - percent))
	}
	
	// 格式化时间
	elapsedStr := formatDuration(elapsed)
	remainingStr := formatDuration(remaining)
	
	// 构建完整进度条
	progressLine := fmt.Sprintf("\r%s [%s] %3.0f%% | %d/%d | %s<%s | %s", 
		p.Prefix, bar, percent*100, p.Current, p.Total, elapsedStr, remainingStr, p.Suffix)
	
	// 打印进度
	fmt.Print(color.CyanString(progressLine))
}

// 格式化持续时间为 MM:SS 格式
func formatDuration(d time.Duration) string {
	minutes := int(d.Minutes())
	seconds := int(d.Seconds()) % 60
	return fmt.Sprintf("%02d:%02d", minutes, seconds)
}
// String 返回进度条的字符串表示
func (pb *ProgressBar) String() string {
    percent := float64(pb.Current) / float64(pb.Total) * 100
    bar := renderProgressBar(pb.Current, pb.Total, 30)
    
    // 注意这里使用 %% 来输出真实的百分号
    return fmt.Sprintf("%s %s %3.0f%% | %d/%d", 
        pb.Prefix, 
        bar, 
        percent, 
        pb.Current, 
        pb.Total)
}
func renderProgressBar(current, total, width int) string {
    percent := float64(current) / float64(total)
    filled := int(percent * float64(width))
    
    bar := "["
    for i := 0; i < width; i++ {
        if i < filled {
            bar += "█"
        } else {
            bar += "░"
        }
    }
    bar += "]"
    
    return bar
}