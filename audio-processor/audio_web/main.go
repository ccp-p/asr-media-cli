package main

import (
    "context"
    "encoding/json"
    "flag"
    "fmt"
    "log"
    "net/http"
    "os"
    "time"

    "github.com/ccp-p/asr-media-cli/audio-processor/internal/controller"
    "github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
    "github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
    "github.com/gorilla/mux"
)

var (
    configFile = flag.String("config", "", "配置文件路径")
    logLevel   = flag.String("log-level", "info", "日志级别 (debug, info, warn, error)")
    logFile    = flag.String("log-file", "./log.txt", "日志文件路径")
    port       = flag.Int("port", 8080, "Web服务端口")
    uploadDir  = flag.String("upload-dir", "./uploads", "上传文件存储目录")
    tempDir    = flag.String("temp-dir", "./temp", "临时文件目录")
    outputDir  = flag.String("output-dir", "./output", "输出文件目录")
)

// 全局Web处理器
var webProcessor *audio.WebProcessor

func main() {
    // 解析命令行参数
    flag.Parse()

    // 创建处理器控制器
    controller, err := controller.NewProcessorController(*configFile, *logLevel, *logFile)
    if err != nil {
        fmt.Printf("初始化控制器失败: %v\n", err)
        os.Exit(1)
    }
    defer controller.Cleanup()

    // 打印欢迎信息
    printWelcome()

    // 检查依赖
    if !checkDependencies() {
        utils.Fatal("缺少必要的依赖项，无法继续")
        os.Exit(1)
    }

    // 创建目录
    for _, dir := range []string{*uploadDir, *tempDir, *outputDir} {
        if err := os.MkdirAll(dir, 0755); err != nil {
            utils.Fatal("创建目录失败: %v", err)
            os.Exit(1)
        }
    }

    // 创建Web处理器
    webProcessor = audio.NewWebProcessor(*uploadDir, *tempDir, *outputDir, controller.Config)
    webProcessor.Processor.SetASRSelector(controller.ASRSelector)
    webProcessor.Processor.SetContext(context.Background())

    // 启动定时清理任务
    go startCleanupTask()

    // 设置路由
    r := mux.NewRouter()
    r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static"))))
    r.HandleFunc("/", homeHandler).Methods("GET")
    r.HandleFunc("/upload", uploadHandler).Methods("POST")
    r.HandleFunc("/health", healthCheckHandler).Methods("GET")

    // 启动服务器
    serverAddr := fmt.Sprintf(":%d", *port)
    utils.Info("Web服务启动在 %s", serverAddr)
    log.Fatal(http.ListenAndServe(serverAddr, r))
}

// 首页处理
func homeHandler(w http.ResponseWriter, r *http.Request) {
    http.ServeFile(w, r, "./web/index.html")
}

// 上传处理
func uploadHandler(w http.ResponseWriter, r *http.Request) {
    // 设置响应头
    w.Header().Set("Content-Type", "application/json")

    // 解析表单
    if err := r.ParseMultipartForm(32 << 20); err != nil { // 32MB
        http.Error(w, "无法解析表单", http.StatusBadRequest)
        return
    }

    // 获取上传的文件
    file, header, err := r.FormFile("file")
    if err != nil {
        sendErrorResponse(w, "获取上传文件失败", http.StatusBadRequest)
        return
    }
    defer file.Close()

    // 处理文件
    utils.Info("接收到文件上传: %s, 大小: %d bytes", header.Filename, header.Size)
    
    result, err := webProcessor.ProcessUploadedFile(file, header.Filename)
    if err != nil {
        sendErrorResponse(w, fmt.Sprintf("处理文件失败: %v", err), http.StatusInternalServerError)
        return
    }

    // 发送成功响应
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(result)
}

// 健康检查
func healthCheckHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]bool{"status": true})
}

// 发送错误响应
func sendErrorResponse(w http.ResponseWriter, message string, statusCode int) {
    w.WriteHeader(statusCode)
    json.NewEncoder(w).Encode(map[string]string{
        "error": message,
    })
}

// 启动定期清理任务
func startCleanupTask() {
    ticker := time.NewTicker(6 * time.Hour)
    defer ticker.Stop()

    for {
        <-ticker.C
        utils.Info("开始清理过期文件...")
        if err := webProcessor.CleanupOldFiles(24 * time.Hour); err != nil {
            utils.Error("清理文件失败: %v", err)
        }
    }
}

func printWelcome() {
    fmt.Println()
    fmt.Println("================================")
    fmt.Println("   音频Web服务 - Go 实现版本   ")
    fmt.Println("================================")
    fmt.Println()
}

func checkDependencies() bool {
    fmt.Print("检查系统依赖... ")

    // 检查ffmpeg
    if !utils.CheckFFmpeg() {
        fmt.Println("失败")
        utils.Error("未检测到FFmpeg，请确保FFmpeg已安装并添加到系统路径")
        return false
    }

    fmt.Println("通过")
    return true
}