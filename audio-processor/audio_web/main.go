package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/controller"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/audio"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/llm"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
	"github.com/gorilla/mux"
)

var (
    configFile  = flag.String("config", "", "配置文件路径")
    logLevel    = flag.String("log-level", "info", "日志级别 (debug, info, warn, error)")
    logFile     = flag.String("log-file", "./log.txt", "日志文件路径")
    port        = flag.Int("port", 8080, "Web服务端口")
    uploadDir   = flag.String("upload-dir", "./uploads", "上传文件存储目录")
    tempDir     = flag.String("temp-dir", "./temp", "临时文件目录")
    outputDir   = flag.String("output-dir", "./output", "输出文件目录")
    volcesAPIKey = flag.String("volces-api-key", '', "Volces API密钥")
)

// 全局Web处理器
var webProcessor *audio.WebProcessor

// 全局API客户端
var apiClient *llm.VolcesAPIClient

func main() {
    // 解析命令行参数
    flag.Parse()

    // 配置日志
    utils.InitLogger(*logLevel, *configFile)

   // 创建处理器控制器
   controller, err := controller.NewProcessorController(*configFile, *logLevel, *logFile)
   if err != nil {
       fmt.Printf("初始化控制器失败: %v\n", err)
       os.Exit(1)
   }
    // 打印欢迎信息
    printWelcome()

    // 检查依赖
    if !checkDependencies() {
        os.Exit(1)
    }

    // 创建目录
    createDirectories()

    // 创建Web处理器
    webProcessor = audio.NewWebProcessor(*uploadDir, *outputDir, *tempDir, controller.Config)
    webProcessor.Processor.SetASRSelector(controller.ASRSelector)
    webProcessor.Processor.SetContext(context.Background())
    // 初始化API客户端
    if *volcesAPIKey != "" {
        apiClient = llm.NewVolcesAPIClient(*volcesAPIKey)
        utils.Info("已初始化Volces API客户端")
    } else {
        utils.Warn("未提供Volces API密钥，意见总结功能将不可用")
    }

    // 启动定时清理任务
    go startCleanupTask()

    // 设置路由
    router := setupRouter()

    // 启动服务器
    serverAddr := fmt.Sprintf(":%d", *port)
    utils.Info("启动Web服务器，监听地址: %s", serverAddr)
    utils.Info("在浏览器中访问: http://localhost:%d", *port)

    server := &http.Server{
        Addr:         serverAddr,
        Handler:      router,
        ReadTimeout:  15 * time.Minute,
        WriteTimeout: 15 * time.Minute,
    }

    if err := server.ListenAndServe(); err != nil {
        utils.Fatal("启动服务器失败: %v", err)
    }
}



// 创建必要的目录
func createDirectories() {
    dirs := []string{*uploadDir, *tempDir, *outputDir}
    for _, dir := range dirs {
        if err := os.MkdirAll(dir, 0755); err != nil {
            utils.Fatal("创建目录失败 %s: %v", dir, err)
            os.Exit(1)
        }
    }
}

// 设置路由
func setupRouter() *mux.Router {
    router := mux.NewRouter()

    // 静态文件服务
    router.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static"))))

    // API路由
    router.HandleFunc("/", homeHandler).Methods("GET")
    router.HandleFunc("/upload", uploadHandler).Methods("POST")
    router.HandleFunc("/health", healthCheckHandler).Methods("GET")
    router.HandleFunc("/api/summarize", summarizeHandler).Methods("POST")

    return router
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

// 总结处理
func summarizeHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")

    // 检查API客户端是否配置
    if apiClient == nil {
        sendErrorResponse(w, "未配置API密钥，无法使用总结功能", http.StatusServiceUnavailable)
        return
    }

    // 解析请求
    var request struct {
        Text string `json:"text"`
    }
    
    if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
        sendErrorResponse(w, "解析请求失败", http.StatusBadRequest)
        return
    }

    // 检查文本是否为空
    if request.Text == "" {
        sendErrorResponse(w, "文本内容为空", http.StatusBadRequest)
        return
    }

    // 调用API生成总结
    summary, err := apiClient.GenerateSummary(request.Text)
    if err != nil {
        utils.Error("生成总结失败: %v", err)
        sendErrorResponse(w, fmt.Sprintf("生成总结失败: %v", err), http.StatusInternalServerError)
        return
    }

    // 返回总结结果
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{
        "summary": summary,
    })
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