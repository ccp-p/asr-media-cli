import logging
import os
from asr_manager import ASRManager
from video_processor import VideoProcessor

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # 初始化ASR管理器
    asr_manager = ASRManager(use_jianying_first=True, use_kuaishou=True)
    
    # 示例1: 直接识别整个视频
    video_path = "d:/project/my_py_project/input/example_video.mp4"
    if os.path.exists(video_path):
        print(f"识别视频: {video_path}")
        result = asr_manager.recognize_media(video_path)
        
        if result:
            print(f"识别结果: {result}")
        else:
            print("识别失败")
    
    # 示例2: 将视频按静音分段处理
    print(f"按静音分段处理视频: {video_path}")
    segments = VideoProcessor.segment_video_by_silence(video_path)
    
    all_results = []
    for i, (start, duration) in enumerate(segments):
        print(f"处理分段 {i+1}: 开始={start:.2f}秒, 持续={duration:.2f}秒")
        
        # 提取分段音频
        audio_segment = VideoProcessor.extract_audio_segment(
            video_path, start_time=start, duration=duration
        )
        
        if audio_segment:
            # 识别分段音频
            segment_result = asr_manager.recognize_audio(audio_segment)
            if segment_result:
                # 添加时间标记
                timed_result = f"[{start:.2f}-{start+duration:.2f}] {segment_result}"
                all_results.append(timed_result)
                print(f"分段 {i+1} 识别结果: {segment_result}")
            
            # 删除临时音频文件
            try:
                os.remove(audio_segment)
            except:
                pass
    
    # 输出完整结果
    if all_results:
        complete_result = "\n".join(all_results)
        print("\n完整识别结果:")
        print(complete_result)
        
        # 保存到文件
        output_file = os.path.join(os.path.dirname(video_path), 
                                  f"{os.path.splitext(os.path.basename(video_path))[0]}_transcript.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(complete_result)
        print(f"结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
