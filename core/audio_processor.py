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
import subprocess
from tqdm import tqdm

# 导入工具函数 - 使用相对导入
from .utils import format_time_duration, load_json_file, save_json_file, ProgressBar, LogConfig

# 导入ASR模块和ASR管理器
from .asr import ASRDataSeg
from .asr_manager import ASRManager
from .text_formatter import TextFormatter
from .progress_manager import ProgressManager
from .audio_splitter import AudioSplitter
from .transcription_manager import TranscriptionManager  # 导入TranscriptionManager

class AudioProcessor:
    """音频处理类，负责音频分割、转写和文本整合"""
    
    def __init__(self, **kwargs):
        """
        音频处理器初始化
        
        Args:
            **kwargs: 配置参数
        """
        # 从kwargs获取参数，若不存在则使用默认值
        self.media_folder = kwargs.get('media_folder', './media')
        self.output_folder = kwargs.get('output_folder', './output')
        self.max_retries = kwargs.get('max_retries', 3)
        self.max_workers = kwargs.get('max_workers', 4)
        self.use_jianying_first = kwargs.get('use_jianying_first', True)
        self.use_kuaishou = kwargs.get('use_kuaishou', True)
        self.use_bcut = kwargs.get('use_bcut', True)
        self.format_text = kwargs.get('format_text', True)
        self.include_timestamps = kwargs.get('include_timestamps', True)
        self.show_progress = kwargs.get('show_progress', True)
        self.process_video = kwargs.get('process_video', True)
        self.video_extensions = kwargs.get('video_extensions', ['.mp4', '.mov', '.avi'])
        self.extract_audio_only = kwargs.get('extract_audio_only', False)
        # 创建输出目录
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
        
        # 初始化ASR服务管理器
        self.asr_manager = ASRManager(
            use_jianying_first=self.use_jianying_first,
            use_kuaishou=self.use_kuaishou,
            use_bcut=self.use_bcut
        )
        
        # 初始化进度条管理器
        self.progress_manager = ProgressManager(show_progress=self.show_progress)
        
        # 初始化音频分割器
        self.audio_splitter = AudioSplitter(self.temp_segments_dir)

        # 初始化转录管理器
        self.transcription_manager = TranscriptionManager(
            asr_manager=self.asr_manager,
            temp_segments_dir=self.temp_segments_dir,
            max_workers=self.max_workers,
            max_retries=self.max_retries,
            progress_callback=self.transcription_progress_callback
        )
    
    # 新增的转录进度回调方法
    def transcription_progress_callback(self, state: str, current: int, total: int, message: str):
        """
        转录进度回调函数
        
        Args:
            state: 当前状态 (recognize, retry_1, retry_2...)
            current: 当前进度
            total: 总数
            message: 显示消息
        """
        # 根据状态决定使用哪个进度条
        if state == 'recognize':
            progress_name = 'recognize_progress'
            prefix = "识别进度"
        elif state.startswith('retry_'):
            retry_round = state.split('_')[1]
            progress_name = f'retry_{retry_round}_progress'
            prefix = f"重试 #{retry_round}"
        else:
            progress_name = 'unknown_progress'
            prefix = "处理中"
        
        # 如果进度条不存在，创建它
        if not self.progress_manager.has_progress_bar(progress_name):
            self.create_progress_bar(progress_name, total, prefix, message)
        
        # 更新进度
        if current >= total:  # 如果是完成状态
            self.finish_progress(progress_name, message)
        else:
            self.update_progress(progress_name, current, message)
    
    # 使用ProgressManager替换原有的进度条方法
    def create_progress_bar(self, name: str, total: int, prefix: str, suffix: str = "") -> Optional[ProgressBar]:
        """创建并存储一个进度条"""
        return self.progress_manager.create_progress_bar(name, total, prefix, suffix)
    
    def update_progress(self, name: str, current: Optional[int] = None, suffix: Optional[str] = None) -> None:
        """更新指定进度条"""
        self.progress_manager.update_progress(name, current, suffix)
    
    def finish_progress(self, name: str, suffix: Optional[str] = None) -> None:
        """完成指定进度条"""
        self.progress_manager.finish_progress(name, suffix)
    
    # 新增: 安全执行函数的包装器
    def safe_execute(self, func: Callable, error_msg: str = "执行出错", progress_name: Optional[str] = None, 
                  error_suffix: Optional[str] = None, *args, **kwargs) -> Any:
        """
        安全执行函数，处理异常并更新进度条
        
        Args:
            func: 要执行的函数
            error_msg: 出错时的日志消息
            progress_name: 相关进度条名称
            error_suffix: 出错时的进度条后缀，默认使用错误消息
            args, kwargs: 传递给func的参数
            
        Returns:
            函数执行结果，出错时返回None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if error_suffix is None:
                error_suffix = f"失败 - {str(e)}"
                
            logging.error(f"{error_msg}: {str(e)}")
            
            if progress_name:
                self.finish_progress(progress_name, error_suffix)
                
            return None
    
    def _save_processed_records(self):
        """保存已处理文件记录"""
        save_json_file(self.processed_record_file, self.processed_files)
    
    def handle_interrupt(self, sig, frame):
        """处理中断信号"""
        logging.warning("\n\n⚠️ 接收到中断信号，正在安全终止程序...\n稍等片刻，正在保存已处理的数据...\n")
        self.interrupt_received = True
        # 设置转录管理器的中断标志
        self.transcription_manager.set_interrupt_flag(True)
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
        
        # 创建进度条，但先不更新
        progress_name = f"split_{filename}"
        self.create_progress_bar(
            progress_name,
            total=100,  # 临时设置，将在回调中更新
            prefix=f"分割 {filename}", 
            suffix="准备中"
        )
        
        # 定义进度回调函数
        def progress_callback(current: int, total: int, message: str):
            # 第一次调用时更新进度条总数
            if current == 0 and hasattr(self, "progress_manager") and progress_name in self.progress_manager.progress_bars:
                self.progress_manager.progress_bars[progress_name].total = total
            
            self.update_progress(progress_name, current, message)
            
            # 如果是结束消息，完成进度条
            if current >= total:
                self.finish_progress(progress_name, message)
        
        # 设置音频分割器的回调
        self.audio_splitter.progress_callback = progress_callback
        
        # 使用安全执行器处理错误
        result = self.safe_execute(
            self.audio_splitter.split_audio_file,
            error_msg=f"分割音频文件 {filename} 失败",
            progress_name=progress_name,
            input_path=input_path,
            segment_length=segment_length
        )
        
        return result or []
    
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
    
    # 删除旧的process_audio_segments方法，使用TranscriptionManager代替
    # 删除旧的retry_failed_segments方法，使用TranscriptionManager代替
    
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
        
        # 显示文本准备进度条
        text_prep_name = "text_preparation"
        self.create_progress_bar(
            text_prep_name,
            total=len(segment_files),
            prefix="文本准备",
            suffix="处理中"
        )
        
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
                
            # 更新进度条
            self.update_progress(
                text_prep_name, 
                i + 1, 
                f"处理片段 {i+1}/{len(segment_files)}"
            )
        
        # 完成文本准备进度条
        self.finish_progress(text_prep_name, "文本片段处理完成")
        
        # 格式化文本以提高可读性
        if self.format_text:
            format_name = "format_text"
            self.create_progress_bar(
                format_name,
                total=1,
                prefix="格式化文本",
                suffix="处理中"
            )
            
            full_text = TextFormatter.format_segment_text(
                all_text, 
                timestamps=all_timestamps if self.include_timestamps else None,
                include_timestamps=self.include_timestamps,
                separate_segments=True  # 启用分片分隔
            )
            
            self.finish_progress(format_name, "格式化完成")
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
            # 创建单个文件总进度条
            file_progress = self.create_progress_bar(
                "file_progress",
                total=4,  # 分割、识别、重试、保存 4个阶段
                prefix=f"处理 {filename}",
                suffix="准备中"
            )
            
            # 记录单个文件处理开始时间
            file_start_time = time.time()
            
            # 分割音频为较小片段
            self.update_progress("file_progress", 0, "分割音频")
            segment_files = self.split_audio_file(input_path)
            
            if not segment_files:
                logging.error(f"分割 {filename} 失败，跳过此文件")
                self.finish_progress("file_progress", "分割失败，跳过")
                return False
            
            # 使用转录管理器处理音频片段
            self.update_progress("file_progress", 1, "识别音频")
            
            # 设置转录管理器的中断标志为False，以便重新开始
            self.transcription_manager.set_interrupt_flag(False)
            
            # 调用转录管理器的transcribe_segments方法
            segment_results, stats = self.transcription_manager.transcribe_segments(segment_files)
            
            # 检查中断状态
            self.interrupt_received = self.transcription_manager.interrupt_received
            
            # 识别已经完成，更新进度到保存阶段
            self.update_progress("file_progress", 3, "生成文本")
            
            # 准备结果文本
            full_text = self.prepare_result_text(segment_files, segment_results)
            
            # 保存结果到文件
            output_file = os.path.join(self.output_folder, filename.replace(".mp3", ".txt"))
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            # 计算并显示单个文件处理时长
            file_duration = time.time() - file_start_time
            formatted_duration = format_time_duration(file_duration)
            
            status = "（部分完成 - 已中断）" if self.interrupt_received else ""
            
            # 更新已处理记录
            self.processed_files[input_path] = {
                "processed_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "output_file": output_file,
                "interrupted": self.interrupt_received,
                "success_rate": f"{stats['success_count']}/{stats['total_count']}",
                "duration": formatted_duration
            }
            self._save_processed_records()
            
            # 完成文件处理进度条
            success_rate = f"{stats['success_count']}/{stats['total_count']}"
            self.finish_progress("file_progress", f"完成 - 成功率: {success_rate}, 耗时: {formatted_duration}")
            
            logging.info(f"✅ {filename} 转换完成{status}: 成功识别 {stats['success_count']}/{stats['total_count']} 片段" + 
                      (f", 失败 {stats['fail_count']} 片段" if stats['fail_count'] > 0 else "") + 
                      f" - 耗时: {formatted_duration}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ {filename} 处理失败: {str(e)}")
            # 确保进度条完成
            self.finish_progress("file_progress", f"处理失败: {str(e)}")
            return False
    
    def process_all_files(self) -> Tuple[int, float]:
        """
        处理所有媒体文件（音频和视频）
        
        Returns:
            (处理文件数, 总耗时)
        """
        # 记录总体开始时间
        total_start_time = time.time()
        
        try:
            # 设置信号处理
            signal.signal(signal.SIGINT, self.handle_interrupt)
            
            # 检查网络连接
            try:
                logging.info("检查网络连接...")
                status_code = requests.get("https://www.google.com").status_code
                logging.info(f"网络连接状态: {status_code}")
            except Exception as e:
                logging.warning(f"网络连接检查失败: {str(e)}")
            
            # 获取所有媒体文件
            media_files = []
            
            # 处理MP3文件
            mp3_files = [f for f in os.listdir(self.media_folder) 
                        if f.lower().endswith('.mp3')]
            media_files.extend(mp3_files)
            
            # 如果开启视频处理，获取视频文件
            if self.process_video:
                video_files = [f for f in os.listdir(self.media_folder) 
                            if any(f.lower().endswith(ext) for ext in self.video_extensions)]
                # 从json文件中读取数据，如果存在对应的mp3文件，则不再处理
                processed_files_names = [os.path.basename(f) for f in self.processed_files.keys()]
                video_files = [f for f in video_files if f.replace(".mp4", ".mp3") not in processed_files_names
                               and f.replace(".mov", ".mp3") not in processed_files_names]
                media_files.extend(video_files)
            
            if not media_files:
                logging.warning(f"在 {self.media_folder} 中没有找到可处理的媒体文件")
                return 0, 0.0
            
            # 显示要处理的文件
            logging.info(f"找到 {len(media_files)} 个媒体文件需要处理")
            
            # 使用线程池并行处理文件
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 是否使用进度条
                if self.show_progress:
                    list(tqdm(
                        executor.map(self.process_file, media_files),
                        total=len(media_files),
                        desc="处理媒体文件"
                    ))
                else:
                    list(executor.map(self.process_file, media_files))
            
            processed_files_count = len(media_files)
            
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
    
    def extract_audio_from_video(self, video_path):
        """
        从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            tuple: (音频文件路径, 是否是新提取的), 失败则返回(None, False)
        """
        video_filename = os.path.basename(video_path)
        base_name = os.path.splitext(video_filename)[0]
        audio_path = os.path.join(self.output_folder, f"{base_name}.mp3")
        
        # 检查音频文件是否已经存在且在处理记录中
        if os.path.exists(audio_path):
            # 检查是否在已处理记录中
            if audio_path in self.processed_files:
                # 如果不是中断状态，则直接返回现有音频路径
                if not self.processed_files[audio_path].get('interrupted', False):
                    logging.info(f"音频已存在且已处理: {audio_path}")
                    return audio_path, False
            else:
                logging.info(f"音频已存在但未记录处理: {audio_path}")
                return audio_path, False
        
        # 创建进度条
        progress_name = f"extract_{video_filename}"
        self.create_progress_bar(
            progress_name,
            total=1,
            prefix=f"提取音频 {video_filename}",
            suffix="准备中"
        )
        
        # 定义进度回调函数
        def progress_callback(current: int, total: int, message: str):
            self.update_progress(progress_name, current, message)
            
            # 如果是结束消息，完成进度条
            if current >= total:
                self.finish_progress(progress_name, message)
        
        # 使用音频分割器提取音频
        return self.audio_splitter.extract_audio_from_video(
            video_path, 
            self.output_folder, 
            progress_callback
        )
    
    def process_file(self, filename):
        """
        处理单个媒体文件
        
        Args:
            filename: 媒体文件名
        """
        file_path = os.path.join(self.media_folder, filename)
        file_extension = os.path.splitext(filename)[1].lower()
        
        # 处理视频文件 - 需要先提取音频
        if file_extension in self.video_extensions:
            logging.info(f"处理视频文件: {filename}")
            
            # 检查对应的mp3文件是否已在处理记录中且已完成
            base_name = os.path.splitext(filename)[0]
            mp3_path = os.path.join(self.output_folder, f"{base_name}.mp3")
            if mp3_path in self.processed_files and not self.processed_files[mp3_path].get('interrupted', False):
                logging.info(f"跳过已处理的视频: {filename}")
                return
                
            # 提取音频
            audio_path, is_new = self.extract_audio_from_video(file_path)
            
            # 如果只需要提取音频，到此为止
            if self.extract_audio_only:
                if is_new:
                    logging.info(f"已提取音频: {audio_path}")
                else:
                    logging.info(f"已存在音频: {audio_path}")
                return
                
            # 继续处理提取出的音频文件
            if audio_path:
                self.transcribe_audio(audio_path, filename)
            else:
                logging.error(f"从视频提取音频失败: {filename}")
        
        # 处理音频文件
        elif file_extension == '.mp3':
            # 检查是否已处理
            if file_path in self.processed_files and not self.processed_files[file_path].get('interrupted', False):
                logging.info(f"跳过已处理的音频: {filename}")
                return
                
            logging.info(f"处理音频文件: {filename}")
            self.transcribe_audio(file_path, filename)
        
        else:
            logging.warning(f"不支持的文件类型: {filename}")
    
    def transcribe_audio(self, audio_path, original_filename):
        """
        将音频转录为文本
        
        Args:
            audio_path: 音频文件路径
            original_filename: 原始文件名
        """
        # 生成输出文本文件路径
        base_name = os.path.splitext(original_filename)[0]
        output_path = os.path.join(self.output_folder, f"{base_name}.txt")
        
        # 如果输出文件已存在且文件已经处理过且不是中断状态，则跳过
        if (os.path.exists(output_path) and 
            audio_path in self.processed_files and 
            not self.processed_files[audio_path].get('interrupted', False)):
            logging.info(f"跳过已处理的文件: {original_filename}")
            return
            
        try:
            # 记录开始处理
            logging.info(f"开始转录音频: {original_filename}")
            
            # 调用单文件处理方法
            success = self.process_single_file(audio_path)
            
            # 打印处理结果
            if success:
                logging.info(f"转录完成: {output_path}")
                
                # 如果是从视频提取的音频，删除音频文件以节省空间
                video_extensions = [ext for ext in self.video_extensions if original_filename.lower().endswith(ext)]
                if video_extensions and os.path.exists(audio_path):
                    logging.info(f"删除提取的音频文件: {audio_path}")
                    os.remove(audio_path)  # 删除已处理的音频文件
            else:
                logging.warning(f"转录失败: {original_filename}")
                
        except Exception as e:
            # 处理异常
            logging.error(f"转录音频时发生错误: {original_filename} - {str(e)}")
            
            # 记录失败状态
            self.processed_files[audio_path] = {
                "processed_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "failed",
                "error": str(e)
            }
            self._save_processed_records()
            
            # 如果是中断信号
            if self.interrupt_received:
                logging.warning(f"转录被用户中断: {original_filename}")
    
    def print_statistics(self, processed_files_count: int, total_duration: float):
        """打印处理统计信息"""
        formatted_total_duration = format_time_duration(total_duration)
        
        # 显示ASR服务统计
        stats = self.asr_manager.get_service_stats()
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
        logging.info("开始清理临时文件和资源...")
        
        # 1. 确保ASR管理器资源被释放
        if hasattr(self, 'asr_manager'):
            logging.info("关闭ASR管理器资源...")
            try:
                # 如果ASR管理器有close方法则调用，否则跳过
                if hasattr(self.asr_manager, 'close') and callable(getattr(self.asr_manager, 'close')):
                    self.asr_manager.close()
                logging.info("ASR管理器资源已关闭")
            except Exception as e:
                logging.warning(f"关闭ASR管理器资源时出错: {str(e)}")
        
        # 2. 关闭所有未完成的进度条
        if hasattr(self, 'progress_manager'):
            self.progress_manager.close_all_progress_bars("已终止")
        
        # 3. 使用超时机制清理临时文件
        try:
            logging.info(f"开始清理临时目录: {self.temp_dir}")
            
            # 检查目录是否存在
            if os.path.exists(self.temp_dir):
                # 使用单独的线程进行清理以避免阻塞
                def remove_temp_dir():
                    try:
                        shutil.rmtree(self.temp_dir, ignore_errors=True)
                    except Exception as e:
                        logging.warning(f"清理线程中出错: {str(e)}")
                
                # 创建清理线程
                import threading
                cleanup_thread = threading.Thread(target=remove_temp_dir, daemon=True)
                cleanup_thread.start()
                
                # 等待最多5秒
                cleanup_thread.join(timeout=5.0)
                
                # 检查是否成功删除
                if not cleanup_thread.is_alive():
                    if not os.path.exists(self.temp_dir):
                        logging.info(f"✓ 临时目录已成功删除: {self.temp_dir}")
                    else:
                        logging.warning(f"⚠️ 临时目录可能未完全删除: {self.temp_dir}")
                else:
                    logging.warning(f"⚠️ 清理临时目录超时，将继续执行（临时文件可能未完全删除）")
            else:
                logging.info(f"临时目录不存在，无需清理: {self.temp_dir}")
                
        except Exception as e:
            logging.warning(f"⚠️ 清理临时文件失败: {str(e)}")
        
        # 4. 根据中断状态显示不同消息
        if self.interrupt_received:
            logging.info("\n程序已安全终止，已保存处理进度。您可以稍后继续处理剩余文件。")
        else:
            logging.info("\n程序已完成所有任务并安全退出。")
        
        # 5. 最终的结束日志
        logging.info("=== 程序执行结束 ===")
