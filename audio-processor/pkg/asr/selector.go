package asr

import (
	"context"
	"fmt"
	"math/rand"
	"os"
	"sync"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/models"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// ServiceCreator 是创建ASR服务实例的函数类型
type ServiceCreator func(audioPath string, useCache bool) (ASRService, error)

// ServiceStats 服务统计数据
type ServiceStats struct {
	SuccessCount int
	TotalCount   int
	Available    bool
}

// ASRSelector 语音服务选择器，负责在多个ASR服务之间进行负载均衡
type ASRSelector struct {
	mu              sync.RWMutex
	services        map[string]ServiceCreator   // 服务创建函数
	weights         map[string]int              // 权重
	counters        map[string]int              // 使用计数
	stats           map[string]*ServiceStats    // 统计信息
	roundRobinIndex int                         // 轮询索引
	serviceList     []string                    // 服务名称列表，用于轮询
}

// NewASRSelector 创建新的ASR服务选择器
func NewASRSelector() *ASRSelector {
	rand.Seed(time.Now().UnixNano())
	return &ASRSelector{
		services:        make(map[string]ServiceCreator),
		weights:         make(map[string]int),
		counters:        make(map[string]int),
		stats:           make(map[string]*ServiceStats),
		roundRobinIndex: 0,
		serviceList:     make([]string, 0),
	}
}

// RegisterService 注册ASR服务
func (s *ASRSelector) RegisterService(name string, creator ServiceCreator, weight int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.services[name] = creator
	s.weights[name] = weight
	s.counters[name] = 0
	s.stats[name] = &ServiceStats{
		SuccessCount: 0,
		TotalCount:   0,
		Available:    true,
	}
	s.serviceList = append(s.serviceList, name)

	utils.Info("注册ASR服务: %s, 权重: %d", name, weight)
}

// ReportResult 报告服务调用结果
func (s *ASRSelector) ReportResult(serviceName string, success bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if stat, exists := s.stats[serviceName]; exists {
		if success {
			stat.SuccessCount++
		}
		stat.TotalCount++

		// 更新服务可用性
		if !success && stat.TotalCount > 5 && float64(stat.SuccessCount)/float64(stat.TotalCount) < 0.2 {
			stat.Available = false
			utils.Warn("ASR服务 %s 成功率过低，临时禁用", serviceName)
		} else if success && !stat.Available {
			stat.Available = true
			utils.Info("ASR服务 %s 恢复可用", serviceName)
		}
	}
}

// SelectService 根据策略选择一个ASR服务
func (s *ASRSelector) SelectService(strategy string) (string, ServiceCreator, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if len(s.services) == 0 {
		return "", nil, false
	}

	// 根据策略选择服务
	switch strategy {
	case "round_robin":
		return s.selectByRoundRobin()
	default: // weighted_random
		return s.selectByWeightedRandom()
	}
}

// selectByRoundRobin 使用轮询策略选择服务
func (s *ASRSelector) selectByRoundRobin() (string, ServiceCreator, bool) {
	// 过滤出可用的服务
	availableServices := make([]string, 0)
	for _, name := range s.serviceList {
		if s.stats[name].Available {
			availableServices = append(availableServices, name)
		}
	}

	if len(availableServices) == 0 {
		return "", nil, false
	}

	s.roundRobinIndex = (s.roundRobinIndex + 1) % len(availableServices)
	selectedName := availableServices[s.roundRobinIndex]
	s.counters[selectedName]++

	return selectedName, s.services[selectedName], true
}

// selectByWeightedRandom 使用加权随机策略选择服务
func (s *ASRSelector) selectByWeightedRandom() (string, ServiceCreator, bool) {
	// 计算可用服务的总权重
	totalWeight := 0
	for name, weight := range s.weights {
		if s.stats[name].Available {
			totalWeight += weight
		}
	}

	if totalWeight == 0 {
		// 如果所有服务都不可用或总权重为0，则返回false
		return "", nil, false
	}

	// 随机选择
	r := rand.Intn(totalWeight)
	cumWeight := 0
	for name, weight := range s.weights {
		if s.stats[name].Available {
			cumWeight += weight
			if r < cumWeight {
				s.counters[name]++
				return name, s.services[name], true
			}
		}
	}

	// 默认情况，返回第一个可用服务
	for name := range s.weights {
		if s.stats[name].Available {
			s.counters[name]++
			return name, s.services[name], true
		}
	}

	return "", nil, false
}

// GetStats 获取服务使用统计信息
func (s *ASRSelector) GetStats() map[string]map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make(map[string]map[string]interface{})
	for name, stat := range s.stats {
		successRate := 0.0
		if stat.TotalCount > 0 {
			successRate = float64(stat.SuccessCount) / float64(stat.TotalCount) * 100
		}

		result[name] = map[string]interface{}{
			"count":        s.counters[name],
			"success_rate": fmt.Sprintf("%.1f%%", successRate),
			"available":    stat.Available,
			"weight":       s.weights[name],
		}
	}

	return result
}

// RunWithService 使用指定服务或自动选择服务来执行ASR任务，并处理结果
func (s *ASRSelector) RunWithService(ctx context.Context, audioPath string, serviceName string, useCache bool, config *models.Config, callback ProgressCallback) ([]models.DataSegment, string, map[string]string, error) {
	var service ASRService
	var err error
	var selectedName string
	var creator ServiceCreator
	var ok bool
	
	// 创建一个带有唯一ID的日志前缀
	requestID := fmt.Sprintf("ASRREQ-%s", utils.GenerateRandomString(6))
	utils.Info("[%s] 开始处理ASR请求: %s, 服务: %s", requestID, audioPath, serviceName)
	
	if serviceName == "auto" {
		// 自动选择服务
		selectedName, creator, ok = s.SelectService("weighted_random")
		if !ok {
			return nil, "", nil, fmt.Errorf("没有可用的ASR服务")
		}
	} else {
		// 使用指定的服务
		s.mu.RLock()
		creator, ok = s.services[serviceName]
		s.mu.RUnlock()
		
		if !ok {
			return nil, "", nil, fmt.Errorf("未知的ASR服务: %s", serviceName)
		}
		selectedName = serviceName
	}

	utils.Info("[%s] 选择ASR服务: %s", requestID, selectedName)

	// 添加文件验证
	if _, err := os.Stat(audioPath); os.IsNotExist(err) {
		utils.Error("[%s] 音频文件不存在: %s", requestID, audioPath)
		return nil, selectedName, nil, fmt.Errorf("音频文件不存在: %s", audioPath)
	}
	
	// 确保文件大小不为零
	fileInfo, err := os.Stat(audioPath)
	if err != nil {
		utils.Error("[%s] 无法获取文件信息: %v", requestID, err)
		return nil, selectedName, nil, fmt.Errorf("无法获取文件信息: %w", err)
	}
	
	if fileInfo.Size() == 0 {
		utils.Error("[%s] 音频文件大小为零: %s", requestID, audioPath)
		return nil, selectedName, nil, fmt.Errorf("音频文件大小为零: %s", audioPath)
	}
	
	utils.Info("[%s] 文件验证通过: %s (大小: %.2f MB)", requestID, audioPath, float64(fileInfo.Size())/(1024*1024))

	// 创建服务实例
	service, err = creator(audioPath, useCache)
	if err != nil {
		utils.Error("[%s] 创建ASR服务失败: %v", requestID, err)
		return nil, selectedName, nil, fmt.Errorf("创建ASR服务失败: %w", err)
	}

	// 包装进度回调以添加请求ID
	wrappedCallback := func(percent int, message string) {
		if callback != nil {
			utils.Debug("[%s] 进度更新: %d%%, %s", requestID, percent, message)
			callback(percent, message)
		}
	}

	// 执行识别，添加重试机制
	utils.Info("[%s] 开始执行ASR识别...", requestID)
	var segments []models.DataSegment
	var retryCount int = 0
	const maxRetries = 2
	
	for retryCount <= maxRetries {
		// 创建一个子上下文，确保每次重试都有新的超时
		taskCtx, cancel := context.WithTimeout(ctx, 5*time.Minute)
		
		// 执行任务
		segments, err = service.GetResult(taskCtx, wrappedCallback)
		cancel() // 不论是否成功，都释放上下文
		
		// 如果成功或达到最大重试次数，退出循环
		if err == nil || retryCount >= maxRetries {
			break
		}
		
		// 记录重试
		retryCount++
		utils.Warn("[%s] ASR识别失败，将进行第 %d 次重试: %v", requestID, retryCount, err)
		
		if callback != nil {
			callback(30, fmt.Sprintf("识别失败，正在重试(%d/%d)...", retryCount, maxRetries))
		}
		
		// 等待一段时间后重试
		time.Sleep(time.Second * 2)
	}
	
	// 报告结果
	success := err == nil && len(segments) > 0
	s.ReportResult(selectedName, success)
	
	if err != nil {
		utils.Error("[%s] ASR识别最终失败: %v", requestID, err)
		return nil, selectedName, nil, err
	}
	
	utils.Info("[%s] ASR识别完成，获取 %d 段文本", requestID, len(segments))
	
	// 处理识别结果
	var outputFiles map[string]string
	if len(segments) > 0 && config != nil {
		// 初始化ASR处理器
		processor := NewASRProcessor(config)
		outputFiles, err = processor.ProcessResults(ctx, segments, audioPath, nil)
		if err != nil {
			utils.Warn("[%s] 处理ASR结果失败: %v", requestID, err)
		} else {
			utils.Info("[%s] ASR结果处理完成，生成文件: %v", requestID, outputFiles)
		}
	} else if len(segments) == 0 {
		utils.Warn("[%s] ASR识别结果为空", requestID)
	}
	
	return segments, selectedName, outputFiles, err
}
