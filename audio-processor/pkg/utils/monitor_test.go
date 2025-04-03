package utils

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// 创建一个模拟的ProgressManager
type MockProgressManager struct {
	mock.Mock
}

func (m *MockProgressManager) CreateProgressBar(id string, total int, title string, status string) {
	m.Called(id, total, title, status)
}

func (m *MockProgressManager) UpdateProgressBar(id string, value int, status string) {
	m.Called(id, value, status)
}

func (m *MockProgressManager) CompleteProgressBar(id string, status string) {
	m.Called(id, status)
}

func (m *MockProgressManager) CloseAll(status string) {
	m.Called(status)
}

// TestNewSegmentProgressMonitor 测试监控器创建
func TestNewSegmentProgressMonitor(t *testing.T) {
	mockPM := new(MockProgressManager)
	monitor := NewSegmentProgressMonitor("testDir", mockPM)
	
	assert.NotNil(t, monitor)
	assert.Equal(t, "testDir", monitor.TempDir)
	assert.Equal(t, mockPM, monitor.ProgressManager)
	assert.NotNil(t, monitor.StopChan)
	assert.Equal(t, 2*time.Second, monitor.Interval)
}

// TestStartStopMonitor 测试启动和停止监控
func TestStartStopMonitor(t *testing.T) {
	mockPM := new(MockProgressManager)
	tempDir, err := os.MkdirTemp("", "monitor_test")
	assert.NoError(t, err)
	defer os.RemoveAll(tempDir)
	
	monitor := NewSegmentProgressMonitor(tempDir, mockPM)
	// 设置更短的间隔以加快测试
	monitor.Interval = 100 * time.Millisecond
	
	// 启动监控
	monitor.Start()
	
	// 创建一个片段目录
	segmentsDir := filepath.Join(tempDir, "segments")
	err = os.MkdirAll(segmentsDir, 0755)
	assert.NoError(t, err)
	
	// 等待一段时间，让协程运行
	time.Sleep(200 * time.Millisecond)
	
	// 停止监控
	monitor.Stop()
}

// TestCheckSegments 测试片段检查功能
func TestCheckSegments(t *testing.T) {
	// 创建测试目录
	tempDir, err := os.MkdirTemp("", "segments_test")
	assert.NoError(t, err)
	defer os.RemoveAll(tempDir)
	
	segmentsDir := filepath.Join(tempDir, "segments")
	err = os.MkdirAll(segmentsDir, 0755)
	assert.NoError(t, err)
	
	// 创建一些测试文件
	for i := 1; i <= 5; i++ {
		filename := filepath.Join(segmentsDir, filepath.Sprintf("test_part%03d.wav", i))
		_, err := os.Create(filename)
		assert.NoError(t, err)
	}
	
	// 创建一些非WAV文件
	_, err = os.Create(filepath.Join(segmentsDir, "test.txt"))
	assert.NoError(t, err)
	
	// 创建模拟的进度管理器
	mockPM := new(MockProgressManager)
	mockPM.On("UpdateProgressBar", "segments_monitor", 5, mock.Anything).Return()
	
	monitor := NewSegmentProgressMonitor(tempDir, mockPM)
	
	// 手动调用检查函数
	monitor.checkSegments()
	
	// 验证是否正确调用了更新进度条的方法
	mockPM.AssertCalled(t, "UpdateProgressBar", "segments_monitor", 5, mock.Anything)
}

// TestStartSegmentMonitoring 测试便捷功能
func TestStartSegmentMonitoring(t *testing.T) {
	mockPM := new(MockProgressManager)
	tempDir, err := os.MkdirTemp("", "start_monitor_test")
	assert.NoError(t, err)
	defer os.RemoveAll(tempDir)
	
	// 测试便捷启动函数
	stopFunc := StartSegmentMonitoring(tempDir, mockPM)
	assert.NotNil(t, stopFunc)
	
	// 调用停止函数
	stopFunc()
}
