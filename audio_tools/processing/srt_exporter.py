"""
SRT字幕导出模块
负责将音频转写结果导出为SRT格式字幕文件
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

class SRTExporter:
    """SRT字幕导出器"""
    
    def __init__(self, output_folder: str):
        """
        初始化SRT导出器
        
        Args:
            output_folder: 输出文件夹路径
        """
        self.output_folder = output_folder
        
    def format_srt_time(self, seconds: float) -> str:
        """
        将秒数格式化为SRT时间格式 (HH:MM:SS,mmm)
        
        Args:
            seconds: 时间（秒）
            
        Returns:
            SRT格式时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def generate_srt_content(self, segments: List[Dict[str, Any]]) -> str:
        """
        生成SRT格式内容
        
        Args:
            segments: 包含文本和时间戳的片段列表
                      [{'text': '文本内容', 'start': 开始时间(秒), 'end': 结束时间(秒)}]
            
        Returns:
            SRT格式文本内容
        """
        srt_lines = []
        
        for i, segment in enumerate(segments, 1):
            # 获取文本和时间戳
            text = segment.get('text', '').strip()
            if not text:
                continue
                
            start_time = segment.get('start', 0)
            end_time = segment.get('end', start_time + 5)  # 默认5秒
            
            # 格式化SRT条目
            srt_start = self.format_srt_time(start_time)
            srt_end = self.format_srt_time(end_time)
            
            # 添加序号、时间范围和文本
            srt_lines.append(f"{i}")
            srt_lines.append(f"{srt_start} --> {srt_end}")
            srt_lines.append(f"{text}")
            srt_lines.append("")  # 空行分隔
            
        return "\n".join(srt_lines)
    
    def convert_timestamps_to_segments(self, 
                                      texts: List[str], 
                                      timestamps: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        将文本和时间戳列表转换为分段列表
        
        Args:
            texts: 文本列表
            timestamps: 对应的时间戳列表
            
        Returns:
            分段列表，适合SRT生成
        """
        segments = []
        
        for i, text in enumerate(texts):
            if not text or text == "[无法识别的音频片段]":
                continue
                
            if i < len(timestamps):
                segment = {
                    'text': text,
                    'start': timestamps[i].get('start', i * 30),
                    'end': timestamps[i].get('end', (i + 1) * 30)
                }
                segments.append(segment)
                
        return segments
    
    def export_srt(self, 
                  segments: List[Dict[str, Any]], 
                  filename: str, 
                  part_num: Optional[int] = None) -> str:
        """
        导出SRT格式字幕文件
        
        Args:
            segments: 文本片段列表
            filename: 文件名（不含扩展名）
            part_num: 可选的部分编号
            
        Returns:
            SRT文件路径
        """
        try:
            # 创建输出文件夹
            os.makedirs(self.output_folder, exist_ok=True)
            
            # 构建文件名
            base_name = os.path.splitext(os.path.basename(filename))[0]
            if part_num is not None:
                output_subfolder = os.path.join(self.output_folder, base_name)
                os.makedirs(output_subfolder, exist_ok=True)
                output_file = os.path.join(output_subfolder, f"{base_name}_part{part_num}.srt")
            else:
                output_file = os.path.join(self.output_folder, f"{base_name}.srt")
            
            # 生成SRT内容
            srt_content = self.generate_srt_content(segments)
            
            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(srt_content)
                
            logging.info(f"已导出SRT字幕: {output_file}")
            return output_file
            
        except Exception as e:
            error_msg = f"导出SRT字幕失败: {str(e)}"
            logging.error(error_msg)
            raise IOError(error_msg)
