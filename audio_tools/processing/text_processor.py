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
                    i + 1,
                    len(segment_files),
                    f"处理片段 {i+1}/{len(segment_files)}"
                )
        
        try:
            # 格式化文本
            if self.format_text:
                if self.progress_callback:
                    self.progress_callback(0, 1, "正在格式化文本", "file")
                
                
                # 使用新的格式化方法
                full_text = self.format_segment_text(
                    all_text,
                    timestamps=all_timestamps if self.include_timestamps else None,
                    include_timestamps=self.include_timestamps,
                    paragraph_min_length=self.min_segment_length
                )
                
                if self.progress_callback:
                    self.progress_callback(
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
            
            if part_num is not None:
                output_subfolder = self.get_output_subfolder(base_name)
                output_file = os.path.join(output_subfolder, f"{base_name}_part{part_num}.txt")
            else:
                output_file = os.path.join(self.output_folder, f"{base_name}.txt")
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
    
    # 以下是参照TextFormatter实现的新方法
    def format_segment_text(self, 
                           segment_texts: List[str], 
                           timestamps: Optional[List[Dict[str, float]]] = None,
                           include_timestamps: bool = False,
                           paragraph_min_length: int = 100,
                           separate_segments: bool = True) -> str:
        """
        格式化文本段落，使其更易于阅读
        
        Args:
            segment_texts: 文本片段列表
            timestamps: 对应的时间戳信息 [{'start': 0.0, 'end': 10.5}, ...]
            include_timestamps: 是否在输出中包含时间戳
            paragraph_min_length: 段落的最小长度，超过此长度会被视为段落
            separate_segments: 是否为每个30秒分片添加分隔符
            
        Returns:
            格式化后的文本
        """
        # 如果没有文本，直接返回空字符串
        if not segment_texts:
            return ""
        
        # 根据separate_segments参数决定处理方式
        if separate_segments:
            # 为每个原始分片添加分隔符，保持片段独立
            formatted_segments = []
            for i, text in enumerate(segment_texts):
                if not text or text == "[无法识别的音频片段]":
                    continue
                
                # 处理文本：将空格替换为逗号，确保句子末尾有句号
                processed_text = self._process_segment_text(text)
                
                # 添加时间戳（如果需要）
                if include_timestamps and timestamps and i < len(timestamps):
                    time_start = timestamps[i]['start']
                    time_end = timestamps[i]['end']
                    time_info = f"[{self._format_time(time_start)}-{self._format_time(time_end)}] "
                    formatted_segments.append(f"{time_info}{processed_text}")
                else:
                    formatted_segments.append(processed_text)
                    
            # 用新行分隔每个片段
            return "\n\n".join(formatted_segments)
        else:
            # 原来的处理方式，合并所有文本并替换无法识别的部分
            raw_text = " ".join([text for text in segment_texts if text and text != "[无法识别的音频片段]"])
            if not raw_text:
                return "[未能成功识别任何内容]"
            
            # 移除多余的空格
            raw_text = re.sub(r'\s+', ' ', raw_text).strip()
            
            # 基于标点符号和句子长度智能分段
            formatted_paragraphs = self._split_into_paragraphs(raw_text, paragraph_min_length)
            
            # 如果需要包含时间戳且提供了时间戳信息
            if include_timestamps and timestamps:
                return self._add_timestamps(formatted_paragraphs, timestamps)
            
            return "\n\n".join(formatted_paragraphs)
    
    def _process_segment_text(self, text: str) -> str:
        """
        处理每个30秒片段的文本:
        1. 将空格替换为逗号
        2. 确保句子末尾有句号
        """
        # 移除多余的空格，保留单词间的空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 中文内容中替换空格为逗号
        # 匹配汉字之间的空格
        text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1，\2', text)
        
        # 处理句尾标点
        last_char = text[-1] if text else ""
        if last_char not in ["。", "！", "？", ".", "!", "?"]:
            text += "。"  # 添加句号
        
        return text
    
    def _split_into_paragraphs(self, text: str, min_length: int = 100) -> List[str]:
        """
        智能地将文本分割成段落
        
        1. 优先在句号、问号、感叹号+空格处分段
        2. 考虑段落长度，过长的段落会被再次分割
        3. 规范标点符号前后的空格
        """
        # 中文句子结束标志
        sentence_end_pattern = r'([。！？\.\!\?]+)(\s*)'
        
        # 首先规范化标点符号
        text = re.sub(sentence_end_pattern, r'\1 ', text)
        
        # 按句子分割
        sentences = re.split(sentence_end_pattern, text)
        # 过滤空字符串并重组句子
        cleaned_sentences = []
        current_sentence = ""
        
        for i in range(0, len(sentences), 3):
            if i < len(sentences):
                current_sentence = sentences[i]
                if i+1 < len(sentences):
                    current_sentence += sentences[i+1]  # 添加标点
                cleaned_sentences.append(current_sentence)
        
        # 合并短句子形成段落
        paragraphs = []
        current_paragraph = ""
        
        for sentence in cleaned_sentences:
            if not sentence.strip():
                continue
                
            if len(current_paragraph) + len(sentence) > min_length and current_paragraph:
                paragraphs.append(current_paragraph.strip())
                current_paragraph = sentence
            else:
                current_paragraph = (current_paragraph + " " + sentence).strip()
        
        # 添加最后一个段落
        if current_paragraph:
            paragraphs.append(current_paragraph.strip())
        
        return paragraphs
    
    def _add_timestamps(self, paragraphs: List[str], timestamps: List[Dict[str, float]]) -> str:
        """
        为段落添加时间戳
        
        Args:
            paragraphs: 文本段落列表
            timestamps: 对应的时间戳信息 [{'start': 0.0, 'end': 10.5}, ...]
            
        Returns:
            包含时间戳的格式化文本
        """
        if not timestamps or len(timestamps) == 0:
            return "\n\n".join(paragraphs)
        
        # 添加总时长信息
        total_duration = timestamps[-1].get('end', 0) - timestamps[0].get('start', 0)
        header = f"【总时长: {self._format_time(total_duration)}】\n\n"
        
        # 给每个段落添加时间范围
        segment_length = total_duration / len(paragraphs)
        timestamped_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            start_time = i * segment_length
            end_time = (i + 1) * segment_length
            
            time_info = f"[{self._format_time(start_time)}-{self._format_time(end_time)}]"
            timestamped_paragraphs.append(f"{time_info} {paragraph}")
        
        return header + "\n\n".join(timestamped_paragraphs)
    
    def _format_time(self, seconds: float) -> str:
        """
        将秒数格式化为 mm:ss 格式
        """
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"
    
    # 保留原有方法作为接口兼容，但内部使用新的实现
    def _format_text(self, 
                    texts: List[str], 
                    timestamps: Optional[List[Dict[str, int]]] = None) -> str:
        """
        格式化文本片段 - 兼容旧接口，实际使用新实现
        
        Args:
            texts: 文本片段列表
            timestamps: 对应的时间戳列表
            
        Returns:
            格式化后的文本
        """
        return self.format_segment_text(
            texts,
            timestamps=timestamps,
            include_timestamps=self.include_timestamps,
            paragraph_min_length=self.min_segment_length,
            separate_segments=False
        )
    
    def _format_timestamp(self, timestamp: Dict[str, int]) -> str:
        """
        格式化时间戳 - 保留兼容旧接口
        """
        return f"[{self._format_time(timestamp['start'])}-{self._format_time(timestamp['end'])}]"
    
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