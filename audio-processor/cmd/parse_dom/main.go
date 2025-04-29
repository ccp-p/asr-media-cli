package main

import (
    "encoding/json"
    "fmt"
    "os"
    "path/filepath"
    "regexp"
    "strings"
)

// Item 结构用于存储提取的数据
type Item struct {
    Title string `json:"title"`
    URL   string `json:"url"`
}

func main() {
    // --- 配置 ---
    // 指定要解析的 HTML 文件路径
    htmlFilePath := `D:\download\dest\zysc.html` // 请将此路径替换为您的 HTML 文件实际路径
    // 指定输出的 JSON 文件路径
    jsonOutputPath := `D:\download\dest\zysc.json`
    // --- 配置结束 ---

    fmt.Printf("正在读取 HTML 文件: %s\n", htmlFilePath)
    // 读取 HTML 文件内容
    htmlContentBytes, err := os.ReadFile(htmlFilePath)
    if err != nil {
        fmt.Printf("错误：无法读取 HTML 文件 '%s': %v\n", htmlFilePath, err)
        os.Exit(1)
    }
    htmlContent := string(htmlContentBytes)

    // 定义正则表达式
    // (?s) 让 . 匹配换行符
    // 捕获组 1: href 属性的值 (URL)
    // 捕获组 2: div.row-subtitle 的完整内部 HTML 内容
    re := regexp.MustCompile(`(?s)<a class=".*?search-super-item.*?href="([^"]+)".*?<div class="row-subtitle".*?>(.*?)</div>`)

    // 查找所有匹配项
    matches := re.FindAllStringSubmatch(htmlContent, -1)

    if len(matches) == 0 {
        fmt.Println("未找到匹配的 DOM 项。")
        return
    }

    fmt.Printf("找到了 %d 个匹配项。\n", len(matches))

    var results []Item
    // 遍历匹配项并提取数据
    for _, match := range matches {
        if len(match) == 3 {
            url := match[1]
            rawSubtitleContent := match[2]

            // 清理标题：
            // 1. 尝试按 "|" 分割，取第一部分（如果存在 "|"）
            // 2. 移除可能存在的嵌套 <a> 标签及其内容（使用简单替换，对复杂 HTML 可能不完美）
            // 3. 去除首尾空白和换行符
            titleParts := strings.SplitN(rawSubtitleContent, "|", 2)
            title := titleParts[0]

            // 简单移除嵌套的 <a> 标签
            anchorTagRegex := regexp.MustCompile(`<a.*?</a>`)
            title = anchorTagRegex.ReplaceAllString(title, "")

            // 去除多余的空白和换行
            title = strings.TrimSpace(title)
            // 替换多个连续空白为一个空格
            spaceRegex := regexp.MustCompile(`\s+`)
            title = spaceRegex.ReplaceAllString(title, " ")


            if title != "" && url != "" {
                results = append(results, Item{
                    Title: title,
                    URL:   url,
                })
            } else {
                fmt.Printf("警告：提取到的标题或 URL 为空。URL: '%s', Raw Title: '%s'\n", url, rawSubtitleContent)
            }
        }
    }

    if len(results) == 0 {
        fmt.Println("提取到的有效数据为空。")
        return
    }

    fmt.Printf("成功提取 %d 条有效数据。\n", len(results))

    // 将结果转换为 JSON 格式
    jsonData, err := json.MarshalIndent(results, "", "  ") // 使用缩进美化输出
    if err != nil {
        fmt.Printf("错误：无法将结果转换为 JSON: %v\n", err)
        os.Exit(1)
    }

    // 确保输出目录存在
    outputDir := filepath.Dir(jsonOutputPath)
    if err := os.MkdirAll(outputDir, os.ModePerm); err != nil {
        fmt.Printf("错误：无法创建输出目录 '%s': %v\n", outputDir, err)
        os.Exit(1)
    }

    // 将 JSON 数据写入文件
    err = os.WriteFile(jsonOutputPath, jsonData, 0644)
    if err != nil {
        fmt.Printf("错误：无法将 JSON 写入文件 '%s': %v\n", jsonOutputPath, err)
        os.Exit(1)
    }

    fmt.Printf("成功将结果写入 JSON 文件: %s\n", jsonOutputPath)
}