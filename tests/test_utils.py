"""
测试工具模块
提供测试过程中需要的各种辅助工具
"""
import os
import shutil
import tempfile
from typing import List, Dict, Any, Optional, Callable

from core.interfaces import ASRService, AudioProcessorInterface, ProgressReporter


class MockASRService(ASRService):
    """模拟ASR服务，用于测试"""
    
    def __init__(self, responses: Dict[str, str] = None):
        """
        初始化模拟ASR服务
        
        Args:
            responses: 音频路径到识别结果的映射
        """
        self.responses = responses or {}
        self.interrupt_flag = False
        self.call_history = []
        
    def recognize_audio(self, audio_path: str) -> Optional[str]:
        """模拟识别音频文件"""
        self.call_history.append(audio_path)
        
        # 如果设置了中断标志，返回None
        if self.interrupt_flag:
            return None
            
        # 返回预设的响应或默认响应
        if audio_path in self.responses:
            return self.responses[audio_path]
        
        # 默认生成一些文本
        base_name = os.path.basename(audio_path)
        return f"这是音频 {base_name} 的模拟转写结果"
    
    def set_interrupt_flag(self, value: bool):
        """设置中断标志"""
        self.interrupt_flag = value


class MockAudioProcessor(AudioProcessorInterface):
    """模拟音频处理器，用于测试"""
    
    def __init__(self, segment_count: int = 10):
        """
        初始化模拟音频处理器
        
        Args:
            segment_count: 默认分割的片段数量
        """
        self.segment_count = segment_count
        self.temp_dir = tempfile.mkdtemp()
        self.call_history = []
        
    def split_audio_file(self, audio_path: str) -> List[str]:
        """模拟分割音频文件为片段"""
        self.call_history.append(('split', audio_path))
        
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        segments = []
        
        for i in range(self.segment_count):
            segment_path = os.path.join(self.temp_dir, f"{base_name}_segment_{i}.mp3")
            # 创建一个空文件
            with open(segment_path, 'w') as f:
                f.write(f"Mock audio segment {i}")
            segments.append(segment_path)
            
        return segments
    
    def extract_audio_from_video(self, video_path: str, output_folder: str) -> tuple:
        """模拟从视频中提取音频"""
        self.call_history.append(('extract', video_path))
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(output_folder, f"{base_name}.mp3")
        
        # 创建一个空文件
        os.makedirs(output_folder, exist_ok=True)
        with open(audio_path, 'w') as f:
            f.write(f"Mock audio from {base_name}")
            
        return audio_path, True
    
    def cleanup(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)


class MockProgressReporter(ProgressReporter):
    """模拟进度报告器，用于测试"""
    
    def __init__(self):
        """初始化模拟进度报告器"""
        self.progress_history = []
        self.current_progress = 0
        self.total = 0
        self.message = ""
        self.is_finished = False
        self.success = False
        
    def report_progress(self, current: int, total: int, message: Optional[str] = None):
        """报告进度"""
        self.current_progress = current
        self.total = total
        self.message = message or ""
        self.progress_history.append((current, total, self.message))
    
    def finish(self, success: bool = True, message: Optional[str] = None):
        """完成报告"""
        self.is_finished = True
        self.success = success
        self.message = message or ""
        self.progress_history.append(('finish', success, self.message))
