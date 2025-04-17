package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
)

// spaHandler 结构用于处理单页应用路由
type spaHandler struct {
	staticPath string
	indexPath  string
}

// ServeHTTP 实现 http.Handler 接口
func (h spaHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// 获取请求的文件路径
	path := filepath.Join(h.staticPath, r.URL.Path)

	// 检查文件是否存在
	_, err := os.Stat(path)
	if os.IsNotExist(err) {
		// 文件不存在，提供 index.html
		http.ServeFile(w, r, filepath.Join(h.staticPath, h.indexPath))
		return
	} else if err != nil {
		// 其他错误
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// 文件存在，直接提供文件
	http.FileServer(http.Dir(h.staticPath)).ServeHTTP(w, r)
}

// apiHandler 处理所有 /api/ 请求的占位符
func apiHandler(w http.ResponseWriter, r *http.Request) {
	// 打印接收到的 API 请求路径
	log.Printf("接收到 API 请求: %s %s", r.Method, r.URL.Path)

	// TODO: 在这里实现你的 API 逻辑
	// 例如：解析请求、调用服务、返回 JSON 响应等

	// 简单的占位符响应
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"message": "API 请求已收到，但尚未实现"}`))
}

func main() {
	// 获取当前工作目录 (例如: D:\project\my_py_project\segement_audio\audio-processor\cmd\webserver)
	currentWorkDir, err := os.Getwd()
	if err != nil {
		log.Fatalf("获取当前工作目录失败: %v", err)
	}
	fmt.Println("当前工作目录:", currentWorkDir)

	// 获取 audio-processor 目录 (父目录的父目录)
	projectRoot := filepath.Dir(filepath.Dir(currentWorkDir))
	fmt.Println("项目根目录 (audio-processor):", projectRoot)

	// 构建静态文件目录的正确路径
	staticFilesDir := filepath.Join(projectRoot, "BillNote_frontend", "dist")
	indexPath := "index.html"

	// 检查静态文件目录是否存在
	if _, err := os.Stat(staticFilesDir); os.IsNotExist(err) {
		log.Fatalf("错误：静态文件目录 '%s' 不存在。请先构建前端应用 (例如：pnpm run build)。", staticFilesDir)
	} else {
		log.Printf("将从目录 '%s' 提供静态文件", staticFilesDir)
	}

	// 创建 SPA 处理器
	spa := spaHandler{staticPath: staticFilesDir, indexPath: indexPath}

	// 注册 API 处理器
	http.HandleFunc("/api/", apiHandler)

	// 注册 SPA 处理器处理所有其他请求
	http.Handle("/", spa)

	port := ":8080"
	log.Printf("服务器启动，监听端口 %s", port)
	log.Printf("请在浏览器中打开 http://localhost%s", port)

	// 启动服务器
	err = http.ListenAndServe(port, nil) // 使用 = 而不是 :=
	if err != nil {
		log.Fatalf("服务器启动失败: %v", err)
	}
}
