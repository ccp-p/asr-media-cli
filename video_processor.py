import os
import logging
import subprocess
import tempfile
from typing import Optional, List, Tuple
import json

class VideoProcessor:
    """视频处理器，提供视频相关操作"""
    
    @staticmethod
    def get_video_info(video_path: str) -> Optional[dict]:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return json.loads(result.stdout)
        except Exception as e:
            logging.error(f"获取视频信息失败: {str(e)}")
            return None
    
    @staticmethod
    def extract_audio_segment(video_path: str, start_time: float = 0, duration: Optional[float] = None) -> Optional[str]:
        """
        从视频提取指定时间段的音频
        
        Args:
            video_path: 视频文件路径
            start_time: 开始时间（秒）
            duration: 持续时间（秒），None表示到视频结束
            
        Returns:
            提取的音频文件路径
        """
        try:
            temp_dir = tempfile.gettempdir()
            video_filename = os.path.basename(video_path)
            audio_filename = f"{os.path.splitext(video_filename)[0]}_{start_time}"
            if duration:
                audio_filename += f"_{duration}"
            audio_filename += ".wav"
            audio_path = os.path.join(temp_dir, audio_filename)
            
            cmd = ['ffmpeg', '-i', video_path]
            
            # 添加时间参数
            if start_time > 0:
                cmd.extend(['-ss', str(start_time)])
            
            if duration:
                cmd.extend(['-t', str(duration)])
                
            cmd.extend([
                '-q:a', '0',
                '-map', 'a',
                '-y',
                audio_path
            ])
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return audio_path
        except Exception as e:
            logging.error(f"提取音频片段失败: {str(e)}")
            return None
    
    @staticmethod
    def segment_video_by_silence(video_path: str, 
                                 min_segment_length: float = 5.0,
                                 silence_threshold: int = -30,
                                 silence_duration: float = 0.5) -> List[Tuple[float, float]]:
        """
        根据静音将视频分割成片段
        
        Args:
            video_path: 视频文件路径
            min_segment_length: 最小片段长度（秒）
            silence_threshold: 静音阈值（dB）
            silence_duration: 静音持续时间（秒）
            
        Returns:
            分段列表，每个元素为 (开始时间, 持续时间) 的元组
        """
        try:
            # 提取整个音频
            audio_path = VideoProcessor.extract_audio_segment(video_path)
            if not audio_path:
                return []
            
            # 使用ffmpeg的silencedetect过滤器检测静音
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-af', f'silencedetect=noise={silence_threshold}dB:d={silence_duration}',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 解析静音检测结果
            silence_starts = []
            silence_ends = []
            
            for line in result.stderr.split('\n'):
                if 'silence_start' in line:
                    silence_starts.append(float(line.split('silence_start: ')[1].split(' ')[0]))
                elif 'silence_end' in line:
                    silence_ends.append(float(line.split('silence_end: ')[1].split(' ')[0]))
            
            # 获取视频总时长
            video_info = VideoProcessor.get_video_info(video_path)
            if not video_info:
                return []
                
            total_duration = float(video_info['format']['duration'])
            
            # 生成分段
            segments = []
            prev_end = 0.0
            
            for i in range(len(silence_starts)):
                segment_start = prev_end
                segment_end = silence_starts[i]
                segment_duration = segment_end - segment_start
                
                # 只保留长度超过最小片段长度的片段
                if segment_duration >= min_segment_length:
                    segments.append((segment_start, segment_duration))
                
                if i < len(silence_ends):
                    prev_end = silence_ends[i]
            
            # 添加最后一个片段
            if total_duration - prev_end >= min_segment_length:
                segments.append((prev_end, total_duration - prev_end))
            
            # 清理临时音频文件
            try:
                os.remove(audio_path)
            except:
                pass
                
            return segments
        except Exception as e:
            logging.error(f"视频分段失败: {str(e)}")
            return []
