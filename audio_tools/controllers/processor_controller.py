"""
处理器控制器模块
负责协调各个组件的工作，管理整体处理流程
"""
import os
import tempfile
import logging
import signal
import time
from typing import Optional, Dict, Any
from ..core.audio_extractor import AudioExtractor
from ..core.file_utils import format_time_duration
from ..core.error_handler import ErrorHandler, AudioToolsError
from ..core.config_manager import ConfigManager, ConfigValidationError
from ..processing.transcription_processor import TranscriptionProcessor
from ..processing.file_processor import FileProcessor
from ..processing.progress_manager import ProgressManager

class ProcessorController:
    """处理器控制器，协调各个组件工作"""
    
    def __init__(self, config_file: Optional[str] = None, **config_params):
        """
        初始化处理器控制器
        
        Args:
            config_file: 可选的配置文件路径
            **config_params: 直接传入的配置参数，优先级高于配置文件
        """
        # 初始化配置管理器并更新配置
        self.config_manager = ConfigManager(config_file)
        if config_params:
            self.config_manager.update(config_params)
        config = self.config_manager.as_dict
        
        # 设置日志级别
        log_level = getattr(logging, config['log_level'].upper(), logging.INFO)
        log_file = config.get('log_file')
        
        handlers = [logging.StreamHandler()]
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        # 从配置创建临时目录
        self.temp_dir = config.get('temp_dir') or tempfile.mkdtemp()
        self.temp_segments_dir = os.path.join(self.temp_dir, "segments")
        os.makedirs(self.temp_segments_dir, exist_ok=True)
        
        # 创建错误处理器
        self.error_handler = ErrorHandler(
            max_retries=config['max_retries'],
            retry_delay=config['retry_delay']
        )
        
        # 初始化进度管理器
        self.progress_manager = ProgressManager(show_progress=config['show_progress'])
        
        # 初始化ASR管理器 (从原有代码导入)
        from core.asr_manager import ASRManager
        self.asr_manager = ASRManager(
            use_jianying_first=config['use_jianying_first'],
            use_kuaishou=config['use_kuaishou'],
            use_bcut=config['use_bcut']
        )
        
        # 初始化组件
        self.audio_extractor = AudioExtractor(
            temp_segments_dir=self.temp_segments_dir,
            progress_callback=self._progress_callback
        )
        
        self.transcription_processor = TranscriptionProcessor(
            asr_manager=self.asr_manager,
            temp_segments_dir=self.temp_segments_dir,
            max_workers=config['max_workers'],
            max_retries=config['max_retries'],
            progress_callback=self._progress_callback
        )
        
        self.file_processor = FileProcessor(
            media_folder=config['media_folder'],
            output_folder=config['output_folder'],
            temp_segments_dir=self.temp_segments_dir,
            transcription_processor=self.transcription_processor,
            audio_extractor=self.audio_extractor,
            progress_callback=self._progress_callback,
            process_video=config['process_video'],
            extract_audio_only=config['extract_audio_only'],
            format_text=config['format_text'],
            include_timestamps=config['include_timestamps'],
            max_part_time=config['max_part_time'],
            max_retries=config['max_retries']
        )
        
        # 初始化统计信息
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_files': 0,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'total_segments': 0,
            'successful_segments': 0,
            'failed_segments': 0
        }
        
        # 注册信号处理
        self._setup_signal_handlers()
        
        # 打印初始配置
        self.config_manager.print_config()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def _handle_interrupt(self, sig, frame):
        """处理中断信号"""
        logging.warning("\n\n⚠️ 接收到中断信号，正在安全终止程序...\n稍等片刻，正在保存已处理的数据...\n")
        self.transcription_processor.set_interrupt_flag(True)
        # 关闭所有进度条
        self.progress_manager.close_all_progress_bars("已中断")
        # 打印统计信息
        self._print_final_stats()
    
    def _progress_callback(self, current: int, total: int, message: Optional[str] = None, context: Optional[str] = None):
        """
        进度回调处理 - 接受但忽略state参数
        
        Args:
            current: 当前进度
            total: 总进度
            message: 可选的进度消息
            context: 上下文标识符，用于区分不同的处理层级
        """
        if not self.config.get('show_progress', True):
            return
            
        # 如果没有提供消息，使用默认消息
        if message is None:
            message = f"处理进度: {current}/{total}"
            
        # 使用固定的进度条名称
        progress_name = f"{context}_progress" if context else "main_progress"
        progress_bar = self.progress_manager.get_progress_bar(progress_name)
        
        # 创建或更新对应的进度条
        if not self.progress_manager.has_progress_bar(progress_name):
            prefix = f"{context or '处理'}"
            self.progress_manager.create_progress_bar(
                progress_name,
                total,
                prefix,
            )
        # 对比bar的值，如果total值变化，以新的total值为准，更新进度条
        elif progress_bar and progress_bar.total != total:
            # 使用新的total重置进度条
            self.progress_manager.reset_progress_bar(progress_name, total)
            
        # 更新进度
        self.progress_manager.update_progress(
            progress_name,
            current,
            message
        )
        
        # 如果进度完成，关闭进度条
        if current >= total:
            self.progress_manager.finish_progress(progress_name, message or "完成")
    def _update_stats(self, file_stats: Dict[str, Any]):
        """更新统计信息"""
        self.stats['processed_files'] += 1
        if file_stats.get('success', False):
            self.stats['successful_files'] += 1
        else:
            self.stats['failed_files'] += 1
            
        self.stats['total_segments'] += file_stats.get('total_segments', 0)
        self.stats['successful_segments'] += file_stats.get('successful_segments', 0)
        self.stats['failed_segments'] += (
            file_stats.get('total_segments', 0) - 
            file_stats.get('successful_segments', 0)
        )
    
    def _print_final_stats(self):
        """打印最终统计信息"""
        self.stats['end_time'] = time.time()
        total_duration = self.stats['end_time'] - self.stats['start_time']
        
        logging.info("\n处理统计:")
        logging.info(f"总计处理文件: {self.stats['processed_files']}/{self.stats['total_files']}")
        logging.info(f"成功处理: {self.stats['successful_files']} 个文件")
        logging.info(f"处理失败: {self.stats['failed_files']} 个文件")
        logging.info(f"片段统计:")
        logging.info(f"  - 总计片段: {self.stats['total_segments']}")
        logging.info(f"  - 成功识别: {self.stats['successful_segments']}")
        logging.info(f"  - 识别失败: {self.stats['failed_segments']}")
        if self.stats['total_segments'] > 0:
            success_rate = (self.stats['successful_segments'] / self.stats['total_segments']) * 100
            logging.info(f"识别成功率: {success_rate:.1f}%")
        
        logging.info(f"\n总耗时: {format_time_duration(total_duration)}")
        
        # 显示ASR服务统计
        stats = self.asr_manager.get_service_stats()
        logging.info("\nASR服务使用统计:")
        for name, stat in stats.items():
            logging.info(f"  {name}: 使用次数 {stat['count']}, 成功率 {stat['success_rate']}, " +
                      f"可用状态: {'可用' if stat['available'] else '禁用'}")
        
        # 显示错误统计
        self.error_handler.print_error_stats()
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config_manager.as_dict
    
    def update_config(self, config_dict: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config_dict: 新的配置字典
        """
        try:
            self.config_manager.update(config_dict)
            logging.info("配置已更新")
            self.config_manager.print_config()
        except ConfigValidationError as e:
            logging.error(f"更新配置失败: {str(e)}")
    
    def save_config(self, config_file: str):
        """
        保存配置到文件
        
        Args:
            config_file: 配置文件路径
        """
        try:
            self.config_manager.save_config(config_file)
            logging.info(f"配置已保存到: {config_file}")
        except ConfigValidationError as e:
            logging.error(f"保存配置失败: {str(e)}")
    
    def start_processing(self):
        """启动处理流程"""
        try:
            self.stats['start_time'] = time.time()
            
            if self.config['watch_mode']:
                 # 处理已有文件
                self._process_existing_files()
                
                self._start_watch_mode()
            else:
                self._process_existing_files()
                
        except KeyboardInterrupt:
            logging.warning("\n程序已被用户中断")
        except Exception as e:
            logging.error(f"\n程序执行出错: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup()
            # 打印最终统计信息
            self._print_final_stats()
    
    def _start_watch_mode(self):
        """启动监听模式"""
        logging.info(f"启动监听模式，监控目录: {self.config['media_folder']}")
        
        # 启动对主媒体文件夹的监控
        main_observer = self.file_processor.start_file_monitoring()
        
        # 导入特殊文件夹监控模块
        from ..processing.folder_monitor import start_dest_folder_monitoring
        
        # 设置下载目录和目标目录
        download_dest = self.config['output_folder']  
        download_target = self.config['media_folder']
        
        # 启动对下载目录的监控
        dest_observer = start_dest_folder_monitoring(download_dest, download_target)
        logging.info(f"启动特殊监控: {download_dest} -> {download_target}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # 停止所有观察者
            main_observer.stop()
            dest_observer.stop()
            
            main_observer.join()
            dest_observer.join()
            logging.info("\n监听模式已停止")
    
    def _process_existing_files(self):
        """处理已存在的文件"""
        media_files = []
        
        # 处理MP3文件
        mp3_files = [f for f in os.listdir(self.config['media_folder']) 
                    if f.lower().endswith('.mp3')]
        media_files.extend(mp3_files)
        
        # 如果开启视频处理，获取视频文件
        if self.config['process_video']:
            video_files = [f for f in os.listdir(self.config['media_folder']) 
                         if any(f.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi'])]
            media_files.extend(video_files)
        
        if not media_files:
            logging.info("没有找到需要处理的媒体文件")
            return
        # 过滤已处理的文件
        
        filtered_files = []
        for filename in media_files:
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(self.config['output_folder'], f"{base_name}.txt")
            
            if self.file_processor.is_recognized_file(output_path):
                logging.info(f"跳过已处理的文件: {filename}")
            else:
                filtered_files.append(filename)
        
        if not filtered_files:
            logging.info("所有文件已处理完毕，没有新文件需要处理")
            return
        
        logging.info(f"找到 {len(filtered_files)}/{len(media_files)} 个新文件需要处理")
    
        self.stats['total_files'] = len(media_files)
        
        # 创建总体进度条
        self.progress_manager.create_progress_bar(
            "total_progress",
            len(media_files),
            "处理媒体文件",
            f"总计 {len(media_files)} 个文件"
        )
        
        # 处理所有文件
        for i, filename in enumerate(media_files):
            filepath = os.path.join(self.config['media_folder'], filename)
            success = self.error_handler.safe_execute(
                self.file_processor.process_file,
                filepath,
                error_msg=f"处理文件失败: {filename}"
            )
            
            # 更新统计信息
            self._update_stats({'success': success})
            
              # 打印当前ASR服务使用统计
            self._print_asr_stats()
            
            # 更新总体进度
            self.progress_manager.update_progress(
                "total_progress",
                i + 1,
                f"已处理 {i+1}/{len(media_files)} 个文件"
            )
        
        # 完成总体进度
        self.progress_manager.finish_progress(
            "total_progress",
            f"完成处理 {len(media_files)} 个文件"
        )
    
    def _print_asr_stats(self):
        """打印ASR服务使用统计信息"""
        stats = self.asr_manager.get_service_stats()
        logging.info("\nASR服务使用统计:")
        for name, stat in stats.items():
            logging.info(f"  - {name}: 成功 {stat.get('success', 0)} 次, "
                        f"失败 {stat.get('failed', 0)} 次, "
                        f"总用时 {format_time_duration(stat.get('time_used', 0))}")

    def _cleanup(self):
        """清理资源"""
        logging.info("清理临时文件和资源...")
        
        # 关闭所有进度条
        self.progress_manager.close_all_progress_bars("清理中")
        
        # 关闭ASR管理器资源
        if hasattr(self.asr_manager, 'close'):
            try:
                self.asr_manager.close()
            except Exception as e:
                logging.warning(f"关闭ASR管理器时出错: {str(e)}")
        
        # 清理临时目录
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logging.warning(f"清理临时目录时出错: {str(e)}")
        
        # 恢复原始信号处理器
        signal.signal(signal.SIGINT, self.original_sigint_handler)