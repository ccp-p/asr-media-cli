import logging
import threading
from typing import Dict, Any, Set, Callable, List, Optional

class TaskManager:
    """任务管理器，管理所有正在运行的任务和线程"""
    
    def __init__(self):
        self.running_tasks: Dict[str, Any] = {}
        self.task_lock = threading.Lock()
        self.interrupt_requested = False
    
    def register_task(self, task_id: str, task_obj: Any) -> None:
        """
        注册一个任务
        
        Args:
            task_id: 任务ID
            task_obj: 任务对象，应该有stop、cancel或terminate方法
        """
        with self.task_lock:
            self.running_tasks[task_id] = task_obj
    
    def unregister_task(self, task_id: str) -> None:
        """
        注销一个任务
        
        Args:
            task_id: 任务ID
        """
        with self.task_lock:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def interrupt_all_tasks(self) -> None:
        """中断所有正在运行的任务"""
        self.interrupt_requested = True
        logging.warning("正在中断所有任务...")
        
        with self.task_lock:
            for task_id, task_obj in list(self.running_tasks.items()):
                self._stop_task(task_id, task_obj)
    
    def _stop_task(self, task_id: str, task_obj: Any) -> None:
        """
        尝试停止一个任务
        
        Args:
            task_id: 任务ID
            task_obj: 任务对象
        """
        try:
            # 尝试各种可能的停止方法
            if hasattr(task_obj, 'set_interrupt_flag'):
                task_obj.set_interrupt_flag(True)
            elif hasattr(task_obj, 'stop'):
                task_obj.stop()
            elif hasattr(task_obj, 'cancel'):
                task_obj.cancel()
            elif hasattr(task_obj, 'terminate'):
                task_obj.terminate()
            elif hasattr(task_obj, 'close'):
                task_obj.close()
            
            logging.debug(f"已停止任务: {task_id}")
        except Exception as e:
            logging.error(f"停止任务 {task_id} 时出错: {str(e)}")