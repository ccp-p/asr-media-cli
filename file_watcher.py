import os
import time
import logging
import traceback
from queue import Queue
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AudioFileHandler(FileSystemEventHandler):
    """音频文件监控处理器"""
    
    def __init__(self, processor, extensions=None):
        """
        初始化文件处理器
        
        Args:
            processor: AudioProcessor实例，用于处理音频文件
            extensions: 要监听的文件扩展名列表，默认为常见音频格式
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
        
def start_file_watcher(processor, watch_folder):
    """
    启动文件监控
    
    Args:
        processor: AudioProcessor实例
        watch_folder: 要监控的文件夹路径
    
    Returns:
        observer: 启动的Observer实例，可用于停止监控
    """
    # 确保输出目录存在
    os.makedirs(processor.output_folder, exist_ok=True)
    
    # 处理已有文件
    processor.process_all_files()
    
    # 设置事件处理器
    event_handler = AudioFileHandler(processor)
    
    # 创建并启动观察者
    observer = Observer()
    observer.schedule(event_handler, watch_folder, recursive=True)
    observer.start()
    
    logging.info(f"已启动文件监控: {watch_folder}")
    print(f"\n监控已启动，正在监视文件夹: {watch_folder}")
    print("按 Ctrl+C 停止监控...\n")
    
    return observer
