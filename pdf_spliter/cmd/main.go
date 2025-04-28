package main

import (
    "fmt"
    "os"
    "path/filepath"
    "strings"

    "github.com/pdfcpu/pdfcpu/pkg/api"
)

func splitPDFBySize(inputPath string, maxSizeMB int) ([]string, error) {
    // 将MB转换为字节
    maxSizeBytes := int64(maxSizeMB * 1024 * 1024)

    // 获取原始文件大小
    fileInfo, err := os.Stat(inputPath)
    if err != nil {
        return nil, fmt.Errorf("无法获取文件信息: %v", err)
    }

    // 如果文件已经小于限制大小，则不需要分割
    if fileInfo.Size() <= maxSizeBytes {
        fmt.Printf("文件大小为 %.2f MB，已经小于限制的 %d MB，无需分割\n", 
            float64(fileInfo.Size())/(1024*1024), maxSizeMB)
        return []string{inputPath}, nil
    }

    // 准备输出文件名
    baseName := strings.TrimSuffix(filepath.Base(inputPath), filepath.Ext(inputPath))
    outDir := filepath.Dir(inputPath)
    
    // 获取PDF总页数
    pageCount, err := api.PageCountFile(inputPath)
    if err != nil {
        return nil, fmt.Errorf("无法获取PDF页数: %v", err)
    }
    
    fmt.Printf("PDF文件共有 %d 页\n", pageCount)
    
    // 估算每页平均大小
    avgPageSize := fileInfo.Size() / int64(pageCount)
    // 估算每个分割文件的页数
    pagesPerFile := int(maxSizeBytes / avgPageSize)
    if pagesPerFile < 1 {
        pagesPerFile = 1 // 至少包含1页
    }
    
    fmt.Printf("预计每个分割文件包含约 %d 页\n", pagesPerFile)
    
    var outputFiles []string
    var startPage, endPage, partNum int

    // 分割PDF
    for startPage = 1; startPage <= pageCount; startPage = endPage + 1 {
        partNum++
        endPage = startPage + pagesPerFile - 1
        if endPage > pageCount {
            endPage = pageCount
        }
        
        outputPath := filepath.Join(outDir, fmt.Sprintf("%s_part%d.pdf", baseName, partNum))
        selectedPages := fmt.Sprintf("%d-%d", startPage, endPage)
        
        // 分割页面范围
        // 使用TrimFile而不是ExtractPagesFile
        err = api.TrimFile(inputPath, outputPath, []string{selectedPages}, nil)
        if err != nil {
            return outputFiles, fmt.Errorf("分割页面失败: %v", err)
        }
        
        // 检查分割后的文件大小
        outInfo, err := os.Stat(outputPath)
        if err != nil {
            return outputFiles, fmt.Errorf("获取分割文件信息失败: %v", err)
        }
        
        // 如果分割后的文件仍然过大，则减少页数重试
        if outInfo.Size() > maxSizeBytes {
            os.Remove(outputPath) // 删除过大的文件
            
            // 减少页数并重试
            oldPagesPerFile := pagesPerFile
            pagesPerFile = int(float64(pagesPerFile) * 0.7) // 减少30%的页数
            if pagesPerFile < 1 {
                pagesPerFile = 1
            }
            
            if pagesPerFile == 1 && oldPagesPerFile == 1 {
                // 已经尝试了最小页数，无法满足大小要求
                return outputFiles, fmt.Errorf("单页PDF大于最大允许大小，无法分割")
            }
            
            // 重置开始页以重试此部分
            startPage -= pagesPerFile
            continue
        }
        
        outputFiles = append(outputFiles, outputPath)
        fmt.Printf("已创建: %s (%.2f MB, 页码 %d-%d)\n", 
            outputPath, float64(outInfo.Size())/(1024*1024), startPage, endPage)
        
        // 动态调整页数，使后续分割更准确
        actualFileSize := outInfo.Size()
        actualPages := endPage - startPage + 1
        if actualPages > 0 {
            // 更新估计的页面大小
            newAvgPageSize := actualFileSize / int64(actualPages)
            // 平滑过渡到新的平均页面大小
            avgPageSize = (avgPageSize + newAvgPageSize) / 2
            // 重新计算每个文件的页数
            pagesPerFile = int((maxSizeBytes * 95 / 100) / avgPageSize) // 预留5%的余量
            if pagesPerFile < 1 {
                pagesPerFile = 1
            }
        }
    }
    
    return outputFiles, nil
}

func main() {
    // 使用固定路径，需要确保文件存在且是PDF文件
    var inputPath string
    // if len(os.Args) < 2 || os.Args[1] == "" {
    //     fmt.Println("请提供一个PDF文件名作为参数。")
    //     os.Exit(1)
    // } else {
    //     inputPath = filepath.Join("D://download", os.Args[1])
    // }
    inputPath = "D://download//liaodao4.pdf"
    maxSizeMB := 99 // 默认略小于100MB
    
    fmt.Printf("正在将 %s 分割为最大 %d MB 的多个部分...\n", inputPath, maxSizeMB)
    
    outputFiles, err := splitPDFBySize(inputPath, maxSizeMB)
    if err != nil {
        fmt.Printf("分割PDF时出错: %v\n", err)
        os.Exit(1)
    }
    
    fmt.Printf("成功分割PDF为%d个文件:\n", len(outputFiles))
    for i, file := range outputFiles {
        fileInfo, _ := os.Stat(file)
        fmt.Printf("%d. %s (%.2f MB)\n", i+1, file, float64(fileInfo.Size())/(1024*1024))
    }
}