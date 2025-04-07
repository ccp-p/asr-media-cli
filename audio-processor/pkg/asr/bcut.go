package asr

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

const (
	// API_BASE_URL 必剪API基础URL
	API_BASE_URL = "https://member.bilibili.com/x/bcut/rubick-interface"
	
	// API_REQ_UPLOAD 申请上传API
	API_REQ_UPLOAD = API_BASE_URL + "/resource/create"
	
	// API_COMMIT_UPLOAD 提交上传API
	API_COMMIT_UPLOAD = API_BASE_URL + "/resource/create/complete"
	
	// API_CREATE_TASK 创建任务API
	API_CREATE_TASK = API_BASE_URL + "/task"
	
	// API_QUERY_RESULT 查询结果API
	API_QUERY_RESULT = API_BASE_URL + "/task/result"
)

// BcutASR 必剪语音识别实现
type BcutASR struct {
	*BaseASR
	taskID       string
	etags        []string
	inBossKey    string
	resourceID   string
	uploadID     string
	uploadURLs   []string
	perSize      int
	clips        int
	downloadURL  string
}

// NewBcutASR 创建必剪ASR实例
func NewBcutASR(audioPath string, useCache bool) (ASRService, error) {
	baseASR, err := NewBaseASR(audioPath, useCache)
	if err != nil {
		return nil, err
	}

	return &BcutASR{
		BaseASR: baseASR,
		etags:   make([]string, 0),
	}, nil
}

// GetResult 实现ASRService接口
func (b *BcutASR) GetResult(ctx context.Context, callback ProgressCallback) ([]models.DataSegment, error) {
	// 检查是否有缓存
	cacheKey := b.GetCacheKey("BcutASR")
	if b.UseCache {
		if segments, ok := b.LoadFromCache("./cache", cacheKey); ok {
			utils.Log.Info("从缓存加载必剪ASR结果")
			return segments, nil
		}
	}

	// 显示进度
	if callback != nil {
		callback(20, "正在上传...")
	}

	// 上传文件
	if err := b.upload(); err != nil {
		return nil, fmt.Errorf("必剪ASR上传失败: %w", err)
	}

	// 显示进度
	if callback != nil {
		callback(50, "提交任务...")
	}

	// 创建任务
	if err := b.createTask(); err != nil {
		return nil, fmt.Errorf("必剪ASR创建任务失败: %w", err)
	}

	// 显示进度
	if callback != nil {
		callback(60, "等待结果...")
	}

	// 查询结果
	result, err := b.queryResult(ctx, callback)
	if err != nil {
		return nil, fmt.Errorf("必剪ASR查询结果失败: %w", err)
	}

	// 处理结果
	segments := b.makeSegments(result)

	// 显示进度
	if callback != nil {
		callback(100, "识别完成")
	}

	// 缓存结果
	if b.UseCache && len(segments) > 0 {
		if err := b.SaveToCache("./cache", cacheKey, segments); err != nil {
			utils.Log.Warnf("保存必剪ASR结果到缓存失败: %v", err)
		}
	}

	return segments, nil
}

// upload 上传文件
func (b *BcutASR) upload() error {
	// 申请上传
	if err := b.requestUpload(); err != nil {
		return err
	}

	// 上传分片
	if err := b.uploadParts(); err != nil {
		return err
	}

	// 提交上传
	if err := b.commitUpload(); err != nil {
		return err
	}

	return nil
}

// requestUpload 申请上传
func (b *BcutASR) requestUpload() error {
	payload := map[string]interface{}{
		"type":             2,
		"name":             "audio.mp3",
		"size":             len(b.FileBinary),
		"ResourceFileType": "mp3",
		"model_id":         "8",
	}

	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("JSON编码失败: %w", err)
	}

	req, err := http.NewRequest("POST", API_REQ_UPLOAD, bytes.NewBuffer(jsonPayload))
	if err != nil {
		return fmt.Errorf("创建HTTP请求失败: %w", err)
	}

	req.Header.Set("User-Agent", "Bilibili/1.0.0 (https://www.bilibili.com)")
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("发送HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("读取响应失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return fmt.Errorf("解析JSON响应失败: %w", err)
	}

	// 提取响应数据
	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return fmt.Errorf("响应格式错误")
	}

	b.inBossKey = data["in_boss_key"].(string)
	b.resourceID = data["resource_id"].(string)
	b.uploadID = data["upload_id"].(string)
	b.perSize = int(data["per_size"].(float64))
	
	uploadURLsIface := data["upload_urls"].([]interface{})
	b.uploadURLs = make([]string, len(uploadURLsIface))
	for i, url := range uploadURLsIface {
		b.uploadURLs[i] = url.(string)
	}
	
	b.clips = len(b.uploadURLs)

	utils.Log.Infof("申请上传成功, 总计大小%dKB, %d分片, 分片大小%dKB: %s", 
		len(b.FileBinary)/1024, b.clips, b.perSize/1024, b.inBossKey)

	return nil
}

// uploadParts 上传分片
func (b *BcutASR) uploadParts() error {
	b.etags = make([]string, b.clips)
	
	for i := 0; i < b.clips; i++ {
		startRange := i * b.perSize
		endRange := (i + 1) * b.perSize
		if endRange > len(b.FileBinary) {
			endRange = len(b.FileBinary)
		}
		
		utils.Log.Infof("开始上传分片%d: %d-%d", i, startRange, endRange)
		
		req, err := http.NewRequest("PUT", b.uploadURLs[i], bytes.NewBuffer(b.FileBinary[startRange:endRange]))
		if err != nil {
			return fmt.Errorf("创建HTTP请求失败: %w", err)
		}
		
		req.Header.Set("User-Agent", "Bilibili/1.0.0 (https://www.bilibili.com)")
		req.Header.Set("Content-Type", "application/octet-stream")
		
		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			return fmt.Errorf("发送HTTP请求失败: %w", err)
		}
		
		etag := resp.Header.Get("Etag")
		if etag == "" {
			// 如果没有Etag，尝试从响应体获取
			body, _ := ioutil.ReadAll(resp.Body)
			var result map[string]interface{}
			if json.Unmarshal(body, &result) == nil {
				if etagVal, ok := result["etag"].(string); ok {
					etag = etagVal
				}
			}
		}
		
		resp.Body.Close()
		
		if etag == "" {
			return fmt.Errorf("分片%d上传失败: 未获取到Etag", i)
		}
		
		b.etags[i] = etag
		utils.Log.Infof("分片%d上传成功: %s", i, etag)
	}
	
	return nil
}

// commitUpload 提交上传
func (b *BcutASR) commitUpload() error {
	payload := map[string]interface{}{
		"InBossKey":  b.inBossKey,
		"ResourceId": b.resourceID,
		"Etags":      b.buildEtags(),
		"UploadId":   b.uploadID,
		"model_id":   "8",
	}

	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("JSON编码失败: %w", err)
	}

	req, err := http.NewRequest("POST", API_COMMIT_UPLOAD, bytes.NewBuffer(jsonPayload))
	if err != nil {
		return fmt.Errorf("创建HTTP请求失败: %w", err)
	}

	req.Header.Set("User-Agent", "Bilibili/1.0.0 (https://www.bilibili.com)")
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("发送HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("读取响应失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return fmt.Errorf("解析JSON响应失败: %w", err)
	}

	// 提取下载URL
	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return fmt.Errorf("响应格式错误")
	}

	b.downloadURL = data["download_url"].(string)
	utils.Log.Infof("提交成功，获取下载URL: %s", b.downloadURL)

	return nil
}

// buildEtags 构建Etags字符串
func (b *BcutASR) buildEtags() string {
	etagsStr := ""
	for i, etag := range b.etags {
		if i > 0 {
			etagsStr += ","
		}
		etagsStr += etag
	}
	return etagsStr
}

// createTask 创建任务
func (b *BcutASR) createTask() error {
	payload := map[string]interface{}{
		"resource": b.downloadURL,
		"model_id": "8",
	}

	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("JSON编码失败: %w", err)
	}

	req, err := http.NewRequest("POST", API_CREATE_TASK, bytes.NewBuffer(jsonPayload))
	if err != nil {
		return fmt.Errorf("创建HTTP请求失败: %w", err)
	}

	req.Header.Set("User-Agent", "Bilibili/1.0.0 (https://www.bilibili.com)")
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("发送HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("读取响应失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return fmt.Errorf("解析JSON响应失败: %w", err)
	}

	// 提取任务ID
	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return fmt.Errorf("响应格式错误")
	}

	b.taskID = data["task_id"].(string)
	utils.Log.Infof("任务已创建: %s", b.taskID)

	return nil
}

// queryResult 查询结果
func (b *BcutASR) queryResult(ctx context.Context, callback ProgressCallback) (map[string]interface{}, error) {
	client := &http.Client{}
	
	// 轮询检查任务状态
	for i := 0; i < 500; i++ {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
			// 继续执行
		}

		url := fmt.Sprintf("%s?model_id=%s&task_id=%s", API_QUERY_RESULT, "7", b.taskID)
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			return nil, fmt.Errorf("创建HTTP请求失败: %w", err)
		}

		req.Header.Set("User-Agent", "Bilibili/1.0.0 (https://www.bilibili.com)")
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			return nil, fmt.Errorf("发送HTTP请求失败: %w", err)
		}

		body, err := ioutil.ReadAll(resp.Body)
		resp.Body.Close()
		
		if err != nil {
			return nil, fmt.Errorf("读取响应失败: %w", err)
		}

		var result map[string]interface{}
		if err := json.Unmarshal(body, &result); err != nil {
			return nil, fmt.Errorf("解析JSON响应失败: %w", err)
		}

		// 提取任务状态
		data, ok := result["data"].(map[string]interface{})
		if !ok {
			return nil, fmt.Errorf("响应格式错误")
		}

		state, _ := data["state"].(float64)
		if state == 4 { // 任务完成
			resultStr, _ := data["result"].(string)
			var resultData map[string]interface{}
			if err := json.Unmarshal([]byte(resultStr), &resultData); err != nil {
				return nil, fmt.Errorf("解析结果失败: %w", err)
			}
			return resultData, nil
		}

		// 更新进度
		if callback != nil && i%10 == 0 {
			progress := 60 + int(float64(i)/500.0*39)
			if progress > 99 {
				progress = 99
			}
			callback(progress, fmt.Sprintf("处理中 %d/500...", i))
		}

		// 等待一秒后再次查询
		time.Sleep(time.Second)
	}

	return nil, fmt.Errorf("任务超时未完成")
}

// makeSegments 处理识别结果
func (b *BcutASR) makeSegments(result map[string]interface{}) []models.DataSegment {
	segments := []models.DataSegment{}

	utterances, ok := result["utterances"].([]interface{})
	if !ok {
		utils.Log.Warnf("解析B站ASR结果失败: 未找到utterances数组")
		return segments
	}

	for _, u := range utterances {
		utterance, ok := u.(map[string]interface{})
		if !ok {
			continue
		}

		text, _ := utterance["transcript"].(string)
        startTimeRaw, _ := utterance["start_time"].(float64)
        endTimeRaw, _ := utterance["end_time"].(float64)

        // 转换为秒，基于实际测试结果的校正公式
        // 经验公式：API时间值/1000 + 偏移量(0.105秒)
        startTime := startTimeRaw/1000.0 + 0.105
        endTime := endTimeRaw/1000.0 + 0.105

		segments = append(segments, models.DataSegment{
			Text:      text,
			StartTime: startTime,
			EndTime:   endTime,
		})
	}

	return segments
}
