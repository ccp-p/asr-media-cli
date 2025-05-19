package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/internal/controller"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

var (
	appController *controller.ProcessorController
)

func main() {
	configFile := os.Getenv("APP_CONFIG_FILE")
	if configFile == "" {
		configFile = "config.yaml"
		utils.Info("未指定配置文件路径 (APP_CONFIG_FILE)，尝试使用默认值: %s", configFile)
	}
	logLevel := os.Getenv("APP_LOG_LEVEL")
	if logLevel == "" {
		logLevel = "info"
	}
	logFile := os.Getenv("APP_LOG_FILE")

	var err error
	appController, err = controller.NewProcessorController(configFile, logLevel, logFile)
	if err != nil {
		log.Fatalf("初始化控制器失败: %v\n", err)
	}

	printWelcomeToLog()
	if !checkDependencies() {
		log.Fatal("缺少必要的依赖项，无法继续")
	}

	http.HandleFunc("/", serveHTMLHandler) // 服务主页面
	http.HandleFunc("/upload", uploadAndProcessHandler) // 处理文件上传和处理

	port := os.Getenv("APP_PORT")
	if port == "" {
		port = "8080"
	}
	serverAddr := ":" + port
	utils.Info("启动 Web 服务器，监听地址: http://localhost%s", serverAddr)
	if err := http.ListenAndServe(serverAddr, nil); err != nil {
		log.Fatalf("服务器启动失败: %v", err)
	}
}

func printWelcomeToLog() {
	utils.Info("================================")
	utils.Info("   音频处理 Web 服务已启动   ")
	utils.Info("================================")
}

func checkDependencies() bool {
	utils.Info("检查系统依赖...")
	if !utils.CheckFFmpeg() {
		utils.Error("未检测到FFmpeg，请确保FFmpeg已安装并添加到系统路径")
		return false
	}
	utils.Info("系统依赖检查通过")
	return true
}

func serveHTMLHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, "./web/index.html")
}

func uploadAndProcessHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "仅支持POST方法", http.StatusMethodNotAllowed)
		return
	}

	file, handler, err := r.FormFile("mediaFile")
	if err != nil {
		utils.Error("获取上传文件失败: %v", err)
		http.Error(w, "获取文件失败: "+err.Error(), http.StatusBadRequest)
		return
	}
	defer file.Close()

	utils.Info("接收到上传文件: %s, 大小: %d bytes", handler.Filename, handler.Size)

	uploadDir := "./uploads_temp" // 临时存储上传文件的目录
	if _, err := os.Stat(uploadDir); os.IsNotExist(err) {
		os.MkdirAll(uploadDir, os.ModePerm)
	}
	tempFilePath := filepath.Join(uploadDir, fmt.Sprintf("%d_%s", time.Now().UnixNano(), handler.Filename))

	tempFile, err := os.Create(tempFilePath)
	if err != nil {
		utils.Error("创建临时文件失败: %v", err)
		http.Error(w, "无法创建临时文件: "+err.Error(), http.StatusInternalServerError)
		return
	}
	defer os.Remove(tempFilePath) // 确保在处理完成后删除临时文件

	_, err = io.Copy(tempFile, file)
	if err != nil {
		utils.Error("保存上传文件失败: %v", err)
		http.Error(w, "无法保存上传文件: "+err.Error(), http.StatusInternalServerError)
		return
	}
	tempFile.Close() // 关闭文件以便后续处理

	// 调用控制器处理文件并获取SRT字符串
	srtContent, err := appController.ProcessSingleFileAndGetSRT(tempFilePath)
	if err != nil {
		utils.Error("处理文件并生成SRT失败: %v", err)
		http.Error(w, "处理失败: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// 返回生成的SRT内容
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"srt": srtContent})
}