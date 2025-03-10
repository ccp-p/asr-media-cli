import argparse
import os
from typing import Dict, Any

from utils import LogConfig

def parse_args() -> Dict[str, Any]:
    """
    解析命令行参数
    
    Returns:
        包含解析后参数的字典
    """
    defaults = get_default_args()
    parser = argparse.ArgumentParser(
        description='将媒体文件(音频或视频)转为文本',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--media_folder', type=str, default=defaults['media_folder'],
                        help='媒体文件所在文件夹，支持音频和视频')
    parser.add_argument('--output_folder', type=str, default=defaults['output_folder'],
                        help='输出结果文件夹')
    parser.add_argument('--max_retries', type=int, default=defaults['max_retries'],
                        help='最大重试次数')
    parser.add_argument('--max_workers', type=int, default=defaults['max_workers'],
                        help='线程池工作线程数')
    parser.add_argument('--use_jianying_first', action='store_true', default=defaults['use_jianying_first'],
                        help='是否优先使用剪映ASR')
    parser.add_argument('--no_jianying_first', action='store_false', dest='use_jianying_first',
                        help='不优先使用剪映ASR')
    parser.add_argument('--use_kuaishou', action='store_true', default=defaults['use_kuaishou'],
                        help='是否使用快手ASR')
    parser.add_argument('--no_kuaishou', action='store_false', dest='use_kuaishou',
                        help='不使用快手ASR')
    parser.add_argument('--use_bcut', action='store_true', default=defaults['use_bcut'],
                        help='是否使用B站ASR')
    parser.add_argument('--no_bcut', action='store_false', dest='use_bcut',
                        help='不使用B站ASR')
    parser.add_argument('--format_text', action='store_true', default=defaults['format_text'],
                        help='是否格式化输出文本')
    parser.add_argument('--no_format', action='store_false', dest='format_text',
                        help='不格式化输出文本')
    parser.add_argument('--include_timestamps', action='store_true', default=defaults['include_timestamps'],
                        help='在格式化文本中包含时间戳')
    parser.add_argument('--no_timestamps', action='store_false', dest='include_timestamps',
                        help='不在格式化文本中包含时间戳')
    parser.add_argument('--show_progress', action='store_true', default=defaults['show_progress'],
                        help='显示进度条')
    parser.add_argument('--hide_progress', action='store_false', dest='show_progress',
                        help='不显示进度条')
    parser.add_argument('--process_video', action='store_true', default=defaults['process_video'],
                        help='处理视频文件')
    parser.add_argument('--ignore_video', action='store_false', dest='process_video',
                        help='忽略视频文件')
    parser.add_argument('--extract_audio_only', action='store_true', default=defaults['extract_audio_only'],
                        help='仅提取音频而不处理成文本')
    parser.add_argument('--video_extensions', nargs='+', default=defaults['video_extensions'],
                        help='要处理的视频文件扩展名列表，如 .mp4 .mov .avi')
    parser.add_argument('--log_mode', choices=['VERBOSE', 'NORMAL', 'QUIET'], default=defaults['log_mode'],
                        help='日志级别：VERBOSE(详细)、NORMAL(正常)、QUIET(静默)')
    
    args = parser.parse_args()
    return vars(args)  # 转换为字典

def get_default_args() -> Dict[str, Any]:
    """
    获取默认参数，用于非命令行调用
    
    Returns:
        包含默认参数的字典
    """
    return {
        'media_folder': './media',  # 更改为media_folder
        'output_folder': './output',
        'max_retries': 3,
        'max_workers': 4,
        'use_jianying_first': True,
        'use_kuaishou': True,
        'use_bcut': True,
        'format_text': True,
        'include_timestamps': True,
        'show_progress': True,
        'process_video': True,  # 新增：是否处理视频文件
        'video_extensions': ['.mp4', '.mov', '.avi'],  # 新增：视频文件扩展名
        'extract_audio_only': False,  # 新增：仅提取音频不进行识别
        'log_mode': LogConfig.NORMAL
    }
