package asr

import (
	"fmt"
	"hash/crc32"
	"io/ioutil"
	"os"
	"path/filepath"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// BaseASR 提供基础ASR功能的结构体
type BaseASR struct {
	AudioPath  string // 音频文件路径
	FileBinary []byte // 文件二进制内容
	CRC32      uint32 // CRC32校验值
	CRC32Hex   string // 文件CRC32校验和（十六进制）
	UseCache   bool   // 是否使用缓存
}

// NewBaseASR 创建一个新的BaseASR实例
func NewBaseASR(audioPath string, useCache bool) (*BaseASR, error) {
	baseASR := &BaseASR{
		AudioPath: audioPath,
		UseCache:  useCache,
	}

	if err := baseASR.loadFile(); err != nil {
		return nil, err
	}

	baseASR.calculateCRC32()
	return baseASR, nil
}

// loadFile 加载音频文件到内存
func (b *BaseASR) loadFile() error {
	// 判断是否是二进制数据或文件路径
	if _, err := os.Stat(b.AudioPath); err == nil {
		// 是文件路径
		utils.Log.Infof("从文件读取音频数据: %s", b.AudioPath)
		b.FileBinary, err = ioutil.ReadFile(b.AudioPath)
		if err != nil {
			return fmt.Errorf("读取音频文件失败: %w", err)
		}
	} else {
		// 如果不是有效路径，可能是直接传递了二进制数据（在实际应用中需要更好的处理）
		return fmt.Errorf("无效的音频路径: %s", b.AudioPath)
	}

	return nil
}

// calculateCRC32 计算文件的CRC32校验和
func (b *BaseASR) calculateCRC32() {
	b.CRC32 = crc32.ChecksumIEEE(b.FileBinary)
	b.CRC32Hex = fmt.Sprintf("%08x", b.CRC32)
	utils.Log.Debugf("计算的CRC32校验和: %s", b.CRC32Hex)
}

// GetCacheKey 获取缓存键名
func (b *BaseASR) GetCacheKey(prefix string) string {
	return fmt.Sprintf("%s-%s", prefix, b.CRC32Hex)
}

// LoadFromCache 从缓存加载识别结果
func (b *BaseASR) LoadFromCache(cacheDir, cacheKey string) ([]models.DataSegment, bool) {
	if !b.UseCache {
		return nil, false
	}

	cacheFilePath := filepath.Join(cacheDir, cacheKey)
	if _, err := os.Stat(cacheFilePath); os.IsNotExist(err) {
		utils.Log.Debugf("缓存文件不存在: %s", cacheFilePath)
		return nil, false
	}

	// TODO: 实现从文件加载缓存的逻辑
	// 这里简化处理，实际中需要实现JSON解析等

	return nil, false
}

// SaveToCache 保存识别结果到缓存
func (b *BaseASR) SaveToCache(cacheDir, cacheKey string, segments []models.DataSegment) error {
	if !b.UseCache {
		return nil
	}

	// 确保缓存目录存在
	if err := os.MkdirAll(cacheDir, 0755); err != nil {
		return fmt.Errorf("创建缓存目录失败: %w", err)
	}

	// TODO: 实现保存缓存到文件的逻辑
	// 这里简化处理，实际中需要实现JSON序列化等

	return nil
}
