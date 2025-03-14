"""音频转录管理器，管理音频片段的识别过程和重试机制"""

import os
import time
import logging
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any, Callable
from .asr_manager import ASRManager

class TranscriptionManager:
    """音频转录管理器，负责多线程识别音频片段和重试管理"""
    
    def __init__(self, asr_manager: ASRManager, temp_segments_dir: str,
                 max_workers: int = 4, max_retries: int = 3,
                 progress_callback: Optional[Callable] = None):
        """
        初始化转录管理器
        
        Args:
            asr_manager: ASR管理器实例
            temp_segments_dir: 临时片段目录路径
            max_workers: 最大并发工作线程数
            max_retries: 最大重试次数
            progress_callback: 进度回调函数
        """
        self.asr_manager = asr_manager
        self.temp_segments_dir = temp_segments_dir
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        self.interrupt_received = False
        
    def set_interrupt_flag(self, value: bool = True):
        """设置中断标志"""
        self.interrupt_received = value
    
    def recognize_audio(self, audio_path: str) -> Optional[str]:
        """识别单个音频片段"""
        return self.asr_manager.recognize_audio(audio_path)
    
    def process_audio_segments(self, segment_files: List[str]) -> Dict[int, str]:
        """
        使用并行处理识别多个音频片段
        
        Args:
            segment_files: 音频片段文件名列表
            
        Returns:
            识别结果字典，格式为 {片段索引: 识别文本}
        """
        try:
            segment_results: Dict[int, str] = {}
            
            logging.info(f"开始多线程识别 {len(segment_files)} 个音频片段...")
            
            # 更新初始进度
            if self.progress_callback:
                try:
                    self.progress_callback('recognize', 0, len(segment_files), "开始识别片段")
                except Exception as e:
                    logging.warning(f"进度回调出错: {str(e)}")
            
            # 跟踪任务开始时间和最大执行时间
            task_start_times = {}
            MAX_TASK_TIME = 60  # 最大任务执行时间(秒)
            PROGRESS_UPDATE_INTERVAL = 2  # 进度更新间隔(秒)
            STALLED_CHECK_INTERVAL = 10  # 卡住任务检查间隔(秒)
            
            # 记录总体开始时间，设置总超时
            overall_start_time = time.time()
            OVERALL_TIMEOUT = max(len(segment_files) * 10, 300)  # 总超时时间(秒)，至少5分钟
                
            # 使用线程池并行处理音频片段
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建任务字典，映射片段索引和对应的Future对象
                future_to_segment = {}
                
                # 提交所有任务
                for i, segment_file in enumerate(segment_files):
                    future = executor.submit(self.recognize_audio, 
                                            os.path.join(self.temp_segments_dir, segment_file))
                    future_to_segment[future] = (i, segment_file)
                    task_start_times[future] = time.time()
                
                # 收集结果，并添加中断检查
                try:
                    completed_count = 0
                    active_futures = list(future_to_segment.keys())
                    last_progress_update = time.time()
                    last_stalled_check = time.time()
                    
                    # 只要还有活动任务且未收到中断信号且未超时
                    while active_futures and not self.interrupt_received:
                        # 检查总体超时
                        if time.time() - overall_start_time > OVERALL_TIMEOUT:
                            logging.warning(f"总体处理时间超过 {OVERALL_TIMEOUT}秒，强制结束...")
                            for future in active_futures:
                                future.cancel()
                            break
                        
                        # 检查任何已完成的任务
                        done_futures = []
                        for future in active_futures:
                            if future.done():
                                done_futures.append(future)
                        
                        # 处理已完成的任务
                        for future in done_futures:
                            i, segment_file = future_to_segment[future]
                            active_futures.remove(future)
                            completed_count += 1
                            
                            try:
                                text = future.result(timeout=3)
                                
                                if text:
                                    segment_results[i] = text
                                    status_text = f"{completed_count}/{len(segment_files)} 片段完成 (成功识别 {len(segment_results)})"
                                    logging.debug(f"  ├─ 成功识别: {segment_file}")
                                else:
                                    status_text = f"{completed_count}/{len(segment_files)} 片段完成 (失败 {completed_count - len(segment_results)})"
                                    logging.warning(f"  ├─ 识别失败: {segment_file}")
                                
                                # 更新进度
                                if self.progress_callback:
                                    try:
                                        self.progress_callback(
                                            'recognize', 
                                            completed_count, 
                                            len(segment_files), 
                                            status_text
                                        )
                                    except Exception as e:
                                        logging.warning(f"进度回调出错: {str(e)}")
                                    
                            except concurrent.futures.TimeoutError:
                                logging.warning(f"  ├─ 识别结果获取超时: {segment_file}")
                                if self.progress_callback:
                                    try:
                                        self.progress_callback(
                                            'recognize',
                                            completed_count, 
                                            len(segment_files),
                                            f"{completed_count}/{len(segment_files)} 片段完成 (超时 {segment_file})"
                                        )
                                    except Exception as e:
                                        logging.warning(f"进度回调出错: {str(e)}")
                            except Exception as exc:
                                logging.error(f"  ├─ 识别出错: {segment_file} - {str(exc)}")
                                if self.progress_callback:
                                    try:
                                        self.progress_callback(
                                            'recognize',
                                            completed_count, 
                                            len(segment_files),
                                            f"{completed_count}/{len(segment_files)} 片段完成 (错误)"
                                        )
                                    except Exception as e:
                                        logging.warning(f"进度回调出错: {str(e)}")
                            
                            # 清理任务计时器
                            if future in task_start_times:
                                del task_start_times[future]
                    
                        # 周期性更新进度，即使没有任务完成
                        current_time = time.time()
                        if current_time - last_progress_update > PROGRESS_UPDATE_INTERVAL and self.progress_callback:
                            last_progress_update = current_time
                            try:
                                self.progress_callback(
                                    'recognize',
                                    completed_count,
                                    len(segment_files),
                                    f"{completed_count}/{len(segment_files)} 片段完成，{len(active_futures)} 个处理中..."
                                )
                            except Exception as e:
                                logging.warning(f"进度回调出错: {str(e)}")
                        
                        # 周期性检查卡住的任务
                        if current_time - last_stalled_check > STALLED_CHECK_INTERVAL:
                            last_stalled_check = current_time
                            stalled_tasks = []
                            
                            # 检查所有活动任务是否运行时间过长
                            for future in list(active_futures):
                                if future in task_start_times:
                                    task_time = current_time - task_start_times[future]
                                    if task_time > MAX_TASK_TIME:
                                        i, segment_file = future_to_segment[future]
                                        logging.warning(f"任务 {segment_file} 执行超过 {MAX_TASK_TIME}秒，强制取消")
                                        stalled_tasks.append((future, i, segment_file))
                            
                            # 处理卡住的任务
                            for future, i, segment_file in stalled_tasks:
                                # 取消任务
                                future.cancel()
                                
                                # 从活跃列表中删除该任务
                                if future in active_futures:
                                    active_futures.remove(future)
                                
                                # 更新完成数量
                                completed_count += 1
                                
                                # 更新进度
                                if self.progress_callback:
                                    try:
                                        self.progress_callback(
                                            'recognize',
                                            completed_count,
                                            len(segment_files),
                                            f"{completed_count}/{len(segment_files)} 片段完成 (强制取消卡住任务)"
                                        )
                                    except Exception as e:
                                        logging.warning(f"进度回调出错: {str(e)}")
                                
                                # 清理任务计时器
                                if future in task_start_times:
                                    del task_start_times[future]
                        
                        # 如果只剩少量任务且已接近总超时，强制结束
                        if len(active_futures) > 0:  # 避免除以零错误
                            remaining_ratio = len(active_futures) / len(segment_files)
                            time_ratio = (time.time() - overall_start_time) / OVERALL_TIMEOUT
                            
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
                        
                except KeyboardInterrupt:
                    logging.warning("检测到用户中断，正在取消剩余任务...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    self.interrupt_received = True
                
                # 如果因为中断或超时跳出循环，取消剩余任务
                if active_futures:
                    reason = "中断" if self.interrupt_received else "总超时"
                    logging.warning(f"检测到{reason}，正在取消剩余 {len(active_futures)} 个任务...")
                    for future in active_futures:
                        future.cancel()
                        
        except KeyboardInterrupt:
            logging.warning("检测到用户中断，正在取消剩余任务...")
            executor.shutdown(wait=False, cancel_futures=True)
            self.interrupt_received = True
        
        # 完成识别阶段
        success_count = len(segment_results)
        fail_count = len(segment_files) - success_count
        
        # 报告最终状态
        if self.progress_callback:
            try:
                self.progress_callback(
                    'recognize',
                    len(segment_files),  # 将进度设为总数，表示完成
                    len(segment_files),
                    f"完成 - {success_count} 成功, {fail_count} 失败" + 
                    (" (已中断)" if self.interrupt_received else "")
                )
            except Exception as e:
                logging.warning(f"最终进度回调出错: {str(e)}")
        
        return segment_results

    def transcribe_segments(self, segment_files: List[str]) -> Tuple[Dict[int, str], Dict]:
        """
        识别一组音频片段，包括重试机制
        
        Args:
            segment_files: 音频片段文件路径列表
            
        Returns:
            (识别结果字典, 统计信息)
        """
        # 第一轮识别
        segment_results = self.process_audio_segments(segment_files)
        
        # 统计第一轮结果
        total_segments = len(segment_files)
        success_count = len(segment_results)
        fail_count = total_segments - success_count
        stats = {
            'total': total_segments,
            'success_count': success_count,
            'fail_count': fail_count,
            'retries': 0
        }
        
        return segment_results, stats

    def _get_audio_duration_minutes(self, audio_path: str) -> float:
        """
        获取音频时长（分钟）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频时长（分钟）
        """
        # 实际项目中需要调用音频处理库获取时长
        # 例如使用 pydub, librosa 等
        from pydub import AudioSegment
        audio_duration = AudioSegment.from_file(audio_path).duration_seconds
        return audio_duration / 60.0

    def transcribe_long_audio(self, audio_path: str, part_duration_minutes: int = 15) -> Dict[str, Any]:
        """
        将长音频分成多个部分进行识别，每部分默认15分钟
        
        Args:
            audio_path: 音频文件路径
            part_duration_minutes: 每部分的时长（分钟）
            
        Returns:
            包含识别结果和统计信息的字典
        """
        try:
            if not os.path.exists(audio_path):
                logging.error(f"音频文件不存在: {audio_path}")
                return {"error": "音频文件不存在", "success": False}
                
            logging.info(f"开始处理长音频: {audio_path}，每部分 {part_duration_minutes} 分钟")
            
            # 获取音频时长
            audio_duration_minutes = self._get_audio_duration_minutes(audio_path)
            
            if audio_duration_minutes <= 0:
                logging.error(f"无法获取音频时长或音频无效: {audio_path}")
                return {"error": "无法获取音频时长或音频无效", "success": False}
                
            # 计算需要分成的部分数
            num_parts = max(1, int(audio_duration_minutes / part_duration_minutes) + 
                          (1 if audio_duration_minutes % part_duration_minutes > 0 else 0))
                
            logging.info(f"音频总时长: {audio_duration_minutes:.2f} 分钟，将分为 {num_parts} 个部分处理")
            
            # 如果只有一个部分，直接处理整个音频
            if num_parts == 1:
                logging.info("音频时长较短，将作为单个部分处理")
                return {"message": "音频较短，使用常规处理方式", "use_regular_method": True}
            
            # 处理每个部分的逻辑将在后续实现
            logging.info("分部处理功能已准备，需要实现音频分割和部分处理逻辑")
            return {"message": "分部处理功能框架已创建", "num_parts": num_parts, "success": True}
            
        except Exception as e:
            logging.error(f"处理长音频时出错: {str(e)}")
            return {"error": str(e), "success": False}
