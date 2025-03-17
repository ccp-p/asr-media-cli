"""
文件处理模块
负责文件的监控和处理流程
"""
import os
import time
import logging
import traceback
from queue import Queue
from threading import Thread
from typing import Set, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from audio_tools.processing.text_processor import TextProcessor
from core.utils import load_json_file, save_json_file
from ..core.audio_extractor import AudioExtractor

class AudioFileHandler(FileSystemEventHandler):
    """音频文件监控处理器"""
    
    def __init__(self, processor, extensions=None):
        """
        初始化文件处理器
        
        Args:
            processor: 处理器实例
            extensions: 要监听的文件扩展名列表
        """
        self.processor = processor
        self.audio_extensions = extensions or ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.mp4']
        self.processing_queue = Queue()
        self.processed_files = set()  # 已处理的文件跟踪
        self._start_worker_thread()
    
    def on_created(self, event):
        """当文件被创建时触发"""
        self._handle_file_event(event.src_path)
        
    def on_modified(self, event):
        """当文件被修改时触发"""
        # 我们不处理修改事件，因为创建时已经处理了文件
        pass
    
    def _is_audio_file(self, filepath):
        """检查文件是否是支持的音频文件类型"""
        if not os.path.isfile(filepath):
            return False
        _, ext = os.path.splitext(filepath)
        return ext.lower() in self.audio_extensions
    
    def _handle_file_event(self, filepath):
        """处理文件事件的统一入口"""
        # 如果不是音频文件或已在队列中，则跳过
        if not self._is_audio_file(filepath) or filepath in self.processed_files:
            return
            
        # 添加到已处理文件集合
        self.processed_files.add(filepath)
        logging.info(f"检测到新音频文件：{filepath}")
        
        # 将文件添加到处理队列
        self.processing_queue.put(filepath)
    
    def _start_worker_thread(self):
        """启动工作线程处理文件队列"""
        def worker():
            while True:
                try:
                    filepath = self.processing_queue.get()
                    # 等待文件写入完成
                    time.sleep(2)
                    
                    # 确保文件仍然存在
                    if not os.path.exists(filepath):
                        logging.warning(f"文件不再存在，跳过处理: {filepath}")
                        continue
                        
                    # 处理文件
                    try:
                        logging.info(f"开始处理文件: {filepath}")
                        self.processor.process_file(filepath)
                        logging.info(f"文件处理完成: {filepath}")
                    except Exception as e:
                        logging.error(f"处理文件时出错 {filepath}: {str(e)}")
                        traceback.print_exc()
                    finally:
                        # 完成任务
                        self.processing_queue.task_done()
                except Exception as e:
                    logging.error(f"工作线程异常: {str(e)}")
                    traceback.print_exc()
        
        # 创建并启动工作线程
        thread = Thread(target=worker, daemon=True)
        thread.start()

class FileProcessor:
    """文件处理器，负责整体文件处理流程"""
    
    def __init__(self, 
                media_folder: str,
                output_folder: str,
                temp_segments_dir: str,
                transcription_processor,
                audio_extractor: Optional[AudioExtractor] = None,
                progress_callback: Optional[Callable] = None,
                process_video: bool = True,
                extract_audio_only: bool = False,
                format_text: bool = True,
                include_timestamps: bool = True,
                max_retries: int = 3):
        """
        初始化文件处理器
        
        Args:
            media_folder: 媒体文件夹路径
            output_folder: 输出文件夹路径
            temp_segments_dir: 临时片段目录
            transcription_processor: 转写处理器实例
            audio_extractor: 音频提取器实例
            progress_callback: 进度回调函数
            process_video: 是否处理视频文件
            extract_audio_only: 是否仅提取音频
            format_text: 是否格式化文本
            include_timestamps: 是否包含时间戳
            max_retries: 最大重试次数
        """
        self.media_folder = media_folder
        self.output_folder = output_folder
        self.temp_segments_dir = temp_segments_dir
        self.transcription_processor = transcription_processor
        self.audio_extractor = audio_extractor
        self.progress_callback = progress_callback
        self.process_video = process_video
        self.extract_audio_only = extract_audio_only
        self.format_text = format_text
        self.include_timestamps = include_timestamps
        self.max_retries = max_retries
        self.processed_record_file = os.path.join(self.output_folder, "processed_audio_files.json")
        self.processed_audio = load_json_file(self.processed_record_file)
        # 创建输出目录
        os.makedirs(output_folder, exist_ok=True)
        
        # 设置支持的文件类型
        self.video_extensions = ['.mp4', '.mov', '.avi'] if process_video else []
        
        # 初始化文本处理器
        self.text_processor = TextProcessor(
            output_folder=output_folder,
            format_text=format_text,
            include_timestamps=include_timestamps,
            progress_callback=progress_callback
        )
    def _is_recognized_file(self, filepath: str) -> bool:
        """检查文件是否已处理过"""
        # 如果输出文件已存在且文件已经处理过
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        
        output_path = os.path.join(self.output_folder, f"{base_name}.txt")
        
        audio_path = os.path.join(self.output_folder, f"{base_name}.mp3")
        # os.path.normpath(audio_path)
        isSamePath = lambda x: os.path.normpath(x)
        isInFile = [isSamePath(audio_path) == isSamePath(key) for key in self.processed_audio.keys()]
        
        res = any([os.path.exists(output_path), any(isInFile)])
        return res
        
        
    
    def process_file(self, filepath: str) -> bool:
        """
        处理单个文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            处理是否成功
        """
        filename = os.path.basename(filepath)
        file_extension = os.path.splitext(filename)[1].lower()
        
        try:
            # 处理视频文件 - 需要先提取音频
            if self._is_recognized_file(filepath):
                logging.info(f"文件已处理过: {filename}跳过")
                return True
            elif file_extension in self.video_extensions:
                return self._process_video_file(filepath)
            # 处理音频文件
            elif file_extension == '.mp3':
                return self._process_audio_file(filepath)
            else:
                logging.warning(f"不支持的文件类型: {filename}")
                return False
                
        except Exception as e:
            logging.error(f"处理文件时出错 {filename}: {str(e)}")
            return False
    
    def _process_video_file(self, video_path: str) -> bool:
        """处理视频文件"""
        filename = os.path.basename(video_path)
        logging.info(f"处理视频文件: {filename}")
        
        # 提取音频
        audio_path, is_new = self.audio_extractor.extract_audio_from_video(
            video_path, 
            self.output_folder
        )
        
        if not audio_path:
            logging.error(f"从视频提取音频失败: {filename}")
            return False
        
        # 如果只需要提取音频，到此为止
        if self.extract_audio_only:
            if is_new:
                logging.info(f"已提取音频: {audio_path}")
            else:
                logging.info(f"已存在音频: {audio_path}")
            return True
        
        # 继续处理提取出的音频文件
        return self._process_audio_file(audio_path)
    
    def _process_audio_file(self, audio_path: str) -> bool:
        """处理音频文件"""
        filename = os.path.basename(audio_path)
        logging.info(f"处理音频文件: {filename}")
        
        try:
            # 分割音频为片段
            segment_files = self.audio_extractor.split_audio_file(audio_path)
            if not segment_files:
                logging.error(f"分割音频失败: {filename}")
                return False
            
            # 处理音频片段
            segment_results = self.transcription_processor.process_audio_segments(segment_files)
            
            # 重试失败的片段
            if segment_results:
                segment_results = self.transcription_processor.retry_failed_segments(
                    segment_files, 
                    segment_results
                )
            
            # 处理转写结果，生成文本文件
            if self.progress_callback:
                self.progress_callback(
                    0,
                    1,
                    "准备生成文本文件..."
                )
            
            # 准备元数据
            metadata = {
                "原始文件": filename,
                "处理时间": time.strftime("%Y-%m-%d %H:%M:%S"),
                "识别成功率": f"{len(segment_results)}/{len(segment_files)} 片段",
                "音频长度": f"{len(segment_files) * 30}秒"
            }
            
            # 准备文本内容
            result_text = self.text_processor.prepare_result_text(
                segment_files=segment_files,
                segment_results=segment_results,
                metadata=metadata
            )
            
            if not result_text:
                logging.warning(f"无有效转写结果: {filename}")
                return False
            
            # 保存文本文件
            output_file = self.text_processor.save_result_text(
                text=result_text,
                filename=filename,
            )
            
            if self.progress_callback:
                self.progress_callback(
                    1,
                    1,
                    f"文本生成完成: {os.path.basename(output_file)}"
                )
                
            logging.info(f"转写结果已保存到: {output_file}")
            
            # self.processed_files[audio_path]["processed_parts"].append(part_num)
            # self.processed_files[audio_path]["total_parts"] = total_parts
            self.processed_audio[audio_path]["last_processed_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            # self.processed_files[audio_path]["part_stats"] = part_stats
                
            self._save_processed_records()
            return True
            
        except Exception as e:
            logging.error(f"处理音频文件时出错 {filename}: {str(e)}")
            return False
    def _save_processed_records(self):
        """保存已处理的文件记录"""
        save_json_file(self.processed_record_file, self.processed_audio)

    def start_file_monitoring(self) -> 'Observer':
        """
        启动文件监控
        
        Returns:
            文件监控器实例
        """
        event_handler = AudioFileHandler(self)
        observer = Observer()
        observer.schedule(event_handler, self.media_folder, recursive=False)
        observer.start()
        logging.info(f"开始监控目录: {self.media_folder}")
        return observer