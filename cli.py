import argparse
import os
from typing import Dict, Any

def parse_args() -> Dict[str, Any]:
    """
    解析命令行参数
    
    Returns:
        包含解析后参数的字典
    """
    parser = argparse.ArgumentParser(
        description='批量将MP3音频转换为文本文件',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # 必需参数
    parser.add_argument(
        '-i', '--input_folder', 
        type=str, 
        required=True,
        help='输入MP3文件所在文件夹路径'
    )
    
    parser.add_argument(
        '-o', '--output_folder', 
        type=str, 
        required=True,
        help='文本输出文件夹路径'
    )
    
    # 可选参数 - 性能设置
    performance_group = parser.add_argument_group('性能设置')
    performance_group.add_argument(
        '--max_workers', 
        type=int, 
        default=os.cpu_count() or 4,
        help='并行处理的线程数'
    )
    
    performance_group.add_argument(
        '--max_retries', 
        type=int, 
        default=3,
        help='识别失败时的最大重试次数'
    )
    
    # 可选参数 - ASR服务设置
    asr_group = parser.add_argument_group('ASR服务设置')
    asr_group.add_argument(
        '--use_jianying_first', 
        action='store_true',
        help='优先使用剪映ASR服务'
    )
    
    asr_group.add_argument(
        '--use_kuaishou', 
        action='store_true',
        help='启用快手ASR服务'
    )
    
    asr_group.add_argument(
        '--use_bcut', 
        action='store_true',
        help='启用必剪(B站)ASR服务'
    )
    
    # 可选参数 - 输出格式设置
    output_group = parser.add_argument_group('输出格式设置')
    output_group.add_argument(
        '--no_format_text', 
        action='store_true',
        help='不格式化输出文本'
    )
    
    output_group.add_argument(
        '--no_timestamps', 
        action='store_true',
        help='不在文本中包含时间戳'
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 转换为字典并进行必要的转换
    args_dict = vars(args)
    
    # 处理反向参数（--no_xxx 转为 xxx=False）
    args_dict['format_text'] = not args_dict.pop('no_format_text')
    args_dict['include_timestamps'] = not args_dict.pop('no_timestamps')
    
    # 重命名参数以符合函数命名
    args_dict['mp3_folder'] = args_dict.pop('input_folder')
    
    return args_dict

def get_default_args() -> Dict[str, Any]:
    """
    获取默认参数，用于非命令行调用
    
    Returns:
        包含默认参数的字典
    """
    return {
        'mp3_folder': r"D:\download",
        'output_folder': r"D:\download\dest",
        'max_retries': 3,
        'max_workers': 6,
        'use_jianying_first': True,
        'use_kuaishou': True,
        'use_bcut': True,
        'format_text': True,
        'include_timestamps': True
    }
