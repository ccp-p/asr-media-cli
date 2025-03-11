import logging
from typing import Dict, Any, Optional, Callable, List
import json
import os
import sys
import time
from datetime import datetime

def format_time_duration(seconds: float) -> str:
    """
    将秒数格式化为更易读的时间格式 (HH:MM:SS)
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串 (HH:MM:SS)
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    加载JSON文件，处理异常
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        解析后的JSON对象，失败则返回空字典
    """
    if not os.path.exists(file_path):
        return {}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.warning(f"读取记录文件 {file_path} 出错。创建新记录。")
        return {}
    except Exception as e:
        logging.error(f"加载JSON文件出错: {str(e)}")
        return {}

def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        file_path: JSON文件路径
        data: 要保存的数据
        
    Returns:
        是否保存成功
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"保存JSON文件出错: {str(e)}")
        return False

class LogConfig:
    """日志配置管理类"""
    
    # 日志级别
    VERBOSE = 1  # 详细模式 - 显示所有日志
    NORMAL = 2   # 正常模式 - 显示信息、警告和错误
    QUIET = 3    # 静默模式 - 只显示警告和错误
    
    # 当前日志级别
    _current_level = NORMAL
    
    # 原始日志级别
    _original_log_level = logging.INFO
    
    @classmethod
    def setup_logging(cls, level=logging.INFO, log_mode=NORMAL):
        """
        设置日志配置
        
        Args:
            level: 基础日志级别
            log_mode: 日志模式 (VERBOSE/NORMAL/QUIET)
        """
        cls._original_log_level = level
        cls._current_level = log_mode
        
        # 配置根日志记录器
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 根据模式调整日志过滤
        if log_mode == cls.QUIET:
            # 静默模式 - 只显示警告和错误
            logging.getLogger().setLevel(logging.WARNING)
        elif log_mode == cls.NORMAL:
            # 正常模式 - 使用默认级别
            pass
        elif log_mode == cls.VERBOSE:
            # 详细模式 - 显示所有日志，包括DEBUG
            logging.getLogger().setLevel(logging.DEBUG)
    
    @classmethod
    def get_log_mode(cls) -> int:
        """获取当前日志模式"""
        return cls._current_level
    
    @classmethod
    def set_log_mode(cls, mode: int):
        """
        设置日志模式
        
        Args:
            mode: 日志模式 (VERBOSE/NORMAL/QUIET)
        """
        cls._current_level = mode
        
        if mode == cls.QUIET:
            # 静默模式 - 只显示警告和错误
            logging.getLogger().setLevel(logging.WARNING)
        elif mode == cls.NORMAL:
            # 正常模式 - 使用默认级别
            logging.getLogger().setLevel(cls._original_log_level)
        elif mode == cls.VERBOSE:
            # 详细模式 - 显示所有日志，包括DEBUG
            logging.getLogger().setLevel(logging.DEBUG)

class ProgressBar:
    """进度条实现，支持命令行交互式显示"""
    
    def __init__(self, total: int, prefix: str = "", suffix: str = "", 
                 length: int = 30, fill: str = "█", print_end: str = "\r"):
        """
        初始化进度条
        
        Args:
            total: 总步数
            prefix: 进度条前缀文本
            suffix: 进度条后缀文本
            length: 进度条字符长度
            fill: 进度条填充字符
            print_end: 打印结束符
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.fill = fill
        self.print_end = print_end
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = 0
        self.is_finished = False
        
        # 确保至少更新一次
        self._update_progress_bar()
    
    def update(self, current: Optional[int] = None, suffix: Optional[str] = None):
        """
        更新进度条
        
        Args:
            current: 当前步数
            suffix: 新的后缀文本
        """
        if current is not None:
            self.current = current
        else:
            self.current += 1
            
        if suffix is not None:
            self.suffix = suffix
            
        # 限制更新频率，避免过多IO
        current_time = time.time()
        if current_time - self.last_update_time > 0.1 or self.current >= self.total:
            self._update_progress_bar()
            self.last_update_time = current_time
    
    def finish(self, suffix: Optional[str] = None):
        """
        完成进度条
        
        Args:
            suffix: 最终后缀文本
        """
        if suffix is not None:
            self.suffix = suffix
        
        self.current = self.total
        self._update_progress_bar()
        print()  # 最后换行
        self.is_finished = True
    
    def _update_progress_bar(self):
        """更新并打印进度条"""
        percent = min(100.0, self.current * 100 / self.total)
        filled_length = int(self.length * self.current // self.total)
        bar = self.fill * filled_length + '-' * (self.length - filled_length)
        
        # 计算剩余时间估计
        elapsed_time = time.time() - self.start_time
        if self.current > 0:
            eta = elapsed_time * (self.total - self.current) / self.current
            time_info = f" | ETA: {format_time_duration(eta)}"
        else:
            time_info = ""
            
        # 打印进度条
        print(f"\r{self.prefix} |{bar}| {percent:.1f}% | {self.current}/{self.total}{time_info} | {self.suffix}", 
              end=self.print_end)
        sys.stdout.flush()
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        将字节大小格式化为人类可读格式
        
        Args:
            size_bytes: 字节数
            
        Returns:
            格式化的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

# 为方便导入，保留原始函数名
def setup_logging(level=logging.INFO, log_mode=LogConfig.NORMAL):
    """
    设置日志配置的简便函数
    
    Args:
        level: 基础日志级别
        log_mode: 日志模式 (VERBOSE/NORMAL/QUIET)
    """
    LogConfig.setup_logging(level, log_mode)
