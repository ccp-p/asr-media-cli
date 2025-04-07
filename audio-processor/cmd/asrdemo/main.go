package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/asr"
	"github.com/ccp-p/asr-media-cli/audio-processor/pkg/utils"
)

func main() {
	// 解析命令行参数
	audioPath := flag.String("audio", "D:\\download\\dest\\test.mp3", "音频文件路径")
	service := flag.String("service", "auto", "ASR服务选择 (kuaishou, auto)")
	useCache := flag.Bool("cache", true, "是否使用缓存")
	logLevel := flag.String("log-level", utils.LogLevelNormal, "日志级别")
	logFile := flag.String("log-file", "", "日志文件路径")
	
	flag.Parse()
	
	// 初始化日志
	if err := utils.InitLogger(*logLevel, *logFile); err != nil {
		fmt.Fprintf(os.Stderr, "初始化日志失败: %v\n", err)
		os.Exit(1)
	}
	
	// 检查音频文件路径
	if *audioPath == "" {
		utils.Log.Fatal("必须指定音频文件路径")
	}
	
	// 创建上下文
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	
	// 创建ASR选择器
	selector := asr.NewASRSelector()
	
	// 注册服务
	selector.RegisterService("kuaishou",func(audioPath string, useCache bool) (asr.ASRService, error) {
        // 调用原始函数，它返回 *KuaiShouASR
        service, err := asr.NewKuaiShouASR(audioPath, useCache)
        // 返回时，Go 会自动将 *KuaiShouASR 转换为 ASRService 接口
        return service, err
    },  10)
	// TODO: 注册更多ASR服务
	
	utils.Log.Info("开始识别音频文件...")
	
	// 进度回调
	progressCallback := func(percent int, message string) {
		utils.Log.Infof("进度 [%d%%] %s", percent, message)
	}
	
	// 执行识别
	start := time.Now()
	segments, serviceName, err := selector.RunWithService(ctx, *audioPath, *service, *useCache, progressCallback)
	if err != nil {
		utils.Log.Fatalf("识别失败: %v", err)
	}
	
	duration := time.Since(start)
	utils.Log.Infof("使用 %s 服务识别完成，耗时 %.2f 秒", serviceName, duration.Seconds())
	
	// 输出结果
	if len(segments) == 0 {
		utils.Log.Info("未识别出任何内容")
		return
	}
	
	utils.Log.Infof("识别结果 (%d 段):", len(segments))
	for i, seg := range segments {
		utils.Log.Infof("[%02d] %.2f-%.2f: %s", i+1, seg.StartTime, seg.EndTime, seg.Text)
	}
	
	// 输出服务统计信息
	stats := selector.GetStats()
	utils.Log.Info("ASR服务统计信息:")
	for name, stat := range stats {
		utils.Log.Infof("%s: 调用次数=%d, 成功率=%s, 可用=%v", 
			name, stat["count"], stat["success_rate"], stat["available"])
	}
}
