"""
文本处理模块
负责格式化转写结果和生成文本文件
"""
import os
import re
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

class TextFormatError(Exception):
    """文本格式化错误"""
    pass

class TextProcessor:
    """文本处理器，负责文本格式化和结果输出"""
    
    def __init__(self, 
                output_folder: str,
                format_text: bool = True,
                include_timestamps: bool = True,
                progress_callback: Optional[Callable] = None,
                max_segment_length: int = 2000,
                min_segment_length: int = 10):
        """
        初始化文本处理器
        
        Args:
            output_folder: 输出文件夹路径
            format_text: 是否格式化文本
            include_timestamps: 是否包含时间戳
            progress_callback: 进度回调函数
            max_segment_length: 最大段落长度
            min_segment_length: 最小段落长度
        """
        self.output_folder = output_folder
        self.format_text = format_text
        self.include_timestamps = include_timestamps
        self.progress_callback = progress_callback
        self.max_segment_length = max_segment_length
        self.min_segment_length = min_segment_length
        
    def prepare_result_text(self, 
                          segment_files: List[str], 
                          segment_results: Dict[int, str],
                          start_segment: int = 0,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        准备最终的识别结果文本
        
        Args:
            segment_files: 所有音频片段文件名列表
            segment_results: 识别结果字典
            start_segment: 当前部分的起始片段索引
            metadata: 可选的元数据信息
            
        Returns:
            合并格式化后的文本
        """
        if not segment_files:
            return ""
        
        if self.progress_callback:
            self.progress_callback(
                'text_preparation',
                0,
                len(segment_files),
                "准备处理文本"
            )
        
        all_text = []
        all_timestamps = []
        
        # 处理所有文本片段
        for i, segment_file in enumerate(segment_files):
            # 计算全局时间戳索引 (考虑当前部分的起始位置)
            global_idx = start_segment + i
            
            if i in segment_results:
                text = segment_results[i].strip()
                if text:  # 只添加非空文本
                    all_text.append(text)
                    # 计算连续的时间戳，每个片段30秒
                    all_timestamps.append({
                        'start': global_idx * 30,
                        'end': (global_idx + 1) * 30
                    })
            else:
                all_text.append("[无法识别的音频片段]")
                all_timestamps.append({
                    'start': global_idx * 30,
                    'end': (global_idx + 1) * 30
                })
            
            # 更新进度
            if self.progress_callback:
                self.progress_callback(
                    'text_preparation',
                    i + 1,
                    len(segment_files),
                    f"处理片段 {i+1}/{len(segment_files)}"
                )
        
        try:
            # 格式化文本
            if self.format_text:
                if self.progress_callback:
                    self.progress_callback(
                        'format_text',
                        0,
                        1,
                        "正在格式化文本"
                    )
                
                full_text = self._format_text(
                    all_text,
                    timestamps=all_timestamps if self.include_timestamps else None
                )
                
                if self.progress_callback:
                    self.progress_callback(
                        'format_text',
                        1,
                        1,
                        "格式化完成"
                    )
            else:
                # 如果不格式化，直接合并文本
                full_text = "\n\n".join([text for text in all_text if text and text != "[无法识别的音频片段]"])
            
            # 添加元数据信息
            if metadata:
                header = self._generate_metadata_header(metadata)
                full_text = f"{header}\n\n{full_text}"
            
            return full_text
            
        except Exception as e:
            error_msg = f"格式化文本时出错: {str(e)}"
            logging.error(error_msg)
            raise TextFormatError(error_msg)
    
    def save_result_text(self, 
                        text: str, 
                        filename: str, 
                        part_num: Optional[int] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        保存转写结果到文件
        
        Args:
            text: 要保存的文本内容
            filename: 原始音频文件名
            part_num: 可选的部分编号
            metadata: 可选的元数据信息
            
        Returns:
            输出文件路径
        """
        try:
            base_name = os.path.splitext(filename)[0]
            output_subfolder = self.get_output_subfolder(base_name)
            
            if part_num is not None:
                output_file = os.path.join(output_subfolder, f"{base_name}_part{part_num}.txt")
            else:
                output_file = os.path.join(output_subfolder, f"{base_name}.txt")
            
            # 准备文件头信息
            header = f"# {base_name}"
            if part_num is not None:
                header += f" - 第 {part_num} 部分"
            header += f"\n# 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if metadata:
                header += self._generate_metadata_header(metadata)
            
            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"{header}\n\n{text}")
            
            return output_file
            
        except Exception as e:
            error_msg = f"保存文本文件时出错: {str(e)}"
            logging.error(error_msg)
            raise IOError(error_msg)
    
    def get_output_subfolder(self, base_name: str) -> str:
        """
        获取输出子文件夹路径
        
        Args:
            base_name: 文件基本名称(不含扩展名)
            
        Returns:
            子文件夹路径
        """
        output_subfolder = os.path.join(self.output_folder, base_name)
        os.makedirs(output_subfolder, exist_ok=True)
        return output_subfolder
    
    def _format_text(self, 
                    texts: List[str], 
                    timestamps: Optional[List[Dict[str, int]]] = None) -> str:
        """
        格式化文本片段
        
        Args:
            texts: 文本片段列表
            timestamps: 对应的时间戳列表
            
        Returns:
            格式化后的文本
        """
        formatted_segments = []
        current_segment = []
        current_length = 0
        
        for i, text in enumerate(texts):
            if not text or text == "[无法识别的音频片段]":
                continue
            
            # 分割过长的句子
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # 如果当前段落加上新句子会超过最大长度，保存当前段落并开始新段落
                if current_length + len(sentence) > self.max_segment_length and current_length >= self.min_segment_length:
                    if current_segment:
                        segment_text = " ".join(current_segment)
                        # 添加时间戳
                        if timestamps and self.include_timestamps:
                            timestamp = timestamps[i]
                            time_str = self._format_timestamp(timestamp)
                            formatted_segments.append(f"{time_str} {segment_text}")
                        else:
                            formatted_segments.append(segment_text)
                        current_segment = []
                        current_length = 0
                
                current_segment.append(sentence)
                current_length += len(sentence)
        
        # 处理最后一个段落
        if current_segment:
            segment_text = " ".join(current_segment)
            if timestamps and self.include_timestamps and timestamps[-1]:
                time_str = self._format_timestamp(timestamps[-1])
                formatted_segments.append(f"{time_str} {segment_text}")
            else:
                formatted_segments.append(segment_text)
        
        return "\n\n".join(formatted_segments)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        将文本分割成句子
        
        Args:
            text: 要分割的文本
            
        Returns:
            句子列表
        """
        # 使用正则表达式分割句子，保留标点符号
        sentences = re.split(r'([。！？.!?]+)', text)
        
        # 重新组合句子和标点
        result = []
        i = 0
        while i < len(sentences) - 1:
            if sentences[i].strip():
                sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
                result.append(sentence.strip())
            i += 2
            
        # 处理最后一个句子
        if i < len(sentences) and sentences[i].strip():
            result.append(sentences[i].strip())
        
        return result
    
    def _format_timestamp(self, timestamp: Dict[str, int]) -> str:
        """
        格式化时间戳
        
        Args:
            timestamp: 包含开始和结束时间的字典
            
        Returns:
            格式化的时间戳字符串
        """
        minutes_start = timestamp['start'] // 60
        seconds_start = timestamp['start'] % 60
        minutes_end = timestamp['end'] // 60
        seconds_end = timestamp['end'] % 60
        
        return f"[{minutes_start:02d}:{seconds_start:02d} - {minutes_end:02d}:{seconds_end:02d}]"
    
    def _generate_metadata_header(self, metadata: Dict[str, Any]) -> str:
        """
        生成元数据头信息
        
        Args:
            metadata: 元数据字典
            
        Returns:
            格式化的元数据字符串
        """
        header_lines = []
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                # 对于复杂类型，使用repr
                header_lines.append(f"# {key}: {repr(value)}")
            else:
                header_lines.append(f"# {key}: {value}")
        
        if header_lines:
            return "\n" + "\n".join(header_lines)
        return ""