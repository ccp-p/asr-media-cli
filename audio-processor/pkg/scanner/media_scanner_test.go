package scanner

import (
	"os"
	"path/filepath"
	"testing"
)

// 创建测试目录和测试文件
func setupTestDirectory(t *testing.T) (string, func()) {
	// 创建临时目录
	tempDir, err := os.MkdirTemp("", "media_scanner_test")
	if err != nil {
		t.Fatalf("创建临时目录失败: %v", err)
	}
	
	// 创建测试文件
	testFiles := map[string]bool{
		"audio1.mp3":      true,  // 音频文件
		"audio2.wav":      true,  // 音频文件
		"video1.mp4":      true,  // 视频文件
		"document.pdf":    false, // 非媒体文件
		"image.jpg":       false, // 非媒体文件
		".hidden.mp3":     false, // 隐藏文件
		"subfolder/a.mp3": true,  // 子文件夹中的音频文件
	}
	
	// 创建子文件夹
	if err := os.MkdirAll(filepath.Join(tempDir, "subfolder"), 0755); err != nil {
		t.Fatalf("创建子文件夹失败: %v", err)
	}
	
	// 创建所有测试文件
	for fileName, _ := range testFiles {
		filePath := filepath.Join(tempDir, fileName)
		if err := os.WriteFile(filePath, []byte("test content"), 0644); err != nil {
			t.Fatalf("创建测试文件失败 %s: %v", fileName, err)
		}
	}
	
	// 返回清理函数
	cleanup := func() {
		os.RemoveAll(tempDir)
	}
	
	return tempDir, cleanup
}

func TestScanDirectory(t *testing.T) {
    // 设置测试目录
    testDir, cleanup := setupTestDirectory(t)
    defer cleanup()
    
    // 创建扫描器
    scanner := NewMediaScanner()
    files, err := scanner.ScanDirectory(testDir)
    
    // 检查是否有错误
    if err != nil {
        t.Fatalf("扫描目录失败: %v", err)
    }
    
    // 期望找到的媒体文件数量（不包括隐藏文件和子目录文件）
    expectedFiles := 3 // 只有：audio1.mp3, audio2.wav, video1.mp4
    
    if len(files) != expectedFiles {
        t.Errorf("期望找到 %d 个媒体文件，实际找到 %d 个", expectedFiles, len(files))
    }
    
    // 验证媒体文件类型识别正确
    foundAudio := 0
    foundVideo := 0
    
    for _, file := range files {
        if file.IsAudio {
            foundAudio++
        }
        if file.IsVideo {
            foundVideo++
        }
        
        // 确保每个文件都有有效的元数据
        if file.Name == "" || file.Path == "" || file.Ext == "" || file.Size == 0 {
            t.Errorf("文件元数据不完整: %+v", file)
        }
    }
    
    if foundAudio != 2 { // 只有：audio1.mp3, audio2.wav
        t.Errorf("期望找到 2 个音频文件，实际找到 %d 个", foundAudio)
    }
    
    if foundVideo != 1 { // video1.mp4
        t.Errorf("期望找到 1 个视频文件，实际找到 %d 个", foundVideo)
    }
}
func TestFilterNewFiles(t *testing.T) {
	// 创建测试文件列表
	testFiles := []MediaFile{
		{Path: "/path/to/file1.mp3", Name: "file1.mp3", IsAudio: true},
		{Path: "/path/to/file2.mp4", Name: "file2.mp4", IsVideo: true},
		{Path: "/path/to/file3.wav", Name: "file3.wav", IsAudio: true},
	}
	
	// 创建已处理文件记录
	processedPaths := map[string]bool{
		"/path/to/file1.mp3": true, // 已处理
	}
	
	// 创建扫描器
	scanner := NewMediaScanner()
	
	// 过滤文件
	newFiles := scanner.FilterNewFiles(testFiles, processedPaths)
	
	// 检查过滤结果
	if len(newFiles) != 2 {
		t.Errorf("期望过滤后剩余 2 个文件，实际有 %d 个", len(newFiles))
	}
	
	// 检查具体文件
	for _, file := range newFiles {
		if file.Path == "/path/to/file1.mp3" {
			t.Errorf("已处理文件未被过滤: %s", file.Path)
		}
	}
}
