import logging
from typing import Dict, Any
import json
import os

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

def setup_logging(level=logging.INFO):
    """设置日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
