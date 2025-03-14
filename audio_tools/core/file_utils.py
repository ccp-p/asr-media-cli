"""
文件处理相关的工具函数
"""
import os
import json
import logging
import subprocess
from typing import Any, Dict, Optional
from pathlib import Path

def setup_logging(log_file: Optional[str] = None) -> None:
    """配置日志系统"""
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def check_ffmpeg_available() -> bool:
    """检查是否安装了FFmpeg"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def load_json_file(filepath: str, default: Any = None) -> Any:
    """
    加载JSON文件
    
    Args:
        filepath: JSON文件路径
        default: 如果文件不存在或读取失败时返回的默认值
        
    Returns:
        解析后的JSON数据或默认值
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"读取JSON文件失败 {filepath}: {str(e)}")
    return default if default is not None else {}

def save_json_file(filepath: str, data: Any) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        filepath: 保存路径
        data: 要保存的数据
        
    Returns:
        是否保存成功
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存JSON文件失败 {filepath}: {str(e)}")
        return False

def format_time_duration(seconds: float) -> str:
    """
    格式化时间长度为易读格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时间字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"