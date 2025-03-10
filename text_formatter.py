import re
import logging
from typing import List, Dict, Optional

class TextFormatter:
    """
    文本格式化工具，将ASR识别结果格式化为易读的格式
    """
    
    @staticmethod
    def format_segment_text(segment_texts: List[str], 
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
                processed_text = TextFormatter._process_segment_text(text)
                
                # 添加时间戳（如果需要）
                if include_timestamps and timestamps and i < len(timestamps):
                    time_start = timestamps[i]['start']
                    time_end = timestamps[i]['end']
                    time_info = f"[{TextFormatter._format_time(time_start)}-{TextFormatter._format_time(time_end)}] "
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
            formatted_paragraphs = TextFormatter._split_into_paragraphs(raw_text, paragraph_min_length)
            
            # 如果需要包含时间戳且提供了时间戳信息
            if include_timestamps and timestamps:
                return TextFormatter._add_timestamps(formatted_paragraphs, timestamps)
            
            return "\n\n".join(formatted_paragraphs)
    
    @staticmethod
    def _process_segment_text(text: str) -> str:
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
    
    @staticmethod
    def _split_into_paragraphs(text: str, min_length: int = 100) -> List[str]:
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
    
    @staticmethod
    def _add_timestamps(paragraphs: List[str], timestamps: List[Dict[str, float]]) -> str:
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
        header = f"【总时长: {TextFormatter._format_time(total_duration)}】\n\n"
        
        # 给每个段落添加时间范围
        segment_length = total_duration / len(paragraphs)
        timestamped_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            start_time = i * segment_length
            end_time = (i + 1) * segment_length
            
            time_info = f"[{TextFormatter._format_time(start_time)}-{TextFormatter._format_time(end_time)}]"
            timestamped_paragraphs.append(f"{time_info} {paragraph}")
        
        return header + "\n\n".join(timestamped_paragraphs)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        将秒数格式化为 mm:ss 格式
        """
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"
