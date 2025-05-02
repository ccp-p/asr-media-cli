package main

import (
    "fmt"
    "os"
    "path/filepath"
    "strings"
)

func main() {
    // 硬编码的目录路径
    // dirPath := `D:\project\cx_project\csp-mange\dist1\dist`
    dirPath := `D:\project\cx_project\csp-mange\dist`

    // 统计结果
    var jsCount, cssCount int
    var totalSize int64
    var jsSize, cssSize int64

    // 统计子目录数量
    subDirs := make(map[string]struct{})

    // 遍历目录
    err := filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
        if err != nil {
            fmt.Printf("访问路径出错: %v\n", err)
            return err
        }

        // 跳过目录本身
        if info.IsDir() {
            // 不统计根目录
            if path != dirPath {
                subDirs[path] = struct{}{}
            }
            return nil
        }

        // 获取文件扩展名并转为小写
        ext := strings.ToLower(filepath.Ext(path))

        // 统计文件大小
        fileSize := info.Size()
        totalSize += fileSize

        // 统计JS文件
        if ext == ".js" {
            jsCount++
            jsSize += fileSize
        }

        // 统计CSS文件
        if ext == ".css" {
            cssCount++
            cssSize += fileSize
        }

        return nil
    })

    if err != nil {
        fmt.Printf("遍历目录失败: %v\n", err)
        os.Exit(1)
    }

    // 打印统计结果
    fmt.Println("============= 文件统计结果 =============")
    fmt.Printf("目录路径: %s\n", dirPath)
    fmt.Printf("JS 文件数量: %d 个\n", jsCount)
    fmt.Printf("CSS 文件数量: %d 个\n", cssCount)
    fmt.Printf("JS + CSS 文件总数: %d 个\n", jsCount+cssCount)
    fmt.Printf("子目录数量: %d 个\n", len(subDirs))
    fmt.Println("\n============= 文件大小统计 =============")
    fmt.Printf("JS 文件总大小: %.2f MB\n", float64(jsSize)/(1024*1024))
    fmt.Printf("CSS 文件总大小: %.2f MB\n", float64(cssSize)/(1024*1024))
    fmt.Printf("所有文件总大小: %.2f MB\n", float64(totalSize)/(1024*1024))

    // 统计不同级别目录下的文件分布
    fmt.Println("\n============= 目录层级分布 =============")
    dirLevelStats := make(map[int]int)
    
    for _, root := range []string{dirPath} {
        rootLevel := strings.Count(root, string(os.PathSeparator))
        
        filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
            if info.IsDir() {
                return nil
            }
            
            currentLevel := strings.Count(path, string(os.PathSeparator)) - rootLevel
            dirLevelStats[currentLevel]++
            return nil
        })
    }
    
    for level, count := range dirLevelStats {
        fmt.Printf("第 %d 层级文件数: %d 个\n", level, count)
    }
    
    // 显示前10个最大的JS和CSS文件
    fmt.Println("\n============= 最大 JS 文件 =============")
    listLargestFiles(dirPath, ".js", 10)
    
    fmt.Println("\n============= 最大 CSS 文件 =============")
    listLargestFiles(dirPath, ".css", 10)
}

// 列出指定类型的最大文件
func listLargestFiles(dirPath, fileExt string, count int) {
    type fileInfo struct {
        path string
        size int64
    }
    
    var files []fileInfo
    
    filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
        if err != nil {
            return nil
        }
        
        if !info.IsDir() && strings.ToLower(filepath.Ext(path)) == fileExt {
            files = append(files, fileInfo{
                path: path,
                size: info.Size(),
            })
        }
        return nil
    })
    
    // 按大小排序
    for i := 0; i < len(files); i++ {
        for j := i + 1; j < len(files); j++ {
            if files[i].size < files[j].size {
                files[i], files[j] = files[j], files[i]
            }
        }
    }
    
    // 显示前count个文件
    displayCount := count
    if len(files) < count {
        displayCount = len(files)
    }
    
    for i := 0; i < displayCount; i++ {
        relativePath, _ := filepath.Rel(dirPath, files[i].path)
        fmt.Printf("%d. %s (%.2f KB)\n", i+1, relativePath, float64(files[i].size)/1024)
    }
}