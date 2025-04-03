package audio

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/stretchr/testify/assert"
)

// TestNewBatchProcessor 测试批处理器的创建
func TestNewBatchProcessor(t *testing.T) {
	config := models.NewDefaultConfig()
	
	// 创建测试目录
	mediaDir, err := os.MkdirTemp("", "batch_test_media")
	assert.NoError(t, err)
	defer os.RemoveAll(mediaDir)
	
	outputDir, err := os.MkdirTemp("", "batch_test_output")
	assert.NoError(t, err)
	defer os.RemoveAll(outputDir)
	
	tempDir, err := os.MkdirTemp("", "batch_test_temp")
	assert.NoError(t, err)
	defer os.RemoveAll(tempDir)
	
	// 创建批处理器
	processor := NewBatchProcessor(mediaDir, outputDir, tempDir, nil, config)
	
	// 验证属性
	assert.NotNil(t, processor)
	assert.Equal(t, mediaDir, processor.MediaDir)
	assert.Equal(t, outputDir, processor.OutputDir)
	assert.Equal(t, tempDir, processor.TempDir)
	assert.NotNil(t, processor.Extractor)
	assert.Equal(t, 4, processor.MaxConcurrency)  // 默认值
}

// TestScanMediaDirectory 测试媒体目录扫描
func TestScanMediaDirectory(t *testing.T) {
	config := models.NewDefaultConfig()
	
	// 创建测试目录
	mediaDir, err := os.MkdirTemp("", "scan_test_media")
	assert.NoError(t, err)
	defer os.RemoveAll(mediaDir)
	
	// 创建测试文件
	supportedFormats := []string{
		"video.mp4", "movie.mkv", "clip.avi", "audio.mp3", "sound.wav",
	}
	
	for _, filename := range supportedFormats {
		filePath := filepath.Join(mediaDir, filename)
		_, err := os.Create(filePath)
		assert.NoError(t, err)
	}
	
	// 创建不支持的格式
	_, err = os.Create(filepath.Join(mediaDir, "document.pdf"))
	assert.NoError(t, err)
	
	// 创建子目录
	subDir := filepath.Join(mediaDir, "subdir")
	err = os.Mkdir(subDir, 0755)
	assert.NoError(t, err)
	
	// 创建批处理器
	processor := NewBatchProcessor(mediaDir, "output", "temp", nil, config)
	
	// 扫描目录
	files, err := processor.scanMediaDirectory()
	assert.NoError(t, err)
	
	// 验证结果 - 应该只找到5个支持的文件
	assert.Equal(t, 5, len(files))
	
	// 验证所有文件都在列表中
	foundFiles := make(map[string]bool)
	for _, file := range files {
		foundFiles[filepath.Base(file)] = true
	}
	
	for _, format := range supportedFormats {
		assert.True(t, foundFiles[format], "应该找到文件: "+format)
	}
	
	// 确认不支持的格式没有被包含
	assert.False(t, foundFiles["document.pdf"])
}

// TestBatchProgressCallback 测试进度回调
func TestBatchProgressCallback(t *testing.T) {
	callbackCalled := false
	
	callback := func(current, total int, filename string, result *BatchResult) {
		callbackCalled = true
		
		assert.GreaterOrEqual(t, current, 1)
		assert.GreaterOrEqual(t, total, current)
		assert.NotEmpty(t, filename)
		
		// 如果result不为nil，验证其值
		if result != nil {
			assert.NotEmpty(t, result.FilePath)
		}
	}
	
	// 手动调用回调测试
	callback(1, 5, "test.mp4", nil)
	assert.True(t, callbackCalled)
	
	// 重置并测试带结果的调用
	callbackCalled = false
	result := BatchResult{
		FilePath: "test.mp4",
		Success: true,
		OutputPath: "test.mp3",
	}
	
	callback(2, 5, "test.mp4", &result)
	assert.True(t, callbackCalled)
}
