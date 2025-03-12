import logging
from typing import Dict, Optional, Any

from .utils import ProgressBar

class ProgressManager:
    """管理多个进度条的帮助类"""
    
    def __init__(self, show_progress: bool = True):
        """
        初始化进度条管理器
        
        Args:
            show_progress: 是否显示进度条
        """
        self.show_progress = show_progress
        self.progress_bars: Dict[str, ProgressBar] = {}
    
    def create_progress_bar(self, name: str, total: int, prefix: str, suffix: str = "") -> Optional[ProgressBar]:
        """
        创建并存储一个进度条
        
        Args:
            name: 进度条名称，用于后续引用
            total: 总步数
            prefix: 进度条前缀
            suffix: 进度条后缀
            
        Returns:
            创建的进度条，如果show_progress为False则返回None
        """
        if not self.show_progress:
            return None
            
        progress_bar = ProgressBar(total=total, prefix=prefix, suffix=suffix)
        self.progress_bars[name] = progress_bar
        return progress_bar
    
    def update_progress(self, name: str, current: Optional[int] = None, suffix: Optional[str] = None) -> None:
        """
        更新指定进度条
        
        Args:
            name: 进度条名称
            current: 当前进度
            suffix: 新的后缀文本
        """
        if not self.show_progress or name not in self.progress_bars:
            return
            
        self.progress_bars[name].update(current, suffix)
    
    def finish_progress(self, name: str, suffix: Optional[str] = None) -> None:
        """
        完成指定进度条
        
        Args:
            name: 进度条名称
            suffix: 完成时的后缀文本
        """
        if not self.show_progress or name not in self.progress_bars:
            return
            
        self.progress_bars[name].finish(suffix)
        del self.progress_bars[name]
    
    def close_all_progress_bars(self, suffix: str = "已终止") -> None:
        """
        关闭所有未完成的进度条
        
        Args:
            suffix: 关闭时显示的后缀文本
        """
        if not self.show_progress:
            return
            
        logging.info(f"关闭 {len(self.progress_bars)} 个未完成的进度条...")
        for name, bar in list(self.progress_bars.items()):
            try:
                self.finish_progress(name, suffix)
            except Exception as e:
                logging.warning(f"关闭进度条 '{name}' 时出错: {str(e)}")
