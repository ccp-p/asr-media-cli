package main

import (
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
)

// 使用 sync.Map 来安全地并发读写
var tasks = sync.Map{}

// createTask 创建一个新任务并存储 (模拟)
func createTask(req GenerateNoteRequest) string {
	taskID := uuid.New().String()
	newTask := &Task{
		ID:       taskID,
		Status:   "PENDING", // 初始状态
		VideoID:  extractVideoID(req.VideoURL, req.Platform), // 假设有函数提取 VideoID
		Platform: req.Platform,
		Result:   nil,
	}
	tasks.Store(taskID, newTask)
	log.Printf("创建任务: %s (VideoURL: %s)", taskID, req.VideoURL)

	// 模拟任务处理过程
	go simulateTaskProcessing(taskID)

	return taskID
}

// getTaskStatus 获取任务状态和结果
func getTaskStatus(taskID string) (*Task, bool) {
	value, ok := tasks.Load(taskID)
	if !ok {
		return nil, false
	}
	task, ok := value.(*Task)
	if !ok {
		// 类型断言失败，这不应该发生
		log.Printf("错误: 任务 %s 类型断言失败", taskID)
		return nil, false
	}
	return task, true
}

// deleteTask 删除任务 (模拟)
func deleteTask(videoID, platform string) bool {
	deleted := false
	tasks.Range(func(key, value interface{}) bool {
		task, ok := value.(*Task)
		if ok && task.VideoID == videoID && task.Platform == platform {
			tasks.Delete(key)
			log.Printf("删除任务: %s (VideoID: %s, Platform: %s)", key, videoID, platform)
			deleted = true
			return false // 停止遍历
		}
		return true // 继续遍历
	})
	return deleted
}

// simulateTaskProcessing 模拟后台任务处理
func simulateTaskProcessing(taskID string) {
	// 1. 模拟运行中状态
	time.Sleep(5 * time.Second) // 模拟处理时间
	value, ok := tasks.Load(taskID)
	if !ok { return } // 任务可能已被删除
	task := value.(*Task)
	task.Status = "RUNNING"
	tasks.Store(taskID, task)
	log.Printf("任务 %s 状态更新为 RUNNING", taskID)

	// 2. 模拟处理完成 -> SUCCESS
	time.Sleep(10 * time.Second) // 模拟更多处理时间
	value, ok = tasks.Load(taskID)
	if !ok { return } // 任务可能已被删除
	task = value.(*Task)
	task.Status = "SUCCESS"
	// 填充模拟结果
	task.Result = &TaskResult{
		Markdown:   "# 模拟生成的笔记\n\n这是根据视频内容生成的模拟 Markdown 笔记。",
		Transcript: map[string]interface{}{"text": "模拟转录文本...", "segments": []string{}},
		AudioMeta: AudioMeta{
			CoverURL: "https://example.com/cover.jpg", // 模拟封面 URL
			Title:    "模拟视频标题",
			VideoID:  task.VideoID,
			Platform: task.Platform,
			Duration: 120.5,
		},
	}
	tasks.Store(taskID, task)
	log.Printf("任务 %s 状态更新为 SUCCESS", taskID)

	// 注意：实际应用中需要处理 FAILED 状态
}

// extractVideoID 模拟从 URL 提取 Video ID (需要根据实际平台实现)
func extractVideoID(videoURL, platform string) string {
	// 这是一个非常简化的示例，你需要根据 Bilibili 和 YouTube 的 URL 格式实现
	// 例如，可以解析 URL 路径或查询参数
	if platform == "bilibili" {
		// 尝试提取 BV 号等
		return "BV1xx411c7mu" // 示例
	} else if platform == "youtube" {
		// 尝试提取 v 参数
		return "dQw4w9WgXcQ" // 示例
	}
	return "unknown_" + uuid.New().String()[:8]
}
