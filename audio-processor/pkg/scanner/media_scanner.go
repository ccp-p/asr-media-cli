package scanner

import (
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

// MediaFile 表示一个媒体文件
type MediaFile struct {
	Path      string    // 文件路径
	Name      string    // 文件名
	Ext       string    // 文件扩展名
	Size      int64     // 文件大小（字节）
	ModTime   time.Time // 修改时间
	IsVideo   bool      // 是否为视频文件
	IsAudio   bool      // 是否为音频文件
	Processed bool      // 是否已处理
}

// MediaScanner 用于扫描媒体文件
type MediaScanner struct {
	AudioExtensions []string
	VideoExtensions []string
}

// NewMediaScanner 创建新的媒体扫描器
func NewMediaScanner() *MediaScanner {
	return &MediaScanner{
		AudioExtensions: []string{".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"},
		VideoExtensions: []string{".mp4", ".mov", ".avi", ".mkv", ".wmv"},
	}
}

// ScanDirectory 扫描指定目录中的媒体文件
func (s *MediaScanner) ScanDirectory(dir string) ([]MediaFile, error) {
	var mediaFiles []MediaFile

	logrus.Infof("开始扫描目录: %s", dir)
	
	  // 读取目录内容（非递归）
	  entries, err := os.ReadDir(dir)
	  if err != nil {
		  return nil, err
	  }
	  
	  for _, entry := range entries {
		  // 跳过目录和隐藏文件
		  if entry.IsDir() || strings.HasPrefix(entry.Name(), ".") {
			  continue
		  }
		  
		  // 获取文件信息
		  info, err := entry.Info()
		  if err != nil {
			  logrus.Warnf("获取文件信息失败: %v", err)
			  continue
		  }
		  
		  path := filepath.Join(dir, entry.Name())
		  ext := strings.ToLower(filepath.Ext(path))
		  
		  // 检查是否为音频文件
		  isAudio := false
		  for _, audioExt := range s.AudioExtensions {
			  if ext == audioExt {
				  isAudio = true
				  break
			  }
		  }
		  
		  // 检查是否为视频文件
		  isVideo := false
		  for _, videoExt := range s.VideoExtensions {
			  if ext == videoExt {
				  isVideo = true
				  break
			  }
		  }
		  
		  // 如果是媒体文件，添加到结果列表
		  if isAudio || isVideo {
			  mediaFiles = append(mediaFiles, MediaFile{
				  Path:      path,
				  Name:      entry.Name(),
				  Ext:       ext,
				  Size:      info.Size(),
				  ModTime:   info.ModTime(),
				  IsVideo:   isVideo,
				  IsAudio:   isAudio,
				  Processed: false,
			  })
		  }
	  }
	
	logrus.Infof("扫描完成，共找到 %d 个媒体文件", len(mediaFiles))
	
	return mediaFiles, err
}

// FilterNewFiles 根据已处理记录过滤出新文件
func (s *MediaScanner) FilterNewFiles(files []MediaFile, processedPaths map[string]bool) []MediaFile {
	var newFiles []MediaFile
	
	for _, file := range files {
		if !processedPaths[file.Path] {
			newFiles = append(newFiles, file)
		}
	}
	
	logrus.Infof("过滤后剩余 %d 个新文件需要处理", len(newFiles))
	
	return newFiles
}
