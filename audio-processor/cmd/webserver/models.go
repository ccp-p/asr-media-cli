package main

// --- 请求结构体 ---

type GenerateNoteRequest struct {
	VideoURL   string `json:"video_url"`
	Platform   string `json:"platform"`
	Quality    string `json:"quality"`
	Screenshot *bool  `json:"screenshot"` // 使用指针以区分未提供和 false
	Link       *bool  `json:"link"`       // 使用指针以区分未提供和 false
}

type DeleteTaskRequest struct {
	VideoID  string `json:"video_id"`
	Platform string `json:"platform"`
}

// --- 响应结构体 ---

type BaseResponse struct {
	Code int    `json:"code"`
	Msg  string `json:"msg,omitempty"` // omitempty 表示如果为空则不包含在 JSON 中
}

type GenerateNoteResponse struct {
	BaseResponse
	Data *struct {
		TaskID string `json:"task_id"`
	} `json:"data,omitempty"`
}

type TaskStatusResponse struct {
	BaseResponse
	Data *TaskStatusData `json:"data,omitempty"`
}

type TaskStatusData struct {
	Status string      `json:"status"` // PENDING, RUNNING, SUCCESS, FAILED
	Result *TaskResult `json:"result,omitempty"`
}

type TaskResult struct {
	Markdown   string      `json:"markdown"`
	Transcript interface{} `json:"transcript"` // 具体结构未知，使用 interface{}
	AudioMeta  AudioMeta   `json:"audio_meta"`
}

type AudioMeta struct {
	CoverURL  string      `json:"cover_url"`
	Duration  float64     `json:"duration"`
	FilePath  string      `json:"file_path"`
	Platform  string      `json:"platform"`
	RawInfo   interface{} `json:"raw_info"` // 具体结构未知
	Title     string      `json:"title"`
	VideoID   string      `json:"video_id"`
}

// --- 任务内部表示 (示例) ---
type Task struct {
	ID         string
	Status     string // PENDING, RUNNING, SUCCESS, FAILED
	Result     *TaskResult
	VideoID    string // 用于删除
	Platform   string // 用于删除
	// ... 其他任务相关信息
}
