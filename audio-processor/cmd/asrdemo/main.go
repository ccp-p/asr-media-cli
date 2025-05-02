package main

import (
    "fmt"
    "io"
    "log"
    "net/http"
    "regexp"
    "strings"
    "time"
)

func main() {
    url := "https://pan.quark.cn/s/11f07d053042#/list/share" // 目标 URL

    fmt.Printf("正在请求 URL: %s\n", url)

    // 创建一个 HTTP 客户端，可以设置超时等
    client := &http.Client{
        Timeout: 15 * time.Second, // 设置 15 秒超时
    }

    // 创建请求，可以添加必要的 Header 模拟浏览器
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        log.Fatalf("创建请求失败: %v", err)
    }

    // 添加一些常见的浏览器 Header，增加请求成功的可能性
    req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9")
    req.Header.Set("Accept-Language", "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7")
    // 如果需要，可能还需要添加 Cookie 等

    // 发送 HTTP GET 请求
    resp, err := client.Do(req)
    if err != nil {
        log.Fatalf("请求 URL 失败: %v", err)
    }
    defer resp.Body.Close() // 确保关闭响应体

    // 检查响应状态码
    if resp.StatusCode != http.StatusOK {
        log.Fatalf("请求失败，状态码: %d %s", resp.StatusCode, resp.Status)
    }

    // 读取响应体内容
    bodyBytes, err := io.ReadAll(resp.Body)
	
    if err != nil {
        log.Fatalf("读取响应体失败: %v", err)
    }
    htmlContent := string(bodyBytes)
    fmt.Println(htmlContent)
    fmt.Println("成功获取响应，长度:", len(htmlContent))
    // fmt.Println("响应体内容 (前 500 字符):", htmlContent[:500]) // 可选：打印部分内容检查

    // 定义正则表达式
    // 匹配包含所有三个类名的元素（顺序不限），并捕获其间的文本内容
    // (?s) 让 . 匹配换行符
    // (?:...) 非捕获分组
    // \b 单词边界，确保匹配完整的类名
    // .*? 非贪婪匹配
    // >(.*?)< 捕获标签之间的内容（捕获组 1）
    regexPattern := `(?s)<(?:div|span|td)[^>]*?\bclass="[^"]*?\bfilename-text\b[^"]*?\beditable-cell\b[^"]*?\beditable-cell-allow\b[^"]*?"[^>]*?>(.*?)</(?:div|span|td)>`
    re := regexp.MustCompile(regexPattern)

    // 查找所有匹配项
    matches := re.FindAllStringSubmatch(htmlContent, -1)

    fmt.Printf("正则表达式 '%s' 查找结果:\n", regexPattern)
    if len(matches) == 0 {
        fmt.Println("未找到任何匹配指定类名的元素。这很可能是因为内容是动态加载的。")
    } else {
        fmt.Printf("找到了 %d 个匹配项:\n", len(matches))
        count := 0
        for _, match := range matches {
            if len(match) > 1 {
                // 提取捕获组 1 的内容，并去除首尾空白
                title := strings.TrimSpace(match[1])
                // 进一步清理，移除可能存在的内部 HTML 标签（简单替换）
                innerTagRegex := regexp.MustCompile(`<.*?>`)
                title = innerTagRegex.ReplaceAllString(title, "")
                title = strings.TrimSpace(title) // 再次 trim

                if title != "" {
                    count++
                    fmt.Printf("  - %d: %s\n", count, title)
                }
            }
        }
        if count == 0 {
            fmt.Println("虽然找到了匹配的标签结构，但未能提取到有效的文本标题。")
        }
    }

    fmt.Println("\n提醒：如果未找到预期结果，很可能是因为文件列表是通过 JavaScript 动态加载的，无法通过简单的 HTTP 请求和正则表达式获取。")
}