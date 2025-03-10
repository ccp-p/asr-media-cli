import os
import logging
import traceback

# 导入工具函数
from utils import LogConfig, setup_logging

# 导入AudioProcessor模块和命令行参数处理
from audio_processor import AudioProcessor
from cli import parse_args, get_default_args

def process_media_to_txt(**kwargs) -> None:
    """
    批量将媒体文件(MP3音频或视频)转为文本，使用ASR服务轮询
    
    Args:
        **kwargs: 参数字典，包含以下内容:
            media_folder: 媒体文件所在文件夹(可以包含MP3或视频文件)
            output_folder: 输出结果文件夹
            max_retries: 最大重试次数
            max_workers: 线程池工作线程数
            use_jianying_first: 是否优先使用剪映ASR
            use_kuaishou: 是否使用快手ASR
            use_bcut: 是否使用B站ASR
            format_text: 是否格式化输出文本以提高可读性
            include_timestamps: 是否在格式化文本中包含时间戳
            show_progress: 是否显示进度条
            process_video: 是否处理视频文件
            video_extensions: 要处理的视频文件扩展名列表，默认为['.mp4', '.mov', '.avi']
            extract_audio_only: 是否仅提取音频而不处理成文本
            log_mode: 日志级别 (VERBOSE/NORMAL/QUIET)
    """
    # 设置代理(如需要)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
    
    # 提取并移除日志模式参数
    log_mode = kwargs.pop('log_mode', LogConfig.NORMAL)
    
    # 设置日志级别
    setup_logging(level=logging.INFO, log_mode=log_mode)
    
    # 创建并运行媒体处理器
    processor = AudioProcessor(**kwargs)
    processor.process_all_files()


if __name__ == "__main__":
    # 添加异常处理
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 调用处理函数
        process_media_to_txt(**args)
        
    except KeyboardInterrupt:
        logging.warning("\n程序已被用户中断")
    except Exception as e:
        logging.error(f"\n程序执行出错: {str(e)}")
        traceback.print_exc()
    finally:
        logging.info("\n程序执行完毕。")
