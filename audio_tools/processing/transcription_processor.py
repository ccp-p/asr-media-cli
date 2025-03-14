"""
音频转写处理模块
负责管理音频片段的转写过程，包括多线程处理和重试机制
"""
import os
import time
import logging
import concurrent.futures
from typing import Dict, List, Tuple, Optional, Callable

class TranscriptionProcessor:
    """转写处理器，负责管理音频片段的转写过程"""
    
    def __init__(self, 
                asr_manager, 
                temp_segments_dir: str,
                max_workers: int = 4,
                max_retries: int = 3,
                progress_callback: Optional[Callable] = None):
        """
        初始化转写处理器
        
        Args:
            asr_manager: ASR管理器实例
            temp_segments_dir: 临时片段目录
            max_workers: 最大并行工作线程数
            max_retries: 最大重试次数
            progress_callback: 进度回调函数
        """
        self.asr_manager = asr_manager
        self.temp_segments_dir = temp_segments_dir
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        
        # 中断标志
        self.interrupt_received = False
        
    def set_interrupt_flag(self, value: bool = True):
        """设置中断标志"""
        self.interrupt_received = value
    
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
        # 初始化结果和统计
        segment_results = {}
        total_segments = len(segment_files)
        
        if not total_segments:
            return {}
        
        # 记录开始时间
        overall_start_time = time.time()
        OVERALL_TIMEOUT = 3600  # 1小时超时
        PROGRESS_UPDATE_INTERVAL = 1.0  # 进度更新间隔
        STALLED_CHECK_INTERVAL = 5.0  # 卡住检查间隔
        SINGLE_TASK_TIMEOUT = 300  # 单任务超时
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_segment = {}
            task_start_times = {}
            completed_count = 0
            
            # 提交所有任务
            for i, segment_file in enumerate(segment_files):
                if self.interrupt_received:
                    break
                    
                future = executor.submit(self.recognize_audio, 
                                      os.path.join(self.temp_segments_dir, segment_file))
                future_to_segment[future] = (i, segment_file)
                task_start_times[future] = time.time()
            
            # 收集结果，并添加中断检查
            active_futures = list(future_to_segment.keys())
            last_progress_update = time.time()
            last_stalled_check = time.time()
            
            while active_futures and not self.interrupt_received:
                # 检查总体超时
                if time.time() - overall_start_time > OVERALL_TIMEOUT:
                    logging.warning(f"ASR处理总时间超过 {OVERALL_TIMEOUT}秒，强制终止剩余任务")
                    for future in active_futures:
                        future.cancel()
                    break
                
                # 等待任意任务完成，带短超时
                done_futures, active_futures = concurrent.futures.wait(
                    active_futures, 
                    timeout=1.0,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # 处理已完成的任务
                for future in done_futures:
                    if self.interrupt_received:
                        break
                        
                    i, segment_file = future_to_segment[future]
                    completed_count += 1
                    
                    try:
                        result = future.result(timeout=5.0)
                        if result:
                            segment_results[i] = result
                    except concurrent.futures.TimeoutError:
                        logging.warning(f"获取结果超时: {segment_file}")
                    except Exception as e:
                        logging.error(f"处理片段出错 {segment_file}: {str(e)}")
                    
                    # 清理任务记录
                    del future_to_segment[future]
                    del task_start_times[future]
                
                # 周期性更新进度
                current_time = time.time()
                if current_time - last_progress_update > PROGRESS_UPDATE_INTERVAL and self.progress_callback:
                    last_progress_update = current_time
                    self.progress_callback(
                        completed_count,
                        total_segments,
                     f"{completed_count}/{total_segments} 片段完成，{len(active_futures)} 个处理中..."
                    )
                
                # 周期性检查卡住的任务
                if current_time - last_stalled_check > STALLED_CHECK_INTERVAL:
                    last_stalled_check = current_time
                    stalled_tasks = []
                    
                    # 检查所有活动任务是否运行时间过长
                    for future in active_futures:
                        task_duration = current_time - task_start_times[future]
                        if task_duration > SINGLE_TASK_TIMEOUT:
                            stalled_tasks.append(future)
                            i, segment_file = future_to_segment[future]
                            logging.warning(f"任务执行时间过长 {task_duration:.1f}秒: {segment_file}")
                    
                    # 取消卡住的任务
                    for future in stalled_tasks:
                        future.cancel()
                        i, segment_file = future_to_segment[future]
                        logging.warning(f"取消卡住的任务: {segment_file}")
                        del future_to_segment[future]
                        del task_start_times[future]
                        active_futures.remove(future)
                        completed_count += 1
                    
                    # 检查是否剩余很少任务但用时过长
                    if active_futures:
                        total_time = time.time() - overall_start_time
                        time_ratio = total_time / (OVERALL_TIMEOUT * 0.8)  # 使用80%超时时间作为基准
                        remaining_ratio = len(active_futures) / total_segments
                        
                        if remaining_ratio < 0.05 and time_ratio > 0.8:  # 剩余不到5%的任务且已用时超过80%
                            logging.warning(f"只剩余 {len(active_futures)} 个任务但执行时间过长，强制完成...")
                            for future in list(active_futures):
                                future.cancel()
                                i, segment_file = future_to_segment[future]
                                logging.warning(f"强制取消卡住的尾部任务: {segment_file}")
                                completed_count += 1
                            active_futures = []
                    
                    # 避免CPU占用过高
                    if not done_futures:
                        time.sleep(0.1)
        
        return segment_results

    def retry_failed_segments(self, segment_files: List[str], 
                            segment_results: Dict[int, str]) -> Dict[int, str]:
        """
        重试失败的片段
        
        Args:
            segment_files: 所有片段文件列表
            segment_results: 当前的识别结果
            
        Returns:
            更新后的识别结果
        """
        max_retry_rounds = self.max_retries
        retry_round = 0
        
        # 找出失败的片段
        failed_segments = [
            (i, segment_file) for i, segment_file in enumerate(segment_files)
            if i not in segment_results
        ]
        
        # 没有失败的片段，直接返回
        if not failed_segments:
            return segment_results
        
        logging.info(f"开始重试 {len(failed_segments)} 个失败的片段...")
        
        while retry_round < max_retry_rounds and failed_segments and not self.interrupt_received:
            retry_round += 1
            logging.info(f"第 {retry_round} 轮重试 ({len(failed_segments)} 个片段)...")
            
            # 执行单轮重试
            failed_segments = self._perform_single_retry_round(retry_round, failed_segments, segment_results)
            
            if self.interrupt_received:
                logging.warning("检测到中断信号，停止重试")
                break
        
        if failed_segments:
            logging.warning(f"在 {retry_round} 轮重试后仍有 {len(failed_segments)} 个片段失败")
        
        return segment_results

    def _perform_single_retry_round(self, retry_round: int, failed_segments: List[Tuple[int, str]], 
                                  segment_results: Dict[int, str]) -> List[Tuple[int, str]]:
        """执行单轮重试"""
        still_failed = []
        success_count = 0
        
        for i, segment_file in failed_segments:
            if self.interrupt_received:
                still_failed.extend([(i, segment_file) for i, segment_file in failed_segments])
                break
            
            try:
                result = self.recognize_audio(os.path.join(self.temp_segments_dir, segment_file))
                if result:
                    segment_results[i] = result
                    success_count += 1
                    continue
            except Exception as e:
                logging.error(f"重试片段时出错 {segment_file}: {str(e)}")
            
            still_failed.append((i, segment_file))
        
        if success_count > 0:
            logging.info(f"第 {retry_round} 轮重试: 成功 {success_count} 个片段")
        
        return still_failed