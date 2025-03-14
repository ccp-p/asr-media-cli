"""
错误处理模块
提供统一的错误处理和恢复机制
"""
import os
import time
import logging
import traceback
from typing import Optional, Callable, Any, Dict, List
from functools import wraps

class AudioToolsError(Exception):
    """音频工具基础异常类"""
    pass

class AudioProcessError(AudioToolsError):
    """音频处理错误"""
    pass

class VideoProcessError(AudioToolsError):
    """视频处理错误"""
    pass

class TranscriptionError(AudioToolsError):
    """转写错误"""
    pass

class RetryableError(AudioToolsError):
    """可重试的错误"""
    pass

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化错误处理器
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间(秒)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._error_stats: Dict[str, Dict[str, int]] = {}
    
    def retry(self, func: Callable, *args, error_msg: str = "", **kwargs) -> Any:
        """
        执行可重试的操作
        
        Args:
            func: 要执行的函数
            error_msg: 错误消息前缀
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            AudioToolsError: 如果重试次数用尽仍然失败
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                self._update_error_stats(func.__name__, str(e))
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logging.warning(f"{error_msg} - 第{attempt+1}次重试失败: {str(e)}")
                    logging.warning(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    break
        
        error_msg = error_msg or f"执行 {func.__name__} 失败"
        raise AudioToolsError(f"{error_msg}: {str(last_error)}")
    
    def safe_execute(self, 
                    func: Callable, 
                    *args,
                    error_msg: str = "",
                    cleanup_func: Optional[Callable] = None,
                    **kwargs) -> Any:
        """
        安全执行操作
        
        Args:
            func: 要执行的函数
            error_msg: 错误消息前缀
            cleanup_func: 清理函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            AudioToolsError: 如果执行失败
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self._update_error_stats(func.__name__, str(e))
            error_msg = error_msg or f"执行 {func.__name__} 失败"
            
            # 执行清理函数
            if cleanup_func:
                try:
                    cleanup_func()
                except Exception as cleanup_error:
                    logging.error(f"清理过程出错: {str(cleanup_error)}")
            
            # 记录详细错误信息
            logging.error(f"{error_msg}: {str(e)}")
            logging.debug(f"错误详情:\n{traceback.format_exc()}")
            
            raise AudioToolsError(f"{error_msg}: {str(e)}")
    
    def with_retry(self, max_retries: Optional[int] = None, error_msg: str = ""):
        """
        重试装饰器
        
        Args:
            max_retries: 最大重试次数，如果不指定则使用默认值
            error_msg: 错误消息前缀
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.retry(
                    func,
                    *args,
                    error_msg=error_msg or f"执行 {func.__name__} 失败",
                    max_retries=max_retries or self.max_retries,
                    **kwargs
                )
            return wrapper
        return decorator
    
    def _update_error_stats(self, operation: str, error: str):
        """
        更新错误统计
        
        Args:
            operation: 操作名称
            error: 错误信息
        """
        if operation not in self._error_stats:
            self._error_stats[operation] = {}
        
        if error not in self._error_stats[operation]:
            self._error_stats[operation][error] = 0
            
        self._error_stats[operation][error] += 1
    
    def get_error_stats(self) -> Dict[str, Dict[str, int]]:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        return self._error_stats.copy()
    
    def print_error_stats(self):
        """打印错误统计信息"""
        if not self._error_stats:
            logging.info("没有错误记录")
            return
            
        logging.info("\n错误统计:")
        for operation, errors in self._error_stats.items():
            logging.info(f"\n操作: {operation}")
            for error, count in errors.items():
                logging.info(f"  - {error}: {count}次")