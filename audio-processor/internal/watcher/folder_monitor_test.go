package watcher

import (
	"os"
	"path/filepath"
	"testing"
)

func TestOnFileModified(t *testing.T) {
	// 创建一个临时文件夹作为目标文件夹
	targetDir, err := os.MkdirTemp("", "test-target")
	if err != nil {
		t.Fatalf("无法创建临时目录: %v", err)
	}
	defer os.RemoveAll(targetDir)

	// 创建处理器
	handler := NewFileMovementHandler(targetDir)
	
	// 调用OnFileModified
	handler.OnFileModified("test.mp3")
	// 目前该方法是空实现，我们只检查调用不会产生panic
}

func TestOnFileDeleted(t *testing.T) {
	// 创建一个临时文件夹作为目标文件夹
	targetDir, err := os.MkdirTemp("", "test-target")
	if err != nil {
		t.Fatalf("无法创建临时目录: %v", err)
	}
	defer os.RemoveAll(targetDir)

	// 创建处理器
	handler := NewFileMovementHandler(targetDir)
	
	// 添加一个测试文件到processedFiles
	testFile := "test_file.mp3"
	handler.processedFiles[testFile] = true
	
	// 确认文件在映射中
	if !handler.processedFiles[testFile] {
		t.Fatal("测试文件应该在processedFiles映射中")
	}
	
	// 调用OnFileDeleted
	handler.OnFileDeleted(testFile)
	
	// 验证文件已从映射中删除
	if handler.processedFiles[testFile] {
		t.Fatal("测试文件应该已从processedFiles映射中删除")
	}
}

func TestMoveFile(t *testing.T) {
	// 创建一个临时文件夹作为源文件夹
	sourceDir, err := os.MkdirTemp("", "test-source")
	if err != nil {
		t.Fatalf("无法创建临时源目录: %v", err)
	}
	defer os.RemoveAll(sourceDir)
	
	// 创建一个临时文件夹作为目标文件夹
	targetDir, err := os.MkdirTemp("", "test-target")
	if err != nil {
		t.Fatalf("无法创建临时目标目录: %v", err)
	}
	defer os.RemoveAll(targetDir)
	
	// 创建处理器
	handler := NewFileMovementHandler(targetDir)
	
	// 创建测试文件
	testFileName := "test_file.mp3"
	testFilePath := filepath.Join(sourceDir, testFileName)
	testContent := []byte("test content")
	if err := os.WriteFile(testFilePath, testContent, 0644); err != nil {
		t.Fatalf("无法创建测试文件: %v", err)
	}
	
	// 测试基本的文件移动
	handler.moveFile(testFilePath)
	
	// 验证文件已移动
	movedFilePath := filepath.Join(targetDir, testFileName)
	if _, err := os.Stat(movedFilePath); os.IsNotExist(err) {
		t.Fatalf("文件应该被移动到目标目录: %v", err)
	}
	
	// 验证文件内容正确
	movedContent, err := os.ReadFile(movedFilePath)
	if err != nil {
		t.Fatalf("无法读取移动后的文件: %v", err)
	}
	if string(movedContent) != string(testContent) {
		t.Fatalf("移动后的文件内容不正确")
	}
	
	// 测试重名文件处理
	// 创建新的测试文件
	testFilePath = filepath.Join(sourceDir, testFileName)
	if err := os.WriteFile(testFilePath, testContent, 0644); err != nil {
		t.Fatalf("无法创建重名测试文件: %v", err)
	}
	
	// 移动文件
	handler.moveFile(testFilePath)
	
	// 检查目标目录中的文件数量
	files, err := os.ReadDir(targetDir)
	if err != nil {
		t.Fatalf("无法读取目标目录: %v", err)
	}
	if len(files) != 2 {
		t.Fatalf("目标目录中应该有两个文件，实际有 %d 个", len(files))
	}
	
	// 确认第二个文件名包含时间戳
	timestampFound := false
	for _, file := range files {
		if file.Name() != testFileName && len(file.Name()) > len(testFileName) {
			timestampFound = true
			// 验证内容
			timestampedContent, err := os.ReadFile(filepath.Join(targetDir, file.Name()))
			if err != nil {
				t.Fatalf("无法读取带时间戳的文件: %v", err)
			}
			if string(timestampedContent) != string(testContent) {
				t.Fatalf("带时间戳的文件内容不正确")
			}
			break
		}
	}
	
	if !timestampFound {
		t.Fatal("未能找到带时间戳的文件")
	}
}
