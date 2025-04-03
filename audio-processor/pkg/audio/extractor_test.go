package audio

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/stretchr/testify/assert"
)

// TestNewAudioExtractor 测试音频提取器的创建
func TestNewAudioExtractor(t *testing.T) {
	config := models.NewDefaultConfig()
	
	// 创建临时目录
	tempDir, err := os.MkdirTemp("", "audio_extractor_test")
	assert.NoError(t, err)
	defer os.RemoveAll(tempDir)
	
	// 测试创建新的音频提取器
	extractor := NewAudioExtractor(tempDir, nil, config)
	
	assert.NotNil(t, extractor)
	assert.Equal(t, tempDir, extractor.TempSegmentsDir)
	assert.Equal(t, config.MaxWorkers, extractor.concurrencyLimit)
}

// TestSetConcurrencyLimit 测试设置并发限制
func TestSetConcurrencyLimit(t *testing.T) {
	config := models.NewDefaultConfig()
	extractor := NewAudioExtractor("test_dir", nil, config)
	
	// 测试设置有效值
	extractor.SetConcurrencyLimit(10)
	assert.Equal(t, 10, extractor.concurrencyLimit)
	
	// 测试设置无效值不会改变并发限制
	extractor.SetConcurrencyLimit(0)
	assert.Equal(t, 10, extractor.concurrencyLimit)
	
	extractor.SetConcurrencyLimit(-5)
	assert.Equal(t, 10, extractor.concurrencyLimit)
}

// TestGetSegmentIndex 测试从文件名提取片段索引
func TestGetSegmentIndex(t *testing.T) {
	// 测试有效的文件名格式
	assert.Equal(t, 0, getSegmentIndex("part001.wav"))
	assert.Equal(t, 9, getSegmentIndex("part010.wav"))
	assert.Equal(t, 99, getSegmentIndex("part100.wav"))
	
	// 测试无效的文件名格式
	assert.Equal(t, 999, getSegmentIndex("invalid_name.wav"))
	assert.Equal(t, 999, getSegmentIndex("part_001.wav"))
}

// 集成测试 - 需要ffmpeg可用
func TestExtractAudioFromVideo(t *testing.T) {
	// 跳过测试，如果环境没有配置ffmpeg
	// 在CI环境中，可以通过环境变量控制是否运行此测试
	if os.Getenv("SKIP_FFMPEG_TESTS") == "1" {
		t.Skip("跳过需要ffmpeg的测试")
	}
	
	config := models.NewDefaultConfig()
	
	// 创建临时目录
	tempDir, err := os.MkdirTemp("", "audio_extract_test")
	assert.NoError(t, err)
	defer os.RemoveAll(tempDir)
	
	// 创建临时视频文件 (这里只创建空文件，实际测试需要有效的视频文件)
	videoPath := filepath.Join(tempDir, "test_video.mp4")
	_, err = os.Create(videoPath)
	assert.NoError(t, err)
	
	// 由于没有真实的视频文件，下面的测试预期会失败
	// 实际项目中，应该准备一个小的测试视频文件
	extractor := NewAudioExtractor(tempDir, nil, config)
	audioPath, extracted, err := extractor.ExtractAudioFromVideo(videoPath, tempDir)
	
	// 这里应该失败，因为我们没有有效的视频文件
	assert.Error(t, err)
	assert.False(t, extracted)
	assert.Equal(t, "", audioPath)
}

// 模拟进度回调的函数
func TestProgressCallback(t *testing.T) {
	config := models.NewDefaultConfig()
	
	// 创建一个通道来跟踪回调是否被调用
	callbackCalled := make(chan bool, 1)
	
	progressCallback := func(current, total int, message string) {
		// 验证传入的参数
		assert.GreaterOrEqual(t, current, 0)
		assert.GreaterOrEqual(t, total, current)
		assert.NotEmpty(t, message)
		
		// 标记回调已被调用
		callbackCalled <- true
	}
	
	extractor := NewAudioExtractor("test_dir", progressCallback, config)
	
	// 手动调用回调函数来测试
	extractor.ProgressCallback(1, 10, "测试消息")
	
	// 等待回调被调用或超时
	select {
	case <-callbackCalled:
		// 回调成功调用
	case <-time.After(time.Second):
		t.Fatal("回调函数没有在预期时间内被调用")
	}
}
