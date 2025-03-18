"""
进度管理器模块
负责管理和显示进度条
"""
import os
import logging
from typing import Dict, Optional
from tqdm import tqdm

class ProgressBar:
    """进度条封装类"""
    
    def __init__(self, total: int, description: str, unit: str = "", show_progress: bool = True):
        """
        初始化进度条
        
        Args:
            total: 总数量
            description: 进度条描述
            unit: 单位
            show_progress: 是否显示进度条
        """
        self.total = total
        self.current = 0
        self.show_progress = show_progress
        self.description = description
        
        if show_progress:
            self.pbar = tqdm(
                total=total,
                desc=description,
                unit=unit,
                ncols=100,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )
        else:
            self.pbar = None
    
    def update(self, n: int = 1):
        """更新进度"""
        if n < 0:
            logging.warning(f"进度更新值不能为负数: {n}")
            return
            
        if self.current + n > self.total:
            logging.warning(f"进度超出总量: current={self.current}, update={n}, total={self.total}")
            n = self.total - self.current
        
        if n > 0:  # 只有在有实际增量时才更新
            self.current += n
            if self.pbar:
                self.pbar.update(n)
    
    def set_description(self, desc: str, refresh: bool = True):
        """
        设置描述
        
        Args:
            desc: 新的描述文本
            refresh: 是否立即刷新显示
        """
        self.description = desc
        if self.pbar:
            self.pbar.set_description_str(desc, refresh=refresh)
    
    def set_postfix(self, state: Optional[str] = None, refresh: bool = True):
        """
        设置后缀状态
        
        Args:
            state: 状态文本
            refresh: 是否立即刷新显示
        """
        if self.pbar and state:
            self.pbar.set_postfix_str(state, refresh=refresh)
    
    def close(self, final_message: Optional[str] = None):
        """
        关闭进度条
        
        Args:
            final_message: 最终显示的消息
        """
        if self.pbar:
            if final_message:
                self.set_description(final_message)
            self.pbar.close()
            self.pbar = None
    
    def reset(self, total: Optional[int] = None, description: Optional[str] = None):
        """
        重置进度条
        
        Args:
            total: 新的总量
            description: 新的描述
        """
        if total is not None:
            self.total = total
        if description is not None:
            self.description = description
            
        self.current = 0
        if self.pbar:
            self.pbar.reset(total=self.total)
            if description:
                self.set_description(description)

class ProgressManager:
    """进度管理器，管理多个进度条"""
    
    def __init__(self, show_progress: bool = True):
        """
        初始化进度管理器
        
        Args:
            show_progress: 是否显示进度条
        """
        self.show_progress = show_progress
        self.progress_bars: Dict[str, ProgressBar] = {}
        
    def create_progress_bar(self, 
                          name: str, 
                          total: int, 
                          prefix: str, 
                          suffix: str = "",
                          unit: str = "") -> Optional[ProgressBar]:
        """
        创建并存储一个进度条
        
        Args:
            name: 进度条名称
            total: 总数量
            prefix: 前缀描述
            suffix: 后缀描述
            unit: 单位
            
        Returns:
            创建的进度条对象
        """
        description = f"{prefix}"
        if suffix:
            description = f"{prefix} - {suffix}"
            
        progress_bar = ProgressBar(
            total=total,
            description=description,
            unit=unit,
            show_progress=self.show_progress
        )
        
        self.progress_bars[name] = progress_bar
        return progress_bar
    
    def update_progress(self, 
                       name: str, 
                       current: Optional[int] = None, 
                       message: Optional[str] = None,
                       state: Optional[str] = None):
        """
        更新指定进度条
        
        Args:
            name: 进度条名称
            current: 当前进度值
            message: 更新的描述信息
            state: 状态文本
        """
        if name not in self.progress_bars:
            return
            
        progress_bar = self.progress_bars[name]
        
        if current < 0:
            logging.warning(f"进度值不能为负数: {current}")
        elif current > progress_bar.total:
            logging.warning(f"进度值超出总量: current={current}, total={progress_bar.total}")
            # 设置到最大值
            if progress_bar.current != progress_bar.total:
                # 计算需要更新的增量
                progress_bar.update(progress_bar.total - progress_bar.current)
        else:
            # 处理进度回退情况
            if current < progress_bar.current:
                # 需要重置进度条
                logging.debug(f"进度条回退: current={progress_bar.current}, new={current}")
                progress_bar.reset(total=progress_bar.total)
                progress_bar.update(current)
            else:
                # 正常增量更新
                progress = current - progress_bar.current
                if progress > 0:  # 仍然需要确认增量为正
                    progress_bar.update(progress)
        
        if message is not None:  # Changed from 'if message:' to handle empty strings properly
            description = f"{progress_bar.description.split(' - ')[0]}"
            description = f"{description} - {message}"
            progress_bar.set_description(description, refresh=False)
            
        if state:
            progress_bar.set_postfix(state, refresh=True)
    
    def finish_progress(self, name: str, suffix: Optional[str] = None):
        """
        完成指定进度条
        
        Args:
            name: 进度条名称
            suffix: 结束时的后缀描述
        """
        if name in self.progress_bars:
            progress_bar = self.progress_bars[name]
            # 确保进度到达100%
            if progress_bar.current < progress_bar.total:
                progress_bar.update(progress_bar.total - progress_bar.current)
            # 更新最终描述
            if suffix:
                description = f"{progress_bar.description.split(' - ')[0]} - {suffix}"
                progress_bar.set_description(description, refresh=True)
            # 关闭进度条
            progress_bar.close()
            # 从管理器中移除
            del self.progress_bars[name]
    
    def has_progress_bar(self, name: str) -> bool:
        """
        检查是否存在指定名称的进度条
        
        Args:
            name: 进度条名称
            
        Returns:
            是否存在
        """
        return name in self.progress_bars
    
    def close_all_progress_bars(self, final_message: Optional[str] = None):
        """
        关闭所有进度条
        
        Args:
            final_message: 结束时显示的消息
        """
        for name in list(self.progress_bars.keys()):
            self.finish_progress(name, final_message)
        self.progress_bars.clear()
    def get_progress_bar(self, name: str) -> Optional[ProgressBar]:
        """
        获取指定名称的进度条
        
        Args:
            name: 进度条名称
            
        Returns:
            进度条对象
        """
        return self.progress_bars.get(name)
    