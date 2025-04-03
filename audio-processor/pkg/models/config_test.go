package models

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNewDefaultConfig(t *testing.T) {
	config := NewDefaultConfig()
	
	// 验证默认值是否正确设置
	assert.Equal(t, "./media", config.MediaFolder)
	assert.Equal(t, "./output", config.OutputFolder)
	assert.Equal(t, 3, config.MaxRetries)
	assert.Equal(t, 4, config.MaxWorkers)
	assert.True(t, config.UseJianyingFirst)
	assert.True(t, config.UseBcut)
	assert.True(t, config.FormatText)
	assert.Equal(t, 30, config.SegmentLength)
	assert.Equal(t, 20, config.MaxPartTime)
	assert.False(t, config.ExportSRT)
}

func TestConfigValidate(t *testing.T) {
	// 测试有效配置
	config := NewDefaultConfig()
	err := config.Validate()
	assert.NoError(t, err)
	
	// 测试无效的MaxRetries
	config.MaxRetries = 0
	err = config.Validate()
	assert.Error(t, err)
	configErr, ok := err.(*ConfigValidationError)
	assert.True(t, ok)
	assert.Equal(t, "MaxRetries", configErr.Field)
	
	// 恢复有效值并测试另一个字段
	config.MaxRetries = 3
	config.SegmentLength = 5 // 小于最小值10
	err = config.Validate()
	assert.Error(t, err)
	configErr, ok = err.(*ConfigValidationError)
	assert.True(t, ok)
	assert.Equal(t, "SegmentLength", configErr.Field)
}

func TestConfigSaveAndLoad(t *testing.T) {
	// 创建临时文件用于测试
	tempFile := "./test_config.json"
	defer os.Remove(tempFile) // 测试结束后清理
	
	// 创建并保存配置
	originalConfig := NewDefaultConfig()
	originalConfig.MediaFolder = "./test_media"
	originalConfig.MaxRetries = 5
	originalConfig.ExportSRT = true
	
	err := originalConfig.SaveToFile(tempFile)
	assert.NoError(t, err)
	
	// 从文件加载配置
	loadedConfig := NewDefaultConfig()
	err = loadedConfig.LoadFromFile(tempFile)
	assert.NoError(t, err)
	
	// 验证加载的配置是否与原始配置匹配
	assert.Equal(t, originalConfig.MediaFolder, loadedConfig.MediaFolder)
	assert.Equal(t, originalConfig.MaxRetries, loadedConfig.MaxRetries)
	assert.Equal(t, originalConfig.ExportSRT, loadedConfig.ExportSRT)
}

func TestConfigUpdate(t *testing.T) {
	config := NewDefaultConfig()
	
	// 有效更新
	updates := map[string]interface{}{
		"media_folder": "./updated_media",
		"max_retries":  5,
		"export_srt":   true,
	}
	
	err := config.Update(updates)
	assert.NoError(t, err)
	assert.Equal(t, "./updated_media", config.MediaFolder)
	assert.Equal(t, 5, config.MaxRetries)
	assert.True(t, config.ExportSRT)
	
	// 无效更新
	invalidUpdates := map[string]interface{}{
		"max_retries": 20, // 超出最大值10
	}
	
	err = config.Update(invalidUpdates)
	assert.Error(t, err)
	assert.Equal(t, 5, config.MaxRetries) // 应该保持原值
}

func TestConfigReset(t *testing.T) {
	config := NewDefaultConfig()
	
	// 修改配置
	config.MediaFolder = "./custom_media"
	config.MaxRetries = 5
	config.ExportSRT = true
	
	// 重置为默认值
	config.Reset()
	
	// 验证是否重置为默认值
	assert.Equal(t, "./media", config.MediaFolder)
	assert.Equal(t, 3, config.MaxRetries)
	assert.False(t, config.ExportSRT)
}
