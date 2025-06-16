package llm

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"

    "github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

// VolcesAPIClient 封装对Volces API的访问
type VolcesAPIClient struct {
    APIKey     string
    BaseURL    string
    HttpClient *http.Client
}

// ChatMessage 表示聊天消息
type ChatMessage struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

// ChatRequest 表示对API的请求
type ChatRequest struct {
    Model    string        `json:"model"`
    Messages []ChatMessage `json:"messages"`
}

// ChatResponse 表示API的响应
type ChatResponse struct {
    ID      string `json:"id"`
    Object  string `json:"object"`
    Created int64  `json:"created"`
    Model   string `json:"model"`
    Choices []struct {
        Index        int `json:"index"`
        Message      ChatMessage `json:"message"`
        FinishReason string `json:"finish_reason"`
    } `json:"choices"`
    Usage struct {
        PromptTokens     int `json:"prompt_tokens"`
        CompletionTokens int `json:"completion_tokens"`
        TotalTokens      int `json:"total_tokens"`
    } `json:"usage"`
}

// NewVolcesAPIClient 创建一个新的API客户端
func NewVolcesAPIClient(apiKey string) *VolcesAPIClient {
    return &VolcesAPIClient{
        APIKey:  apiKey,
        BaseURL: "https://ark.cn-beijing.volces.com",
        HttpClient: &http.Client{
            Timeout: 60 * time.Second,
        },
    }
}

// GenerateSummary 使用API生成文本摘要
func (c *VolcesAPIClient) GenerateSummary(content string) (string, error) {
    endpoint := "/api/v3/chat/completions"
    url := c.BaseURL + endpoint

    // 构建请求体
    messages := []ChatMessage{
        {
            Role:    "system",
            Content: "你是一个专业的文字总结助手。请对以下文本进行简明扼要的总结，提取关键信息和主要观点。",
        },
        {
            Role:    "user",
            Content: content,
        },
    }

    requestBody := ChatRequest{
        Model:    "doubao-1-5-pro-256k-250115",
        Messages: messages,
    }

    // 将请求体序列化为JSON
    jsonBytes, err := json.Marshal(requestBody)
    if err != nil {
        return "", fmt.Errorf("序列化请求失败: %v", err)
    }

    // 创建HTTP请求
    req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonBytes))
    if err != nil {
        return "", fmt.Errorf("创建请求失败: %v", err)
    }

    // 设置请求头
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+c.APIKey)

    // 发送请求
    utils.Info("发送API请求到 %s", url)
    resp, err := c.HttpClient.Do(req)
    if err != nil {
        return "", fmt.Errorf("发送请求失败: %v", err)
    }
    defer resp.Body.Close()

    // 读取响应体
    body, err := io.ReadAll(resp.Body)
    if err != nil {
        return "", fmt.Errorf("读取响应失败: %v", err)
    }

    // 检查状态码
    if resp.StatusCode != http.StatusOK {
        return "", fmt.Errorf("API返回错误状态码: %d, 响应: %s", resp.StatusCode, string(body))
    }

    // 解析响应
    var response ChatResponse
    if err := json.Unmarshal(body, &response); err != nil {
        return "", fmt.Errorf("解析响应失败: %v", err)
    }

    // 提取生成的文本
    if len(response.Choices) > 0 {
        return response.Choices[0].Message.Content, nil
    }

    return "", fmt.Errorf("API响应中没有生成内容")
}