package main

import (
    "fmt"
    "io"
    "log"
    "net/http"
    "os"
    "path/filepath"
)

// corsMiddleware 添加基本的 CORS 响应头，允许所有来源和 POST 方法。
func corsMiddleware(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        // 允许来自任何来源的请求
        w.Header().Set("Access-Control-Allow-Origin", "*")
        // 允许 POST 方法和 OPTIONS (用于预检请求)
        w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
        // 允许 Content-Type 请求头 (fetch 需要)
        w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

        // 处理预检 OPTIONS 请求
        if r.Method == "OPTIONS" {
            w.WriteHeader(http.StatusOK)
            return
        }

        // 调用实际的处理函数
        next(w, r)
    }
}

// handleSaveData 接收通过 POST 发送的数据，并将其追加到本地文件。
func handleSaveData(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "只允许 POST 方法", http.StatusMethodNotAllowed)
        return
    }

    // 读取请求体 (包含 DOM 数据)
    body, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "读取请求体失败", http.StatusInternalServerError)
        log.Printf("读取请求体错误: %v", err)
        return
    }
    defer r.Body.Close()

    if len(body) == 0 {
        // 不保存空数据，但确认收到请求
        log.Println("收到空的请求体，无需保存。")
        w.WriteHeader(http.StatusOK)
        fmt.Fprintln(w, "收到空数据。")
        return
    }

    // 定义保存数据的文件路径
    saveFileName := "saved_dom_data.html"
    savePath := filepath.Join(".", saveFileName) // 保存在可执行文件所在的相同目录下

    // 以追加模式打开文件，如果文件不存在则创建
    file, err := os.OpenFile(savePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    if err != nil {
        http.Error(w, "打开或创建保存文件失败", http.StatusInternalServerError)
        log.Printf("打开/创建文件 %s 失败: %v", savePath, err)
        return
    }
    defer file.Close()

    // 将接收到的数据写入文件，并在之后添加分隔符
    if _, err := file.Write(body); err != nil {
        http.Error(w, "写入文件失败", http.StatusInternalServerError)
        log.Printf("写入文件 %s 失败: %v", savePath, err)
        return
    }
    // 添加换行符或分隔符以便阅读（如果追加多个数据块）
    if _, err := file.WriteString("\n\n<!-- === 数据块结束 === -->\n\n"); err != nil {
        log.Printf("写入分隔符到文件 %s 时出错: %v", savePath, err)
        // 即使写入分隔符失败也继续
    }

    log.Printf("成功追加 %d 字节到 %s", len(body), savePath)

    // 向浏览器发送成功响应
    w.WriteHeader(http.StatusOK)
    fmt.Fprintln(w, "数据接收并保存成功。")
}

func main() {
    // 为 /save 端点注册处理函数，并用 CORS 中间件包装
    http.HandleFunc("/save", corsMiddleware(handleSaveData))

    port := ":8080"
    saveFileName := "saved_dom_data.html"
    log.Printf("启动本地服务器于 http://localhost%s", port)
    log.Printf("数据将追加到: %s (位于服务器运行目录下)", saveFileName)
    log.Println("正在监听 /save 路径上的 POST 请求 ...")

    // 启动服务器
    err := http.ListenAndServe(port, nil)
    if err != nil {
        log.Fatalf("服务器启动失败: %v", err)
    }
}