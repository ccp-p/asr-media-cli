"""
接口定义模块
定义系统中各组件应实现的接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Union


class ASRService(ABC):
    """语音识别服务接口"""
    
    @abstractmethod
    def recognize_audio(self, audio_path: str) -> Optional[str]:
        """识别音频文件"""
        pass
    
    @abstractmethod
    def set_interrupt_flag(self, value: bool):
        """设置中断标志"""
        pass


class AudioProcessorInterface(ABC):
    """音频处理器接口"""
    
    @abstractmethod
    def split_audio_file(self, audio_path: str) -> List[str]:
        """分割音频文件为片段"""
        pass
    
    @abstractmethod
    def extract_audio_from_video(self, video_path: str, output_folder: str) -> tuple:
        """从视频中提取音频"""
        pass


class ProgressReporter(ABC):
    """进度报告接口"""
    
    @abstractmethod
    def report_progress(self, current: int, total: int, message: Optional[str] = None):
        """报告进度"""
        pass
    
    @abstractmethod
    def finish(self, success: bool = True, message: Optional[str] = None):
        """完成报告"""
        pass


class ConfigProvider(ABC):
    """配置提供者接口"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any):
        """设置配置项"""
        pass
