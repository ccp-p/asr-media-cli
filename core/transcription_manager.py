import os
import time
import logging
import concurrent.futures
from typing import Dict, List, Optional, Callable, Any, Tuple

class TranscriptionManager:
    """音频转录管理器，负责多线程识别音频片段和重试管理"""
    
    def __init__(self, 
                asr_manager, 
                temp_segments_dir: str,
                max_workers: int = 4,
                max_retries: int = 3,
                progress_callback: Optional[Callable] = None):
        """
        初始化转录管理器
        
        Args:
            asr_manager: ASR服务管理器
            temp_segments_dir: 临时片段目录
            max_workers: 最大并行工作线程数
            max_retries: 最大重试次数
            progress_callback: 进度回调函数 (state, current, total, message)
                state可以是: 'recognize', 'retry_1', 'retry_2'...
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
        """
        识别单个音频片段
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            识别结果文本，失败返回None
        """
        # 使用ASR管理器进行识别
        return self.asr_manager.recognize_audio(audio_path)
    
    def process_audio_segments(self, segment_files: List[str]) -> Dict[int, str]:
        """
        使用并行处理识别多个音频片段
        
        Args:
            segment_files: 音频片段文件名列表
            
        Returns:
            识别结果字典，格式为 {片段索引: 识别文本}
        """
        segment_results: Dict[int, str] = {}
        
        logging.info(f"开始多线程识别 {len(segment_files)} 个音频片段...")
        
        # 更新初始进度
        if self.progress_callback:
            self.progress_callback('recognize', 0, len(segment_files), "开始识别片段")
        
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
                            # 使用较短的超时时间获取结果
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
                                self.progress_callback(
                                    'recognize', 
                                    completed_count, 
                                    len(segment_files), 
                                    status_text
                                )
                                
                        except concurrent.futures.TimeoutError:
                            logging.warning(f"  ├─ 识别结果获取超时: {segment_file}")
                            if self.progress_callback:
                                self.progress_callback(
                                    'recognize',
                                    completed_count, 
                                    len(segment_files),
                                    f"{completed_count}/{len(segment_files)} 片段完成 (超时 {segment_file})"
                                )
                        except Exception as exc:
                            logging.error(f"  ├─ 识别出错: {segment_file} - {str(exc)}")
                            if self.progress_callback:
                                self.progress_callback(
                                    'recognize',
                                    completed_count, 
                                    len(segment_files),
                                    f"{completed_count}/{len(segment_files)} 片段完成 (错误)"
                                )
                        
                        # 清理任务计时器
                        if future in task_start_times:
                            del task_start_times[future]
                    
                    # 周期性更新进度，即使没有任务完成
                    current_time = time.time()
                    if current_time - last_progress_update > PROGRESS_UPDATE_INTERVAL and self.progress_callback:
                        last_progress_update = current_time
                        self.progress_callback(
                            'recognize',
                            completed_count,
                            len(segment_files),
                            f"{completed_count}/{len(segment_files)} 片段完成，{len(active_futures)} 个处理中..."
                        )
                    
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
                                self.progress_callback(
                                    'recognize',
                                    completed_count,
                                    len(segment_files),
                                    f"{completed_count}/{len(segment_files)} 片段完成 (强制取消卡住任务)"
                                )
                            
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
            self.progress_callback(
                'recognize',
                len(segment_files),  # 将进度设为总数，表示完成
                len(segment_files),
                f"完成 - {success_count} 成功, {fail_count} 失败" + 
                (" (已中断)" if self.interrupt_received else "")
            )
        
        return segment_results
    
    def _perform_single_retry_round(self, retry_round: int, failed_segments: List[Tuple[int, str]], 
                                   segment_results: Dict[int, str]) -> Tuple[List[Tuple[int, str]], int]:
        """
        执行单轮重试
        
        Args:
            retry_round: 当前重试轮次
            failed_segments: 需要重试的片段列表 [(索引, 文件名),...]
            segment_results: 当前的识别结果字典
            
        Returns:
            Tuple[List[Tuple[int, str]], int]: (仍然失败的片段列表, 本轮成功数量)
        """
        retry_state = f'retry_{retry_round}'
        if self.progress_callback:
            self.progress_callback(
                retry_state,
                0,
                len(failed_segments),
                f"0/{len(failed_segments)} 片段完成"
            )
        
        still_failed = []
        success_in_round = 0
        completed_count = 0
        
        # 对失败的片段进行多线程重试
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as retry_executor:
            future_to_failed = {
                retry_executor.submit(self.recognize_audio, 
                                    os.path.join(self.temp_segments_dir, segment_file)): 
                (idx, segment_file)
                for idx, segment_file in failed_segments
            }
            
            try:
                for future in concurrent.futures.as_completed(future_to_failed):
                    if self.interrupt_received:
                        logging.warning("检测到中断，正在取消剩余重试任务...")
                        retry_executor.shutdown(wait=False, cancel_futures=True)
                        break
                        
                    idx, segment_file = future_to_failed[future]
                    completed_count += 1
                    
                    try:
                        text = future.result(timeout=60)
                        if text:
                            segment_results[idx] = text
                            success_in_round += 1
                            logging.debug(f"  ├─ 重试成功: {segment_file}")
                            
                            # 更新进度
                            if self.progress_callback:
                                self.progress_callback(
                                    retry_state, 
                                    completed_count, 
                                    len(failed_segments),
                                    f"{completed_count}/{len(failed_segments)} 完成 (成功 {success_in_round})"
                                )
                        else:
                            still_failed.append((idx, segment_file))
                            logging.warning(f"  ├─ 重试失败: {segment_file}")
                            
                            # 更新进度
                            if self.progress_callback:
                                self.progress_callback(
                                    retry_state, 
                                    completed_count, 
                                    len(failed_segments),
                                    f"{completed_count}/{len(failed_segments)} 完成 (失败 {len(still_failed)})"
                                )
                    except concurrent.futures.TimeoutError:
                        still_failed.append((idx, segment_file))
                        logging.warning(f"  ├─ 重试超时: {segment_file}")
                        
                        # 更新进度
                        if self.progress_callback:
                            self.progress_callback(
                                retry_state, 
                                completed_count, 
                                len(failed_segments),
                                f"{completed_count}/{len(failed_segments)} 完成 (超时 {len(still_failed)})"
                            )
                    except Exception as exc:
                        still_failed.append((idx, segment_file))
                        logging.error(f"  ├─ 重试出错: {segment_file} - {str(exc)}")
                        
                        # 更新进度
                        if self.progress_callback:
                            self.progress_callback(
                                retry_state, 
                                completed_count, 
                                len(failed_segments),
                                f"{completed_count}/{len(failed_segments)} 完成 (错误 {len(still_failed)})"
                            )
            except KeyboardInterrupt:
                logging.warning("检测到用户中断，正在取消剩余重试任务...")
                retry_executor.shutdown(wait=False, cancel_futures=True)
                self.interrupt_received = True
        
        # 完成这一轮重试
        if self.progress_callback:
            self.progress_callback(
                retry_state,
                len(failed_segments),  # 将进度设为总数，表示完成
                len(failed_segments),
                f"完成 - 成功 {success_in_round}, 仍失败 {len(still_failed)}" +
                (" (已中断)" if self.interrupt_received else "")
            )
        
        logging.info(f"  └─ 第 {retry_round} 轮重试结果: 成功 {success_in_round}, 仍失败 {len(still_failed)}")
        return still_failed, success_in_round

    def retry_failed_segments(self, segment_files: List[str], 
                              segment_results: Dict[int, str]) -> Dict[int, str]:
        """
        重试识别失败的片段
        
        Args:
            segment_files: 所有音频片段文件名列表
            segment_results: 已成功识别的结果
            
        Returns:
            更新后的识别结果字典
        """
        # 如果已收到中断信号或没有失败的片段，则直接返回当前结果
        if self.interrupt_received:
            return segment_results
            
        fail_count = len(segment_files) - len(segment_results)
        if fail_count == 0:
            return segment_results
            
        logging.info(f"\n开始重试 {fail_count} 个失败的片段...")
        failed_segments = [(i, segment_files[i]) for i in range(len(segment_files)) 
                         if i not in segment_results]
        
        for retry_round in range(1, self.max_retries + 1):
            if not failed_segments or self.interrupt_received:
                break
                
            logging.info(f"第 {retry_round} 轮重试 ({len(failed_segments)} 个片段):")
            
            # 执行单轮重试
            failed_segments, success_in_round = self._perform_single_retry_round(
                retry_round, failed_segments, segment_results
            )
            
            if not failed_segments:
                logging.info("  └─ 所有片段都已成功识别，无需继续重试")
                break
        
        return segment_results
    
    def transcribe_segments(self, segment_files: List[str]) -> Tuple[Dict[int, str], Dict]:
        """
        处理音频片段并返回识别结果和统计信息
        
        Args:
            segment_files: 音频片段文件名列表
            
        Returns:
            Tuple[Dict[int, str], Dict]: (识别结果字典, 统计信息)
        """
        # 开始时间
        start_time = time.time()
        
        # 初始识别
        segment_results = self.process_audio_segments(segment_files)
        
        # 重试识别失败的片段
        if not self.interrupt_received:
            segment_results = self.retry_failed_segments(segment_files, segment_results)
        
        # 计算统计信息
        success_count = len(segment_results)
        fail_count = len(segment_files) - success_count
        duration = time.time() - start_time
        
        # 返回结果和统计
        stats = {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_count': len(segment_files),
            'success_rate': success_count / len(segment_files) if segment_files else 0,
            'duration': duration,
            'interrupted': self.interrupt_received
        }
        
        return segment_results, stats
