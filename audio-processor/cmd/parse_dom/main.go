package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	// 获取目标目录，支持命令行参数或默认当前目录
	targetDir := "D:\\project\\cx_project\\china_mobile\\chartityProject\\gitSourceCode\\charity-open-fronted\\wap"
	if len(os.Args) > 1 {
		targetDir = os.Args[1]
	}

	fmt.Printf("正在扫描目录: %s\n", targetDir)

	// 定义要删除的文件扩展名和名称（不区分大小写）
	extensions := []string{".pdf"}
	names := []string{"readme"}

	// 遍历目录并删除匹配文件
	err := filepath.WalkDir(targetDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			fmt.Printf("警告: 无法访问 %s: %v\n", path, err)
			return nil // 继续遍历其他文件
		}

		// 排除 node_modules 目录
		if d.IsDir() && d.Name() == "node_modules" {
			fmt.Printf("跳过目录: %s\n", path)
			return filepath.SkipDir // 跳过整个 node_modules 子树
		}

		// 只处理文件
		if !d.Type().IsRegular() {
			return nil
		}

		filename := strings.ToLower(d.Name())
		shouldDelete := false

		// 检查是否是 .txt 文件
		for _, ext := range extensions {
			if strings.HasSuffix(filename, ext) {
				shouldDelete = true
				break
			}
		}

		// 检查是否是 README（不区分大小写）
		for _, name := range names {
			if filename == name || strings.HasPrefix(filename, name+".") {
				shouldDelete = true
				break
			}
		}

		if shouldDelete {
			fmt.Printf("即将删除: %s\n", path)
			// err := os.Remove(path)
			// if err != nil {
			// 	fmt.Printf("❌ 删除失败: %s - %v\n", path, err)
			// } else {
			// 	fmt.Printf("✅ 已删除: %s\n", path)
			// }
		}

		return nil
	})

	if err != nil {
		fmt.Printf("遍历目录时发生错误: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("清理完成！")
}