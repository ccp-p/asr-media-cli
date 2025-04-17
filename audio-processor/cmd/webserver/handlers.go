package main

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
)

// --- Helper Functions ---

// respondWithError 发送错误 JSON 响应
func respondWithError(w http.ResponseWriter, code int, message string) {
	respondWithJSON(w, code, BaseResponse{Code: code, Msg: message})
}

// respondWithJSON 发送 JSON 响应
func respondWithJSON(w http.ResponseWriter, code int, payload interface{}) {
	response, err := json.Marshal(payload)
	if err != nil {
		log.Printf("JSON 序列化错误: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`{"code": 500, "msg": "内部服务器错误：无法序列化响应"}`))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	w.Write(response)
}

// --- API Handlers ---

// handleGenerateNote 处理生成笔记请求
func handleGenerateNote(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		respondWithError(w, http.StatusMethodNotAllowed, "只允许 POST 方法")
		return
	}

	var req GenerateNoteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondWithError(w, http.StatusBadRequest, "无效的请求体: "+err.Error())
		return
	}
	defer r.Body.Close()

	// 基本验证 (可以添加更详细的验证)
	if req.VideoURL == "" || req.Platform == "" || req.Quality == "" {
		respondWithError(w, http.StatusBadRequest, "缺少必要的字段 (video_url, platform, quality)")
		return
	}

	// TODO: 在这里调用实际的任务创建逻辑
	taskID := createTask(req) // 使用模拟函数

	resp := GenerateNoteResponse{
		BaseResponse: BaseResponse{Code: 0},
		Data: &struct {
			TaskID string `json:"task_id"`
		}{TaskID: taskID},
	}
	respondWithJSON(w, http.StatusOK, resp)
}

// handleDeleteTask 处理删除任务请求
func handleDeleteTask(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		respondWithError(w, http.StatusMethodNotAllowed, "只允许 POST 方法")
		return
	}

	var req DeleteTaskRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondWithError(w, http.StatusBadRequest, "无效的请求体: "+err.Error())
		return
	}
	defer r.Body.Close()

	if req.VideoID == "" || req.Platform == "" {
		respondWithError(w, http.StatusBadRequest, "缺少必要的字段 (video_id, platform)")
		return
	}

	// TODO: 调用实际的任务删除逻辑
	deleted := deleteTask(req.VideoID, req.Platform) // 使用模拟函数

	if deleted {
		respondWithJSON(w, http.StatusOK, BaseResponse{Code: 0, Msg: "任务已删除"})
	} else {
		// 注意：即使找不到任务也可能返回成功，取决于产品需求
		// 这里假设找不到任务算作一种“失败”或未找到
		respondWithError(w, http.StatusNotFound, "未找到要删除的任务")
	}
}

// handleGetTaskStatus 处理获取任务状态请求
func handleGetTaskStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondWithError(w, http.StatusMethodNotAllowed, "只允许 GET 方法")
		return
	}

	// 从 URL 路径中提取 task_id
	// 假设路径是 /api/task_status/{task_id}
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) != 3 || pathParts[1] != "task_status" {
		respondWithError(w, http.StatusBadRequest, "无效的请求路径格式，应为 /api/task_status/{task_id}")
		return
	}
	taskID := pathParts[2]

	if taskID == "" {
		respondWithError(w, http.StatusBadRequest, "缺少 task_id")
		return
	}

	// TODO: 调用实际的获取任务状态逻辑
	task, found := getTaskStatus(taskID) // 使用模拟函数

	if !found {
		respondWithError(w, http.StatusNotFound, "未找到指定的任务")
		return
	}

	resp := TaskStatusResponse{
		BaseResponse: BaseResponse{Code: 0},
		Data: &TaskStatusData{
			Status: task.Status,
			Result: task.Result, // 如果任务未完成，Result 可能为 nil
		},
	}
	respondWithJSON(w, http.StatusOK, resp)
}

// handleImageProxy 处理图片代理请求
func handleImageProxy(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		respondWithError(w, http.StatusMethodNotAllowed, "只允许 GET 方法")
		return
	}

	imageURL := r.URL.Query().Get("url")
	if imageURL == "" {
		respondWithError(w, http.StatusBadRequest, "缺少 'url' 查询参数")
		return
	}

	// 解码 URL (如果前端编码了)
	decodedURL, err := url.QueryUnescape(imageURL)
	if err != nil {
		respondWithError(w, http.StatusBadRequest, "无效的 'url' 参数: "+err.Error())
		return
	}

	log.Printf("代理图片请求: %s", decodedURL)

	// TODO: 添加安全检查，例如限制允许代理的域名

	// 发起 GET 请求获取外部图片
	resp, err := http.Get(decodedURL)
	if err != nil {
		log.Printf("代理请求失败 (%s): %v", decodedURL, err)
		respondWithError(w, http.StatusBadGateway, "无法获取外部图片")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("代理请求外部资源返回非 200 状态 (%s): %d", decodedURL, resp.StatusCode)
		// 可以选择透传状态码，或者返回统一错误
		respondWithError(w, http.StatusBadGateway, "外部图片服务器错误")
		return
	}

	// 设置响应头 (Content-Type, Content-Length 等会被 io.Copy 自动处理一部分)
	// 复制外部响应的 Content-Type
	contentType := resp.Header.Get("Content-Type")
	if contentType != "" {
		w.Header().Set("Content-Type", contentType)
	}
	// 可以添加缓存头等
	// w.Header().Set("Cache-Control", "public, max-age=86400") // 缓存一天

	// 将图片内容流式传输给客户端
	_, err = io.Copy(w, resp.Body)
	if err != nil {
		log.Printf("代理图片流式传输错误 (%s): %v", decodedURL, err)
		// 此时可能已经发送了部分响应头，无法再发送 JSON 错误
		// http 包会自动处理
	}
}
