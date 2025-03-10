import os
import tempfile
import shutil
import time
import concurrent.futures
import logging
import requests
import signal
from typing import Dict, List, Set, Tuple, Optional, Any, Callable
from pathlib import Path
from pydub import AudioSegment

# 导入工具函数
from utils import format_time_duration, load_json_file, save_json_file

# 导入ASR模块
from asr import GoogleASR, JianYingASR, KuaiShouASR, BcutASR, ASRDataSeg, ASRServiceSelector
from text_formatter import TextFormatter

# 创建全局的ASR服务选择器
asr_selector = ASRServiceSelector()

class AudioProcessor:
    """音频处理类，负责音频分割、转写和文本整合"""
    
    def __init__(self, mp3_folder: str, output_folder: str, 
                 max_retries: int = 3, max_workers: int = 4,
                 use_jianying_first: bool = False, use_kuaishou: bool = False, 
                 use_bcut: bool = False, format_text: bool = True,
                 include_timestamps: bool = True):
        """
        初始化音频处理器
        
        Args:
            mp3_folder: MP3文件所在文件夹
            output_folder: 输出结果文件夹
            max_retries: 最大重试次数
            max_workers: 线程池工作线程数
            use_jianying_first: 是否优先使用剪映ASR
            use_kuaishou: 是否使用快手ASR
            use_bcut: 是否使用B站ASR
            format_text: 是否格式化输出文本以提高可读性
            include_timestamps: 是否在格式化文本中包含时间戳
        """
        self.mp3_folder = mp3_folder
        self.output_folder = output_folder
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.use_jianying_first = use_jianying_first
        self.use_kuaishou = use_kuaishou
        self.use_bcut = use_bcut
        self.format_text = format_text
        self.include_timestamps = include_timestamps
        
        # 创建输出文件夹
        os.makedirs(self.output_folder, exist_ok=True)
        
        # 记录文件路径
        self.processed_record_file = os.path.join(self.output_folder, "processed_audio_files.json")
        self.processed_files = load_json_file(self.processed_record_file)
        
        # 初始化中断信号处理
        self.interrupt_received = False
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        
        # 临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.temp_segments_dir = os.path.join(self.temp_dir, "segments")
        os.makedirs(self.temp_segments_dir, exist_ok=True)
        
        # 初始化ASR服务
        self._register_asr_services()
    
    def _save_processed_records(self):
        """保存已处理文件记录"""
        save_json_file(self.processed_record_file, self.processed_files)
    
    def _register_asr_services(self):
        """注册ASR服务到服务选择器"""
        # 根据用户配置设置权重
        google_weight = 5 if (self.use_jianying_first or self.use_kuaishou or self.use_bcut) else 20
        jianying_weight = 20 if self.use_jianying_first else 10
        kuaishou_weight = 25 if self.use_kuaishou else 0  # 0表示不使用
        bcut_weight = 30 if self.use_bcut else 0  # 0表示不使用
        
        # 注册服务
        asr_selector.register_service("Google", GoogleASR, weight=google_weight)
        asr_selector.register_service("剪映", JianYingASR, weight=jianying_weight)
        
        if self.use_kuaishou:
            asr_selector.register_service("快手", KuaiShouASR, weight=kuaishou_weight)
        
        if self.use_bcut:
            asr_selector.register_service("B站", BcutASR, weight=bcut_weight)
        
        logging.info("ASR服务注册完成")
    
    def handle_interrupt(self, sig, frame):
        """处理中断信号"""
        logging.warning("\n\n⚠️ 接收到中断信号，正在安全终止程序...\n稍等片刻，正在保存已处理的数据...\n")
        self.interrupt_received = True
        # 不立即退出，允许程序完成当前处理和清理
    
    def split_audio_file(self, input_path: str, segment_length: int = 30) -> List[str]:
        """
        将单个音频文件分割为较小片段
        
        Args:
            input_path: 输入音频文件路径
            segment_length: 每个片段的长度(秒)
            
        Returns:
            分割后的片段文件列表
        """
        filename = os.path.basename(input_path)
        logging.info(f"正在分割 {filename} 为小片段...")
        
        try:
            audio = AudioSegment.from_mp3(input_path)
            
            # 计算总时长（毫秒转秒）
            total_duration = len(audio) // 1000
            logging.info(f"音频总时长: {total_duration}秒")
            
            segment_files = []
            
            # 分割音频
            for i, start in enumerate(range(0, total_duration, segment_length)):
                end = min(start + segment_length, total_duration)
                segment = audio[start*1000:end*1000]
                
                # 导出为WAV格式（兼容语音识别API）
                output_filename = f"{os.path.splitext(filename)[0]}_part{i+1:03d}.wav"
                output_path = os.path.join(self.temp_segments_dir, output_filename)
                segment.export(
                    output_path,
                    format="wav",
                    parameters=["-ac", "1", "-ar", "16000"]  # 单声道，16kHz采样率
                )
                segment_files.append(output_filename)
                logging.info(f"  ├─ 分割完成: {output_filename}")
            
            return segment_files
            
        except Exception as e:
            logging.error(f"分割音频文件 {filename} 失败: {str(e)}")
            return []
    
    def recognize_audio(self, audio_path: str) -> Optional[str]:
        """
        识别单个音频片段
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            识别结果文本，失败返回None
        """
        # 最多尝试的服务数量
        max_attempts = 3
        attempts = 0
        
        # 已尝试的服务，避免重复使用
        tried_services: Set[str] = set()
        
        while attempts < max_attempts:
            # 选择一个ASR服务
            service_result = asr_selector.select_service()
            if not service_result:
                logging.warning("没有可用的ASR服务")
                break
                
            name, service_class = service_result
            
            # 如果已经尝试过该服务，且还有其他服务可用，则继续选择
            if name in tried_services and attempts < max_attempts - 1:
                attempts += 1
                continue
                
            tried_services.add(name)
            
            logging.info(f"尝试使用 {name} ASR识别: {os.path.basename(audio_path)}")
            try:
                # 创建ASR实例并识别
                asr = service_class(audio_path)
                segments = asr.get_result(callback=lambda p, m: logging.info(f"{name}识别进度: {p}% - {m}"))
                
                if segments:
                    result_text = " ".join([seg.text for seg in segments if seg.text])
                    if result_text:
                        logging.info(f"{name} ASR识别成功: {os.path.basename(audio_path)}")
                        asr_selector.report_result(name, True)  # 报告成功
                        return result_text
                
                logging.warning(f"{name} ASR未能识别文本")
                asr_selector.report_result(name, False)  # 报告失败
                
            except Exception as e:
                logging.error(f"{name} ASR识别出错: {str(e)}")
                asr_selector.report_result(name, False)  # 报告失败
            
            attempts += 1
        
        # 所有服务都失败了
        logging.error(f"所有ASR服务均未能识别: {os.path.basename(audio_path)}")
        return None
    
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
        
        # 使用线程池并行处理音频片段
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建任务字典，映射片段索引和对应的Future对象
            future_to_segment = {
                executor.submit(self.recognize_audio, os.path.join(self.temp_segments_dir, segment_file)): 
                (i, segment_file)
                for i, segment_file in enumerate(segment_files)
            }
            
            # 收集结果，并添加中断检查
            try:
                for future in concurrent.futures.as_completed(future_to_segment):
                    if self.interrupt_received:
                        logging.warning("检测到中断，正在取消剩余任务...")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                        
                    i, segment_file = future_to_segment[future]
                    try:
                        text = future.result(timeout=60)  # 添加超时以避免无限等待
                        if text:
                            segment_results[i] = text
                            logging.info(f"  ├─ 成功识别: {segment_file}")
                        else:
                            logging.warning(f"  ├─ 识别失败: {segment_file}")
                    except concurrent.futures.TimeoutError:
                        logging.warning(f"  ├─ 识别超时: {segment_file}")
                    except Exception as exc:
                        logging.error(f"  ├─ 识别出错: {segment_file} - {str(exc)}")
            except KeyboardInterrupt:
                logging.warning("检测到用户中断，正在取消剩余任务...")
                executor.shutdown(wait=False, cancel_futures=True)
                self.interrupt_received = True
        
        return segment_results
    
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
        # 如果没有中断并且有失败的片段，则进行重试
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
            still_failed = []
            
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
                        try:
                            text = future.result(timeout=60)
                            if text:
                                segment_results[idx] = text
                                logging.info(f"  ├─ 重试成功: {segment_file}")
                            else:
                                still_failed.append((idx, segment_file))
                                logging.warning(f"  ├─ 重试失败: {segment_file}")
                        except concurrent.futures.TimeoutError:
                            still_failed.append((idx, segment_file))
                            logging.warning(f"  ├─ 重试超时: {segment_file}")
                        except Exception as exc:
                            still_failed.append((idx, segment_file))
                            logging.error(f"  ├─ 重试出错: {segment_file} - {str(exc)}")
                except KeyboardInterrupt:
                    logging.warning("检测到用户中断，正在取消剩余重试任务...")
                    retry_executor.shutdown(wait=False, cancel_futures=True)
                    self.interrupt_received = True
            
            failed_segments = still_failed
        
        return segment_results
    
    def prepare_result_text(self, segment_files: List[str], 
                          segment_results: Dict[int, str]) -> str:
        """
        准备最终的识别结果文本
        
        Args:
            segment_files: 所有音频片段文件名列表
            segment_results: 识别结果字典
            
        Returns:
            合并格式化后的文本
        """
        # 按顺序合并所有文本片段
        all_text = []
        all_timestamps = []
        
        for i in range(len(segment_files)):
            if i in segment_results:
                all_text.append(segment_results[i])
                # 简单估算时间戳，每个片段30秒
                all_timestamps.append({
                    'start': i * 30,
                    'end': (i + 1) * 30
                })
            else:
                all_text.append("[无法识别的音频片段]")
                all_timestamps.append({
                    'start': i * 30,
                    'end': (i + 1) * 30
                })
        
        # 格式化文本以提高可读性
        if self.format_text:
            full_text = TextFormatter.format_segment_text(
                all_text, 
                timestamps=all_timestamps if self.include_timestamps else None,
                include_timestamps=self.include_timestamps,
                separate_segments=True  # 启用分片分隔
            )
        else:
            # 如果不格式化，仍使用原来的合并方式
            full_text = "\n\n".join([text for text in all_text if text and text != "[无法识别的音频片段]"])
        
        return full_text
    
    def process_single_file(self, input_path: str) -> bool:
        """
        处理单个音频文件
        
        Args:
            input_path: 音频文件路径
            
        Returns:
            处理是否成功
        """
        filename = os.path.basename(input_path)
        
        try:
            # 记录单个文件处理开始时间
            file_start_time = time.time()
            
            # 分割音频为较小片段
            segment_files = self.split_audio_file(input_path)
            if not segment_files:
                logging.error(f"分割 {filename} 失败，跳过此文件")
                return False
            
            # 处理音频片段
            segment_results = self.process_audio_segments(segment_files)
            
            # 如果处理被中断，保存当前结果并退出
            if self.interrupt_received:
                logging.warning("处理被中断，尝试保存已完成的识别结果...")
            else:
                # 重试失败的片段
                segment_results = self.retry_failed_segments(segment_files, segment_results)
            
            # 准备结果文本
            full_text = self.prepare_result_text(segment_files, segment_results)
            
            # 保存结果到文件
            output_file = os.path.join(self.output_folder, filename.replace(".mp3", ".txt"))
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            # 统计识别结果
            success_count = len(segment_results)
            fail_count = len(segment_files) - success_count
            
            # 计算并显示单个文件处理时长
            file_duration = time.time() - file_start_time
            formatted_duration = format_time_duration(file_duration)
            
            status = "（部分完成 - 已中断）" if self.interrupt_received else ""
            logging.info(f"✅ {filename} 转换完成{status}: 成功识别 {success_count}/{len(segment_files)} 片段" + 
                      (f", 失败 {fail_count} 片段" if fail_count > 0 else "") + 
                      f" - 耗时: {formatted_duration}")
            
            # 更新已处理记录
            self.processed_files[input_path] = {
                "processed_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "output_file": output_file,
                "interrupted": self.interrupt_received,
                "success_rate": f"{success_count}/{len(segment_files)}"
            }
            self._save_processed_records()
            
            logging.info(f"✅ 文件已处理完成并记录: {os.path.basename(input_path)}")
            return True
            
        except Exception as e:
            logging.error(f"❌ {filename} 处理失败: {str(e)}")
            return False
    
    def process_all_files(self) -> Tuple[int, float]:
        """
        处理所有MP3文件
        
        Returns:
            (处理文件数, 总耗时)
        """
        # 记录总体开始时间
        total_start_time = time.time()
        processed_files_count = 0
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
        try:
            # 检查网络连接
            try:
                logging.info("检查网络连接...")
                status_code = requests.get("https://www.google.com").status_code
                logging.info(f"网络连接状态: {status_code}")
            except Exception as e:
                logging.warning(f"网络连接检查失败: {str(e)}")
            
            # 遍历处理所有MP3文件
            for filename in os.listdir(self.mp3_folder):
                if self.interrupt_received:
                    logging.warning("程序被用户中断，停止处理新文件。")
                    break
                    
                if not filename.endswith(".mp3"):
                    continue
                    
                input_path = os.path.join(self.mp3_folder, filename)
                
                # 检查文件是否已处理
                if input_path in self.processed_files:
                    logging.info(f"跳过 {filename}（已处理）")
                    continue
                
                # 处理单个文件
                success = self.process_single_file(input_path)
                if success:
                    processed_files_count += 1
                
                if self.interrupt_received:
                    break
            
            # 计算总处理时长
            total_duration = time.time() - total_start_time
            
            # 所有识别完成后，显示服务使用统计
            self.print_statistics(processed_files_count, total_duration)
            
            return processed_files_count, total_duration
            
        finally:
            # 恢复原始信号处理程序
            signal.signal(signal.SIGINT, self.original_sigint_handler)
            
            # 清理临时文件
            self.cleanup()
    
    def print_statistics(self, processed_files_count: int, total_duration: float):
        """打印处理统计信息"""
        formatted_total_duration = format_time_duration(total_duration)
        
        # 显示ASR服务统计
        stats = asr_selector.get_service_stats()
        logging.info("\nASR服务使用统计:")
        for name, stat in stats.items():
            logging.info(f"  {name}: 使用次数 {stat['count']}, 成功率 {stat['success_rate']}, " +
                      f"可用状态: {'可用' if stat['available'] else '禁用'}")
                
        # 打印总结信息
        logging.info(f"\n总结: 处理了 {processed_files_count} 个文件, 总耗时: {formatted_total_duration}")
        
        # 显示平均每个文件处理时长
        if processed_files_count > 0:
            avg_time = total_duration / processed_files_count
            formatted_avg_time = format_time_duration(avg_time)
            logging.info(f"平均每个文件处理时长: {formatted_avg_time}")
    
    def cleanup(self):
        """清理临时文件和资源"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logging.info(f"✓ 临时文件已清理: {self.temp_dir}")
        except Exception as e:
            logging.warning(f"⚠️ 清理临时文件失败: {str(e)}")
        
        if self.interrupt_received:
            logging.info("\n程序已安全终止，已保存处理进度。您可以稍后继续处理剩余文件。")
