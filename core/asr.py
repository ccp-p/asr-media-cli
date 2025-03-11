"""
语音识别(ASR)相关模块
"""
import logging
from typing import Dict, Any, List, Optional

class ASRDataSeg:
    """ASR数据片段类，用于存储和处理ASR结果"""
    
    def __init__(self, text: str = "", start_time: float = 0, end_time: float = 0):
        """
        初始化ASR数据片段
        
        Args:
            text: 识别出的文本
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
        """
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.start_time:.2f}s-{self.end_time:.2f}s] {self.text}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ASRDataSeg':
        """从字典创建ASR数据片段"""
        return cls(
            text=data.get("text", ""),
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time", 0)
        )
