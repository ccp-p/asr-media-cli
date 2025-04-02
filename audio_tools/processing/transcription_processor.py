"""
音频转写处理模块
负责管理音频片段的转写过程，包括多线程处理和重试机制
"""
import os
import time
import logging
from typing import Dict, List, Tuple, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from core.interfaces import ASRService
from core.dependency_container import container


class TranscriptionProcessor:
    """转写处理器，负责管理音频片段的转写过程"""
    
    def __init__(self, 
                asr_manager=None,
                temp_segments_dir: str = None,
                max_workers: int = 4,
                max_retries: int = 3,
                progress_callback: Optional[Callable] = None):
        """
        初始化转录处理器
        
        Args:
            asr_manager: ASR管理器，如果为None则从容器获取
            temp_segments_dir: 临时片段目录
            max_workers: 最大工作线程数
            max_retries: 最大重试次数
            progress_callback: 进度回调函数
        """
        # 支持依赖注入
        self.asr_manager = asr_manager or container.get('asr_manager')
        self.temp_segments_dir = temp_segments_dir or container.get('config').get('temp_segments_dir')
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        self.interrupt_flag = False
        
        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
    def set_interrupt_flag(self, value: bool = True):
        """设置中断标志"""
        self.interrupt_flag = value
        
        # 传递中断标志到ASR管理器
        if hasattr(self.asr_manager, 'set_interrupt_flag'):
            self.asr_manager.set_interrupt_flag(value)
        
    def recognize_audio(self, audio_path: str) -> Optional[str]:
        """识别单个音频片段"""
        return self.asr_manager.recognize_audio(audio_path)
    
    def process_audio_segments(self, segment_files: List[str]) -> Dict[int, str]:
        """
        处理音频片段列表
        
        Args:
            segment_files: 音频片段文件列表
            
        Returns:
            索引到识别结果的映射
        """
        results = {}
        total_segments = len(segment_files)
        
        # 创建进度追踪
        if self.progress_callback:
            self.progress_callback(0, total_segments, "开始处理音频片段")
        
        # 使用线程池并行处理
        futures = {}
        for idx, segment_file in enumerate(segment_files):
            if self.interrupt_flag:
                logging.warning("检测到中断标志，停止处理更多片段")
                break
                
            future = self.executor.submit(self.recognize_audio, os.path.join(self.temp_segments_dir, segment_file))
            futures[future] = idx
        
        # 收集结果
        completed = 0
        for future in futures:
            idx = futures[future]
            try:
                result = future.result()
                results[idx] = result
                
                completed += 1
                if self.progress_callback and completed % 5 == 0:
                    self.progress_callback(completed, total_segments, f"处理中: {completed}/{total_segments}")
            except Exception as e:
                logging.error(f"处理片段 {idx} 失败: {str(e)}")
        
        # 完成进度报告
        if self.progress_callback:
            self.progress_callback(total_segments, total_segments, "音频片段处理完成")
            
        return results
        
    def retry_failed_segments(self, segment_files: List[str], results: Dict[int, str]) -> Dict[int, str]:
        """
        重试失败的音频片段
        
        Args:
            segment_files: 音频片段文件列表
            results: 当前识别结果
            
        Returns:
            更新后的识别结果
        """
        # 找出失败的片段
        failed_segments = []
        for idx, segment in enumerate(segment_files):
            if idx not in results or results[idx] is None or not results[idx].strip():
                failed_segments.append((idx, segment))
        
        if not failed_segments:
            return results
            
        # 创建进度追踪
        total_retries = len(failed_segments)
        if self.progress_callback:
            self.progress_callback(0, total_retries, f"重试 {total_retries} 个失败片段")
            
        # 重试每个失败的片段
        for retry in range(self.max_retries):
            if self.interrupt_flag or not failed_segments:
                break
                
            logging.info(f"第 {retry+1}/{self.max_retries} 轮重试, 剩余 {len(failed_segments)} 个片段")
            
            still_failed = []
            for i, (idx, segment) in enumerate(failed_segments):
                if self.interrupt_flag:
                    logging.warning("检测到中断标志，停止重试")
                    break
                    
                try:
                    result = self.recognize_audio(os.path.join(self.temp_segments_dir, segment))
                    if result and result.strip():
                        results[idx] = result
                        if self.progress_callback:
                            self.progress_callback(i+1, total_retries, f"重试成功 {i+1}/{total_retries}")
                    else:
                        still_failed.append((idx, segment))
                        if self.progress_callback:
                            self.progress_callback(i+1, total_retries, f"重试仍失败 {i+1}/{total_retries}")
                except Exception as e:
                    still_failed.append((idx, segment))
                    logging.error(f"重试片段 {idx} 失败: {str(e)}")
            
            failed_segments = still_failed
            
        return results