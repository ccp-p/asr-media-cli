import os
import logging
import time
import shutil
from threading import Thread, Timer
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DestFolderHandler(FileSystemEventHandler):
    """
    专门处理 download/dest 目录的文件处理器
    将检测到的媒体文件移动到指定的目标目录
    """
    
    def __init__(self, target_folder, file_extensions=None, debounce_seconds=5):
        """
        初始化处理器
        
        Args:
            target_folder: 文件移动的目标文件夹
            file_extensions: 要处理的文件扩展名列表
            debounce_seconds: 防抖延迟时间(秒)
        """
        super().__init__()
        self.target_folder = target_folder
        self.file_extensions = file_extensions or ['.mp4', '.mp3', '.wav', '.m4a']
        self.pending_files = {}  # 等待处理的文件及其定时器
        self.processed_files = set()  # 已处理的文件
        self.debounce_seconds = debounce_seconds
        self.processing_queue = Queue()
        self._start_worker_thread()
        
        # 确保目标文件夹存在
        os.makedirs(target_folder, exist_ok=True)
    
    def on_created(self, event):
        """当文件被创建时触发"""
        self._handle_file_event(event.src_path)
        
    def on_modified(self, event):
        """当文件被修改时触发"""
        self._handle_file_event(event.src_path)
    
    def _is_target_file(self, filepath):
        """检查文件是否是要处理的类型"""
        if not os.path.isfile(filepath):
            return False
            
        _, ext = os.path.splitext(filepath)
        return ext.lower() in self.file_extensions
    
    def _handle_file_event(self, filepath):
        """处理文件事件的统一入口，使用防抖动技术"""
        # 如果不是目标文件或已在处理队列中，则跳过
        if not self._is_target_file(filepath) or filepath in self.processed_files:
            return
        
        # 取消之前为此文件设置的任何待处理定时器
        if filepath in self.pending_files:
            self.pending_files[filepath].cancel()
        
        # 设置新的定时器
        timer = Timer(
            self.debounce_seconds, 
            self._add_to_processing_queue, 
            args=[filepath]
        )
        timer.daemon = True
        self.pending_files[filepath] = timer
        timer.start()
        
        logging.debug(f"检测到文件: {filepath}，设置处理延时")
    
    def _add_to_processing_queue(self, filepath):
        """将文件添加到处理队列"""
        # 检查文件是否仍然存在
        if not os.path.exists(filepath):
            return
        
        # 从待处理列表中移除
        if filepath in self.pending_files:
            del self.pending_files[filepath]
        
        # 检查文件是否已在已处理列表中
        if filepath in self.processed_files:
            return
        
        # 添加到已处理列表
        self.processed_files.add(filepath)
        
        logging.info(f"添加文件到移动队列: {filepath}")
        self.processing_queue.put(filepath)
    
    def _start_worker_thread(self):
        """启动工作线程处理文件队列"""
        def worker():
            while True:
                try:
                    filepath = self.processing_queue.get()
                    self._move_file(filepath)
                    self.processing_queue.task_done()
                except Exception as e:
                    logging.error(f"处理文件时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        # 创建并启动工作线程
        thread = Thread(target=worker, daemon=True)
        thread.start()
    
    def _move_file(self, source_path):
        """将文件移动到目标文件夹"""
        try:
            filename = os.path.basename(source_path)
            target_path = os.path.join(self.target_folder, filename)
            
            # 如果目标文件已存在，添加时间戳
            if os.path.exists(target_path):
                name, ext = os.path.splitext(filename)
                timestamp = time.strftime("%Y%m%d%H%M%S")
                new_filename = f"{name}_{timestamp}{ext}"
                target_path = os.path.join(self.target_folder, new_filename)
            
            # 移动文件
            shutil.move(source_path, target_path)
            logging.info(f"文件已移动: {source_path} -> {target_path}")
            
            return target_path
        except Exception as e:
            logging.error(f"移动文件失败 {source_path}: {str(e)}")
            return None

def start_dest_folder_monitoring(dest_folder, target_folder):
    """
    启动对指定目录的监控，将检测到的文件移动到目标目录
    
    Args:
        dest_folder: 要监控的源文件夹
        target_folder: 文件移动的目标文件夹
        
    Returns:
        观察者实例
    """
    # 确保目录存在
    os.makedirs(dest_folder, exist_ok=True)
    os.makedirs(target_folder, exist_ok=True)
    
    handler = DestFolderHandler(target_folder)
    observer = Observer()
    observer.schedule(handler, dest_folder, recursive=False)
    observer.start()
    
    logging.info(f"开始监控目录: {dest_folder} -> {target_folder}")
    return observer