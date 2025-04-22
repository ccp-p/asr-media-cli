package asr

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"mime/multipart"
	"net/http"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
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
func (k *KuaiShouASR) GetResult(ctx context.Context, callback ProgressCallback) ([]models.DataSegment, error) {
	instanceID := fmt.Sprintf("KuaiShouASR-%s", utils.GenerateRandomString(6))
	utils.Info("[%s] 开始处理音频: %s", instanceID, k.AudioPath)

	// 检查是否有缓存
	cacheKey := k.GetCacheKey("KuaiShouASR")
	if k.UseCache {
		if segments, ok := k.LoadFromCache("./cache", cacheKey); ok {
			utils.Info("[%s] 从缓存加载快手ASR结果", instanceID)
			if callback != nil {
				callback(100, "识别完成 (缓存)")
			}
			return segments, nil
		}
	}

	// 显示进度
	if callback != nil {
		callback(30, "提交请求中...")
	}
	utils.Info("[%s] 提交识别请求...", instanceID)

	// 提交识别请求
	result, err := k.submit(ctx)
	if err != nil {
		utils.Error("[%s] 请求失败: %v", instanceID, err)
		return nil, fmt.Errorf("快手ASR请求失败: %w", err)
	}

	// 处理结果
	utils.Info("[%s] 处理识别结果...", instanceID)
	segments := k.makeSegments(result)
	utils.Info("[%s] 处理完成, 获取 %d 段文本", instanceID, len(segments))

	// 显示进度
	if callback != nil {
		callback(100, "识别完成")
	}

	// 缓存结果
	if k.UseCache && len(segments) > 0 {
		if err := k.SaveToCache("./cache", cacheKey, segments); err != nil {
			utils.Warn("[%s] 保存快手ASR结果到缓存失败: %v", instanceID, err)
		} else {
			utils.Info("[%s] 结果已缓存", instanceID)
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
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
	req.Header.Set("Accept", "application/json, text/plain, */*")

	// 发送请求
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		utils.Error("快手ASR请求发送失败: %v", err)
		return &KuaiShouResponse{}, fmt.Errorf("发送HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	// 检查HTTP状态码
	if resp.StatusCode != http.StatusOK {
		utils.Error("快手ASR请求返回非200状态码: %d", resp.StatusCode)
		return &KuaiShouResponse{}, fmt.Errorf("HTTP请求返回错误状态码: %d", resp.StatusCode)
	}

	// 读取响应
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		utils.Error("读取响应失败: %v", err)
		return &KuaiShouResponse{}, fmt.Errorf("读取响应内容失败: %w", err)
	}

	// 输出原始响应用于调试
	utils.Debug("快手ASR原始响应: %s", string(body))

	// 检查响应是否为空
	if len(body) == 0 {
		utils.Error("快手ASR返回空响应")
		return &KuaiShouResponse{}, fmt.Errorf("接收到空响应")
	}

	// 解析JSON
	var result KuaiShouResponse
	if err := json.Unmarshal(body, &result); err != nil {
		utils.Error("解析响应JSON失败: %v, 原始数据: %s", err, string(body))
		return &KuaiShouResponse{}, fmt.Errorf("解析JSON响应失败: %w", err)
	}

	// 检查解析后的结果
	if result.Data.Text == nil {
		utils.Error("快手ASR响应中没有文本数据")
		return &KuaiShouResponse{}, fmt.Errorf("响应中没有文本数据")
	}

	utils.Info("成功解析快手ASR响应，文本段落数量: %d", len(result.Data.Text))
	return &result, nil
}

// makeSegments 处理识别结果
func (k *KuaiShouASR) makeSegments(resp *KuaiShouResponse) []models.DataSegment {
	var segments []models.DataSegment

	// 安全检查
	if resp == nil {
		utils.Error("快手ASR响应为空")
		return segments
	}

	// 检查文本数组
	if resp.Data.Text == nil {
		utils.Error("快手ASR响应中文本数组为空")
		return segments
	}

	// 提取文本段落
	for _, item := range resp.Data.Text {
		// 跳过空文本
		if item.Text == "" {
			continue
		}
		
		segments = append(segments, models.DataSegment{
			Text:      item.Text,
			StartTime: item.StartTime,
			EndTime:   item.EndTime,
		})
	}

	// 检查结果
	if len(segments) == 0 {
		utils.Warn("快手ASR没有识别出任何文本段落")
	} else {
		utils.Info("成功从快手ASR提取 %d 个文本段落", len(segments))
	}

	return segments
}
