"""
音频提取和分割模块
负责从视频中提取音频以及将音频分割成小片段
"""
import os
import logging
import subprocess
from typing import List, Optional, Callable, Tuple
from pydub import AudioSegment

class AudioExtractor:
    """音频提取器，负责音频提取和分割"""

    def __init__(self, temp_segments_dir: str, progress_callback: Optional[Callable] = None):
        """
        初始化音频提取器
        
        Args:
            temp_segments_dir: 临时片段存储目录
            progress_callback: 进度回调函数，接受 (current, total, message) 参数
        """
        self.temp_segments_dir = temp_segments_dir
        self.progress_callback = progress_callback
        
        # 确保临时目录存在
        os.makedirs(self.temp_segments_dir, exist_ok=True)
    
    def split_audio_file(self, input_path: str, segment_length: int = 30) -> List[str]:
        """
        将音频文件分割为较小片段
        
        Args:
            input_path: 输入音频文件路径
            segment_length: 每个片段的长度(秒)
            
        Returns:
            分割后的片段文件列表
        """
        filename = os.path.basename(input_path)
        logging.info(f"正在分割 {filename} 为小片段...")
        
        # 加载音频文件
        audio = AudioSegment.from_file(input_path)
        
        # 计算总时长（毫秒转秒）
        total_duration = len(audio) // 1000
        logging.info(f"音频总时长: {total_duration}秒")
        
        # 预计片段数
        expected_segments = (total_duration + segment_length - 1) // segment_length
        
        # 报告初始进度
        if self.progress_callback:
            self.progress_callback(0, expected_segments, "准备分割音频")
        
        segment_files = []
        
        # 分割音频
        for i, start in enumerate(range(0, total_duration, segment_length)):
            end = min(start + segment_length, total_duration)
            segment = audio[start*1000:end*1000]
            
            # 导出为WAV格式（兼容语音识别API）
            output_filename = f"{os.path.splitext(filename)[0]}_part{i+1:03d}.wav"
            output_path = os.path.join(self.temp_segments_dir, output_filename)
            
            # 更新进度
            if self.progress_callback:
                self.progress_callback(
                    i, 
                    expected_segments, 
                    f"导出片段 {i+1}/{expected_segments}"
                )
            
            # 导出音频段
            try:
                logging.debug(f"  ├─ 导出片段到: {output_path}")
                segment.export(
                    output_path,
                    format="wav",
                    parameters=["-ac", "1", "-ar", "16000"]  # 单声道，16kHz采样率
                )
                segment_files.append(output_filename)
                logging.debug(f"  ├─ 分割完成: {output_filename}")
            except Exception as e:
                logging.error(f"  ├─ 导出片段失败: {output_path}, 错误: {str(e)}")
                raise
        
        # 完成进度
        if self.progress_callback:
            self.progress_callback(
                expected_segments, 
                expected_segments, 
                f"完成 - {len(segment_files)} 个片段"
            )
        
        return segment_files

    def extract_audio_from_video(self, video_path: str, output_folder: str, 
                               progress_callback: Optional[Callable] = None) -> tuple:
        """
        从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            output_folder: 输出音频的目录
            progress_callback: 特定于此操作的进度回调函数
            
        Returns:
            tuple: (音频文件路径, 是否是新提取的), 失败则返回(None, False)
        """
        try:
            video_filename = os.path.basename(video_path)
            base_name = os.path.splitext(video_filename)[0]
            audio_path = os.path.join(output_folder, f"{base_name}.mp3")
            
            # 检查音频文件是否已经存在
            if os.path.exists(audio_path):
                logging.info(f"音频已存在: {audio_path}")
                return audio_path, False
            
            # 报告进度
            if progress_callback:
                progress_callback(0, 1, "准备提取音频")
            
            # 使用FFmpeg提取音频
            cmd = [
                'ffmpeg', '-i', video_path, 
                '-q:a', '0', '-map', 'a', audio_path, 
                '-y'  # 覆盖已存在的文件
            ]
            
            logging.info(f"正在从视频提取音频: {video_filename}")
            
            # 执行命令
            process = subprocess.run(cmd, check=True, capture_output=True)
            
            if os.path.exists(audio_path):
                logging.info(f"音频提取成功: {audio_path}")
                # 完成进度
                if progress_callback:
                    progress_callback(1, 1, "提取完成")
                return audio_path, True
            else:
                logging.error(f"音频提取失败: {video_filename}")
                # 失败进度
                if progress_callback:
                    progress_callback(1, 1, "提取失败")
                return None, False
                
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg处理失败: {e}")
            if progress_callback:
                progress_callback(1, 1, f"处理失败: FFmpeg错误")
            return None, False
        except Exception as e:
            logging.error(f"提取音频时发生错误: {str(e)}")
            if progress_callback:
                progress_callback(1, 1, f"处理失败: {str(e)}")
            return None, False