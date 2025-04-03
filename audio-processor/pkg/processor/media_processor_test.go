package processor

import (
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

// 跳过测试的辅助函数（在没有安装FFmpeg的环境中使用）
func skipIfNoFFmpeg(t *testing.T) {
	cmd := exec.Command("ffmpeg", "-version")
	if err := cmd.Run(); err != nil {
		t.Skip("跳过测试：未安装FFmpeg")
	}
}

// 创建测试媒体文件
func createTestMediaFile(t *testing.T, dir string) (string, func()) {
	// 我们需要一个真实的音频文件用于测试
	// 这里创建一个极小的测试音频
	testFile := filepath.Join(dir, "test.mp3")
	
	// 使用FFmpeg生成一个1秒的测试音频
	cmd := exec.Command(
		"ffmpeg",
		"-f", "lavfi",
		"-i", "sine=frequency=1000:duration=1",
		"-c:a", "libmp3lame",
		"-q:a", "9",
		testFile,
		"-y",
	)
	
	if err := cmd.Run(); err != nil {
		t.Fatalf("创建测试音频文件失败: %v", err)
	}
	
	cleanup := func() {
		os.Remove(testFile)
	}
	
	return testFile, cleanup
}

func TestCheckFFmpeg(t *testing.T) {
	// 创建处理器
	processor := NewMediaProcessor("", "")
	
	// 检查FFmpeg
	ffmpegAvailable := processor.CheckFFmpeg()
	
	// 如果我们检测到FFmpeg，系统中应该安装了它
	// 注意：这个测试更多是确认函数工作正常，而不是确保FFmpeg真的存在
	t.Logf("FFmpeg可用: %v", ffmpegAvailable)
}

func TestGetMediaInfo(t *testing.T) {
	// 如果没有FFmpeg，跳过测试
	skipIfNoFFmpeg(t)
	
	// 创建临时目录
	tempDir, err := ioutil.TempDir("", "media_processor_test")
	if err != nil {
		t.Fatalf("创建临时目录失败: %v", err)
	}
	defer os.RemoveAll(tempDir)
	
	// 创建测试媒体文件
	testFile, cleanup := createTestMediaFile(t, tempDir)
	defer cleanup()
	
	// 创建处理器
	processor := NewMediaProcessor(tempDir, tempDir)
	
	// 获取媒体信息
	info, err := processor.GetMediaInfo(testFile)
	if err != nil {
		t.Fatalf("获取媒体信息失败: %v", err)
	}
	
	// 验证媒体信息
	if info.Path != testFile {
		t.Errorf("路径不匹配: 期望 %s, 实际 %s", testFile, info.Path)
	}
	
	if info.Name != filepath.Base(testFile) {
		t.Errorf("文件名不匹配: 期望 %s, 实际 %s", filepath.Base(testFile), info.Name)
	}
	
	if info.Format != "mp3" {
		t.Errorf("格式不匹配: 期望 mp3, 实际 %s", info.Format)
	}
	
	// 一秒的测试文件
	if info.Duration < 0.9 || info.Duration > 1.1 {
		t.Errorf("时长不在预期范围内: %f", info.Duration)
	}
	
	// 检查采样率和声道
	if info.SampleRate <= 0 {
		t.Errorf("采样率无效: %d", info.SampleRate)
	}
	
	if info.Channels <= 0 {
		t.Errorf("声道数无效: %d", info.Channels)
	}
	
	// 检查文件大小
	if info.Size <= 0 {
		t.Errorf("文件大小无效: %d", info.Size)
	}
}


func TestExtractAudioFromVideo(t *testing.T) {
	// 如果没有FFmpeg，跳过测试
	skipIfNoFFmpeg(t)
	
	// 创建临时目录
	tempDir, err := ioutil.TempDir("", "media_processor_test")
	if err != nil {
		t.Fatalf("创建临时目录失败: %v", err)
	}
	defer os.RemoveAll(tempDir)
	
	// 创建测试视频文件 (1秒测试视频)
	testVideo := filepath.Join(tempDir, "test.mp4")
	cmd := exec.Command(
		"ffmpeg",
		"-f", "lavfi",
		"-i", "testsrc=duration=1:size=320x240:rate=30",
		"-f", "lavfi",
		"-i", "sine=frequency=1000:duration=1",
		"-c:v", "libx264",
		"-c:a", "aac",
		testVideo,
		"-y",
	)
	
	if err := cmd.Run(); err != nil {
		t.Skip("创建测试视频失败，跳过测试")
		return
	}
	
	// 创建处理器
	processor := NewMediaProcessor(tempDir, tempDir)
	
	// 从视频提取音频
	audioPath, err := processor.ExtractAudioFromVideo(testVideo)
	if err != nil {
		t.Fatalf("从视频提取音频失败: %v", err)
	}
	
	// 验证提取的音频文件存在
	if _, err := os.Stat(audioPath); os.IsNotExist(err) {
		t.Errorf("提取的音频文件不存在: %s", audioPath)
	}
	
	// 验证音频文件格式
	if filepath.Ext(audioPath) != ".mp3" {
		t.Errorf("提取的音频文件格式不是MP3: %s", audioPath)
	}
}
