package asr

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"mime/multipart"
	"net/http"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// KuaiShouASR 快手语音识别实现
type KuaiShouASR struct {
	*BaseASR
}

// NewKuaiShouASR 创建快手ASR实例
func NewKuaiShouASR(audioPath string, useCache bool) (*KuaiShouASR, error) {
	baseASR, err := NewBaseASR(audioPath, useCache)
	if err != nil {
		return nil, err
	}

	return &KuaiShouASR{
		BaseASR: baseASR,
	}, nil
}

// KuaiShouResponse 响应结构
type KuaiShouResponse struct {
	Data struct {
		Text []struct {
			Text      string  `json:"text"`
			StartTime float64 `json:"start_time"`
			EndTime   float64 `json:"end_time"`
		} `json:"text"`
	} `json:"data"`
}

// GetResult 实现ASRService接口
func (k *KuaiShouASR) GetResult(ctx context.Context, callback ProgressCallback) ([]DataSegment, error) {
	// 检查是否有缓存
	cacheKey := k.GetCacheKey("KuaiShouASR")
	if k.UseCache {
		if segments, ok := k.LoadFromCache("./cache", cacheKey); ok {
			utils.Log.Info("从缓存加载快手ASR结果")
			return segments, nil
		}
	}

	// 显示进度
	if callback != nil {
		callback(50, "正在识别...")
	}

	// 提交识别请求
	result, err := k.submit(ctx)
	if err != nil {
		return nil, fmt.Errorf("快手ASR请求失败: %w", err)
	}

	// 处理结果
	segments := k.makeSegments(result)

	// 显示进度
	if callback != nil {
		callback(100, "识别完成")
	}

	// 缓存结果
	if k.UseCache {
		if err := k.SaveToCache("./cache", cacheKey, segments); err != nil {
			utils.Log.Warnf("保存快手ASR结果到缓存失败: %v", err)
		}
	}

	return segments, nil
}

// submit 提交识别请求
func (k *KuaiShouASR) submit(ctx context.Context) (*KuaiShouResponse, error) {
	// 创建multipart表单
	var requestBody bytes.Buffer
	writer := multipart.NewWriter(&requestBody)

	// 添加表单字段
	err := writer.WriteField("typeId", "1")
	if err != nil {
		return nil, fmt.Errorf("写入表单字段失败: %w", err)
	}

	// 添加文件
	part, err := writer.CreateFormFile("file", "test.mp3")
	if err != nil {
		return nil, fmt.Errorf("创建表单文件失败: %w", err)
	}
	_, err = part.Write(k.FileBinary)
	if err != nil {
		return nil, fmt.Errorf("写入文件数据失败: %w", err)
	}

	err = writer.Close()
	if err != nil {
		return nil, fmt.Errorf("关闭表单写入器失败: %w", err)
	}

	// 创建请求
	req, err := http.NewRequestWithContext(ctx, "POST", "https://ai.kuaishou.com/api/effects/subtitle_generate", &requestBody)
	if err != nil {
		return nil, fmt.Errorf("创建HTTP请求失败: %w", err)
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())

	// 发送请求
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		utils.Log.Errorf("快手ASR请求发送失败: %v", err)
		return &KuaiShouResponse{}, nil
	}
	defer resp.Body.Close()

	// 读取响应
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		utils.Log.Errorf("读取响应失败: %v", err)
		return &KuaiShouResponse{}, nil
	}

	// 解析JSON
	var result KuaiShouResponse
	if err := json.Unmarshal(body, &result); err != nil {
		utils.Log.Errorf("解析响应JSON失败: %v", err)
		return &KuaiShouResponse{}, nil
	}

	return &result, nil
}

// makeSegments 处理识别结果
func (k *KuaiShouASR) makeSegments(resp *KuaiShouResponse) []DataSegment {
	var segments []DataSegment

	// 安全处理响应
	if resp != nil && resp.Data.Text != nil {
		for _, item := range resp.Data.Text {
			segments = append(segments, DataSegment{
				Text:      item.Text,
				StartTime: item.StartTime,
				EndTime:   item.EndTime,
			})
		}
	}

	return segments
}
