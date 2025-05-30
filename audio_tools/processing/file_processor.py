"""
文件处理模块
负责文件的监控和处理流程
"""
import os
import subprocess
import threading
import time
import logging
import traceback
from queue import Queue
from threading import Thread
from typing import Set, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from asr.utils import get_audio_duration
from audio_tools.processing.text_processor import TextProcessor
from core.utils import load_json_file, save_json_file
from ..core.audio_extractor import AudioExtractor

class AudioFileHandler(FileSystemEventHandler):
    def __init__(self, processor, extensions=None, debounce_seconds=5):
        super().__init__()
        self.processor = processor
        self.audio_extensions = extensions or ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.mp4']
        self.processing_queue = Queue()
        self.processed_files = set()  # 已处理的文件跟踪
        self.pending_files = {}  # 等待处理的文件及其定时器
        self.debounce_seconds = debounce_seconds
        self._start_worker_thread()
    
    def on_created(self, event):
        """当文件被创建时触发"""
        self._handle_file_event(event.src_path)
        
    def on_modified(self, event):
        """当文件被修改时触发"""
        self._handle_file_event(event.src_path)
    
    def _is_audio_file(self, filepath):
        """检查文件是否是支持的音频文件类型"""
        if not os.path.isfile(filepath):
            return False
        _, ext = os.path.splitext(filepath)
        return ext.lower() in self.audio_extensions
    
    def _handle_file_event(self, filepath):
        """处理文件事件的统一入口，使用防抖动技术"""
        # 如果不是音频文件或已在处理队列中，则跳过
        if not self._is_audio_file(filepath) or filepath in self.processed_files:
            return
        
        # 取消之前为此文件设置的任何待处理定时器
        if filepath in self.pending_files:
            self.pending_files[filepath].cancel()
        
        # 设置新的定时器
        timer = threading.Timer(
            self.debounce_seconds, 
            self._add_to_processing_queue, 
            args=[filepath]
        )
        timer.daemon = True
        self.pending_files[filepath] = timer
        timer.start()
        
        logging.debug(f"文件事件触发，设置处理延时: {filepath}")
    
    def _add_to_processing_queue(self, filepath):
        """将文件添加到处理队列"""
        # 检查文件是否仍然存在
        if not os.path.exists(filepath):
            if filepath in self.pending_files:
                del self.pending_files[filepath]
            return
        
        # 从待处理列表中移除
        if filepath in self.pending_files:
            del self.pending_files[filepath]
        
        # 检查文件是否已在已处理列表中
        if filepath in self.processed_files:
            return
        
        # 添加到已处理列表
        self.processed_files.add(filepath)
        
        logging.info(f"添加文件到处理队列: {filepath}")
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
        
    def _update_processed_records_on_rename(self, old_path, new_path):
        """当文件重命名时更新处理记录"""
        if old_path in self.processed_audio:
            # 将记录从旧路径转移到新路径
            self.processed_audio[new_path] = self.processed_audio.pop(old_path)
            logging.info(f"已更新处理记录: {old_path} -> {new_path}")
            self._save_processed_records()
    
    def on_moved(self, event):
        """当文件被移动或重命名时触发"""
        # 获取源路径和目标路径
        src_path = event.src_path
        dest_path = event.dest_path
        
        # 忽略目录事件
        if os.path.isdir(dest_path):
            return
            
        logging.info(f"文件移动/重命名: {os.path.basename(src_path)} -> {os.path.basename(dest_path)}")
        
        # 如果源文件在已处理列表中，需要更新记录
        if src_path in self.processed_files:
            self.processed_files.remove(src_path)
            logging.debug(f"从已处理列表中移除原文件: {src_path}")
        
        # 如果源文件在待处理列表中，需要取消定时器并移除
        if src_path in self.pending_files:
            self.pending_files[src_path].cancel()
            del self.pending_files[src_path]
            logging.debug(f"已取消源文件的待处理定时器: {src_path}")
        
        # 检查目标文件是否是需要处理的文件类型
        if self._is_audio_file(dest_path):
            # 更新处理器中的记录（如果适用）
            if hasattr(self.processor, '_update_processed_records_on_rename'):
                self.processor._update_processed_records_on_rename(src_path, dest_path)
                
            # 将目标文件当作新文件处理
            self._handle_file_event(dest_path)
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
                max_part_time: int = 20,
                include_timestamps: bool = True,
                max_retries: int = 3,
                export_srt: bool = False):
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
            export_srt: 是否导出SRT字幕文件
        """
        self.media_folder = media_folder
        self.output_folder = output_folder
        self.max_part_time= max_part_time
        self.temp_segments_dir = temp_segments_dir
        self.transcription_processor = transcription_processor
        self.audio_extractor = audio_extractor
        self.progress_callback = progress_callback
        self.process_video = process_video
        self.extract_audio_only = extract_audio_only
        self.format_text = format_text
        self.include_timestamps = include_timestamps
        self.max_retries = max_retries
        self.export_srt = export_srt
        self.processed_record_file = os.path.join(self.output_folder, "processed_audio_files.json")
        self.processed_audio = load_json_file(self.processed_record_file)
        self.interrupt_received = False
        # 创建输出目录
        os.makedirs(output_folder, exist_ok=True)
        
        # 设置支持的文件类型
        self.video_extensions = ['.mp4', '.mov', '.avi'] if process_video else []
        
        # 初始化文本处理器
        self.text_processor = TextProcessor(
            output_folder=output_folder,
            format_text=format_text,
            include_timestamps=include_timestamps,
            progress_callback=progress_callback,
            export_srt=export_srt  # 添加SRT导出选项
        )
        
    def set_interrupt_flag(self, value=True):
        """设置中断标志"""
        self.interrupt_received = value
        
        # 确保中断传递到转写处理器
        if hasattr(self, 'transcription_processor'):
            self.transcription_processor.set_interrupt_flag(value)
            
        # 停止当前所有处理
        if value and hasattr(self, 'worker_threads'):
            for thread in self.worker_threads:
                # 这只是一个标记，实际上需要线程自己检查标记并退出
                thread.interrupt = True
        
    def is_recognized_file(self, filepath: str) -> bool:
        """检查文件是否已处理过，基于文件名而非完整路径"""
        # 获取不含路径和扩展名的基本文件名
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        
        # 检查是否存在对应的输出文件
        output_path = os.path.join(self.output_folder, f"{base_name}.txt")
        if os.path.exists(output_path):
            return True
        
        # 检查处理记录中是否存在同名文件
        for processed_path in self.processed_audio.keys():
            processed_base_name = os.path.splitext(os.path.basename(processed_path))[0]
            # inculdes
            
            if base_name == processed_base_name:
                return True
        
        return False
        
    
    def process_file(self, filepath: str) -> bool:
        """
        处理单个文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            处理是否成功
        """
        filepath = self._normalize_filename(filepath)
        filename = os.path.basename(filepath)
        file_extension = os.path.splitext(filename)[1].lower()
        if(self.is_recognized_file(filepath)):
            logging.info(f"文件 {filename} 已处理，跳过: {filepath}")
            return True
        try:
            # 处理视频文件 - 需要先提取音频
            if file_extension in self.video_extensions:
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
    def _process_large_audio_file(self, audio_path: str, audio_duration: float) -> bool:
        """
        处理大音频文件，按part分段处理
        
        Args:
            audio_path: 音频文件路径
            audio_duration: 音频时长(秒)
            
        Returns:
            是否处理成功
        """
        from .part_manager import PartManager
        
        filename = os.path.basename(audio_path)
        logging.info(f"检测到大音频文件: {filename}，长度: {audio_duration/60:.1f}分钟，开始分part处理")
        
        # 创建Part管理器
        part_manager = PartManager(self.output_folder, self.max_part_time)
        
        # 获取part信息和待处理part
        file_record, pending_parts = part_manager.get_parts_for_audio(
            audio_path, audio_duration, self.processed_audio
        )
        
        # 如果所有part都已完成，创建索引文件并返回
        if not pending_parts:
            logging.info(f"音频 {filename} 所有part已处理完成")
            index_file = part_manager.create_index_file(audio_path, self.processed_audio)
            self._save_processed_records()
            
            return True
        
        # 分割音频为片段
        segment_files = self.audio_extractor.split_audio_file(audio_path)
        if not segment_files:
            logging.error(f"分割音频失败: {filename}")
            return False
        
        # 依次处理每个pending的part
        total_pending = len(pending_parts)
        for i, part_idx in enumerate(pending_parts):
            if self.interrupt_received:
                logging.warning(f"处理被中断，已完成 {i}/{total_pending} 个待处理part")
                break
                
            # 获取这个part的片段文件
            part_segments = part_manager.get_segments_for_part(
                part_idx, segment_files
            )
            
            logging.info(f"处理Part {part_idx+1}/{file_record['total_parts']}，" +
                    f"包含 {len(part_segments)} 个片段")
            
            # 显示进度
            if self.progress_callback:
                
                self.progress_callback(
                    i,
                    total_pending,
                    f"处理Part {part_idx+1}/{file_record['total_parts']}",
                )
            
            # 处理这个part的所有片段
            segment_results = self.transcription_processor.process_audio_segments(part_segments)
            # 记录 ASR 统计信息
            successful_segments = sum(1 for r in segment_results.values() if r is not None)
            part_key = str(part_idx)
            total_segments = len(part_segments)
            if part_key not in file_record["parts"]:
                file_record["parts"][part_key] = {}
            file_record["parts"][part_key]["segment_stats"] = {
                "successful": successful_segments,
                "total": total_segments
            }

            # 记录 ASR 模型信息
            if hasattr(self.transcription_processor, 'model_name'):
                file_record["asr_model"] = self.transcription_processor.model_name

            # 重试失败的片段
            if segment_results:
                segment_results = self.transcription_processor.retry_failed_segments(
                    part_segments, segment_results
                )
            
            # 准备part的文本内容
            start_time, end_time = part_manager.get_part_time_range(part_idx)
            part_metadata = {
                "原始文件": filename,
                "Part编号": f"{part_idx+1}/{file_record['total_parts']}",
                "时间范围": f"{start_time/60:.1f}-{min(end_time, audio_duration)/60:.1f}分钟",
                "处理时间": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            part_text = self.text_processor.prepare_result_text(
                segment_files=part_segments,
                segment_results=segment_results,
                metadata=part_metadata
            )
            
            # 保存part的文本
            if part_text:
                output_file = part_manager.save_part_text(
                    audio_path, part_idx, part_text, self.processed_audio
                )
                logging.info(f"Part {part_idx+1} 转写结果已保存: {output_file}")
                
                # 保存进度
                self._save_processed_records()
            else:
                logging.warning(f"Part {part_idx+1} 无有效转写结果")
        
        # 检查是否全部完成
        file_record = self.processed_audio.get(audio_path, {})
        if file_record.get("completed", False):
            # 创建索引文件
            index_file = part_manager.create_index_file(audio_path, self.processed_audio)
            logging.info(f"所有Part处理完成，创建索引文件: {index_file}")
            
        # 保存最终状态
        self._save_processed_records()
        return True
    
    def _cleanup_audio_file(self, audio_path: str):
        """
        清理处理完成后的音频文件
        
        Args:
            audio_path: 音频文件路径
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logging.info(f"删除音频文件: {audio_path}")
        except Exception as e:
            logging.warning(f"删除音频文件失败: {audio_path}, 错误: {str(e)}")

    def _process_audio_file(self, audio_path: str) -> bool:
        """处理音频文件"""
        filename = os.path.basename(audio_path)
        logging.info(f"处理音频文件: {filename}")
        
        # 获取音频时长
        audio_duration = get_audio_duration(audio_path)
        if audio_duration <= 0:
            logging.error(f"无法获取音频时长: {filename}")
            return False
            
        logging.info(f"音频时长: {audio_duration:.1f}秒")
        
        # 判断是否为大音频文件（超过20分钟）
        if audio_duration > self.max_part_time * 60:
            return self._process_large_audio_file(audio_path, audio_duration)
        
        
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
            
            # 准备文本内容和SRT分段数据
            result_text, srt_segments = self.text_processor.prepare_result_text(
                segment_files=segment_files,
                segment_results=segment_results,
                metadata=metadata
            )
            
            if not result_text:
                logging.warning(f"无有效转写结果: {filename}")
                return False
            
            # 保存文本文件和SRT字幕文件
            output_files = self.text_processor.save_result_text(
                text=result_text,
                filename=filename,
                metadata=metadata,
                srt_segments=srt_segments
            )
            
            txt_file = output_files.get("txt", "")
            srt_file = output_files.get("srt", "")
            
            if self.progress_callback:
                self.progress_callback(
                    1,
                    1,
                    f"文件生成完成: {os.path.basename(txt_file)}"
                )
                
            logging.info(f"转写结果已保存到: {txt_file}")
            if srt_file:
                logging.info(f"SRT字幕已保存到: {srt_file}")
            
            # 更新处理记录
            if audio_path not in self.processed_audio:
                self.processed_audio[audio_path] = {}
            self.processed_audio[audio_path]["last_processed_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 清理临时文件
            dest_audio_path = os.path.join(self.output_folder, os.path.basename(audio_path))
            self._cleanup_audio_file(audio_path)
            self._cleanup_audio_file(dest_audio_path)
            
            self._save_processed_records()
            return True
            
        except Exception as e:
            # track
            import traceback
            traceback.print_exc()
            logging.error(f"处理音频文件时出错 {filename}: {str(e)}")
            return False
    def _save_processed_records(self):
        """保存已处理的文件记录"""
        save_json_file(self.processed_record_file, self.processed_audio)
    def init_media_files(self):
        """初始化媒体文件夹"""

        pass
    def nomallize_audio_format(self, input_path: str, output_format: str = "mp3") -> str:
        """
        将音频文件转换为指定格式
        
        Args:
            input_path: 输入音频文件路径
            output_format: 目标音频格式，默认为mp3
            
        Returns:
            转换后的音频文件路径，失败则返回None
        """
        try:
            input_filename = os.path.basename(input_path)
            base_name = os.path.splitext(input_filename)[0]
            output_dir = os.path.dirname(input_path)
            output_path = os.path.join(output_dir, f"{base_name}.{output_format}")
            
            # 如果输出文件已存在，或者输入文件已经是目标格式，则直接返回
            if output_path == input_path or os.path.exists(output_path):
                logging.info(f"目标格式文件已存在: {output_path}")
                return output_path
                
            # 使用FFmpeg转换音频格式
            logging.info(f"正在将音频 {input_filename} 转换为 {output_format} 格式")
            
            # 根据不同格式设置FFmpeg参数
            if output_format == "mp3":
                quality_param = ['-q:a', '0']
            elif output_format == "wav":
                quality_param = ['-acodec', 'pcm_s16le']
            elif output_format == "m4a":
                quality_param = ['-c:a', 'aac', '-b:a', '192k']
            else:
                # 默认参数
                quality_param = ['-q:a', '0']
                
            cmd = [
                'ffmpeg', '-i', input_path,
                *quality_param, output_path,
                '-y'  # 覆盖已存在的文件
            ]
            
            # 执行命令
            subprocess.run(cmd, check=True, capture_output=True)
            
            if os.path.exists(output_path):
                logging.info(f"格式转换成功: {output_path}")
                os.remove(input_path)  # 删除原始文件
                logging.info(f"删除原始文件: {input_path}")
                return output_path
            else:
                logging.error(f"格式转换失败: {input_filename}")
                return None
                
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg处理失败: {e}")
            return None
        except Exception as e:
            logging.error(f"转换音频格式时发生错误: {str(e)}")
            return None
    def start_file_monitoring(self,additional_folders=None) -> 'Observer':
        """
        启动文件监控
        
        Returns:
            文件监控器实例
        """
        event_handler = AudioFileHandler(self)
        observer = Observer()
      # 监控主媒体文件夹
        observer.schedule(event_handler, self.media_folder, recursive=False)
        logging.info(f"开始监控目录: {self.media_folder}")
        additional_folders = additional_folders or self.output_folder
        # 监控额外的文件夹
        if additional_folders:
            if isinstance(additional_folders, str):
                additional_folders = [additional_folders]
                
            for folder in additional_folders:
                if os.path.isdir(folder):
                    observer.schedule(event_handler, folder, recursive=False)
                    logging.info(f"开始监控额外目录: {folder}")
                else:
                    logging.warning(f"额外目录不存在，跳过监控: {folder}")
        
        observer.start()
        return observer

    def _normalize_filename(self, filepath: str) -> str:
        """
        规范化文件名，移除可能导致路径问题的特殊字符
        
        Args:
            filepath: 原始文件路径
            
        Returns:
            规范化后的文件路径
        """
        dir_name = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        
        # 清理文件名：去除首尾空格
        cleaned_filename = filename.strip()
        
        # 如果文件名已更改，则重命名文件
        if cleaned_filename != filename:
            new_path = os.path.join(dir_name, cleaned_filename)
            try:
                os.rename(filepath, new_path)
                logging.info(f"规范化文件名: {filename} -> {cleaned_filename}")
                return new_path
            except Exception as e:
                logging.warning(f"规范化文件名失败: {str(e)}")
                return filepath
        return filepath