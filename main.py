import os
import sys
import logging
import traceback
import time

def check_dependencies():
    """检查所需依赖是否已安装"""
    required_modules = {
        'tqdm': '进度条显示',
        'requests': '网络请求',
        'pydub': '音频处理',
        'watchdog': '文件监控',
    }
    
    missing_modules = []
    
    for module, description in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing_modules.append((module, description))
    
    if (missing_modules):
        print("\n缺少必要的依赖模块:")
        for module, description in missing_modules:
            print(f"  - {module}: {description}")
        
        print("\n请使用以下命令安装所需依赖:")
        print("pip install -r requirements.txt")
        print("\n或者手动安装缺失的模块:")
        for module, _ in missing_modules:
            print(f"pip install {module}")
        
        print("\n程序将继续尝试运行，但可能功能受限...\n")
    
    # 检查FFmpeg是否可用
    try:
        from core import check_ffmpeg_available
        if not check_ffmpeg_available():
            print("\n警告: 未检测到FFmpeg，转换TS格式视频需要FFmpeg支持")
            print("请安装FFmpeg: https://ffmpeg.org/download.html")
            print("安装后确保将FFmpeg添加到系统PATH中\n")
    except ImportError:
        pass

# 从core包导入所需功能
from core import setup_logging, AudioProcessor, process_media_file, start_file_watcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置代理(如需要)
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

def convert_media_to_txt(media_folder: str, output_folder: str, max_retries: int = 3, 
                     max_workers: int = 4, use_jianying_first: bool = False, 
                     use_kuaishou: bool = False, use_bcut: bool = False,
                     format_text: bool = True, include_timestamps: bool = True,
                     watch_mode: bool = False, segments_per_part: int = 30) -> None:
    """
    批量将媒体文件(MP3、TS、MP4等)转为文本，使用ASR服务轮询
    
    Args:
        media_folder: 媒体文件所在文件夹
        output_folder: 输出结果文件夹
        max_retries: 最大重试次数
        max_workers: 线程池工作线程数
        use_jianying_first: 是否优先使用剪映ASR
        use_kuaishou: 是否使用快手ASR
        use_bcut: 是否使用B站ASR
        format_text: 是否格式化输出文本以提高可读性
        include_timestamps: 是否在格式化文本中包含时间戳
        watch_mode: 是否启用监听模式，监控文件夹变动
        segments_per_part: 每个部分包含多少个30秒片段，默认30个(15分钟)
    """
    # 创建处理器
    processor = AudioProcessor(
        media_folder=media_folder,
        output_folder=output_folder,
        max_retries=max_retries,
        max_workers=max_workers,
        use_jianying_first=use_jianying_first,
        use_kuaishou=use_kuaishou,
        use_bcut=use_bcut,
        format_text=format_text,
        include_timestamps=include_timestamps,
        segments_per_part=segments_per_part  # 添加片段分组参数
    )
    
    # 为AudioProcessor添加媒体文件预处理功能
    # 这将处理TS和其他视频文件，转换为MP3
    processor.preprocess_media = process_media_file
    
    # 确保输出目录存在
    os.makedirs(output_folder, exist_ok=True)
    
    if watch_mode:
        try:
            # 记录开始监听时间
            watch_start_time = time.time()
            processed_files_count = 0
            
            # 如果启用监听模式，导入并使用file_watcher模块
            observer = start_file_watcher(processor, media_folder)
            
            # 保持程序运行，直到用户中断
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                observer.join()
                print("\n文件监控已停止")
                
                # 计算监听总时长
                total_duration = time.time() - watch_start_time
                
                # 打印ASR服务使用统计信息
                logging.info("\n监听模式结束，显示ASR服务使用统计:")
                processor.print_statistics(processed_files_count, total_duration)
                
        except ImportError:
            logging.error("无法导入file_watcher模块，请确保watchdog库已安装")
            print("监控模式需要watchdog库支持，请运行: pip install watchdog")
            # 降级为正常处理模式
            processor.process_all_files()
    else:
        # 常规模式，处理所有文件
        processor.process_all_files()


if __name__ == "__main__":
    try:
        # 检查依赖
        check_dependencies()
        
        # 修改这几个路径即可
        convert_media_to_txt(  
            media_folder = r"D:\download",
            output_folder = r"D:\download\dest",
            max_retries = 3,
            max_workers = 6,
            use_jianying_first = True,
            use_kuaishou = True,
            use_bcut = True,
            format_text = True,
            include_timestamps = True,
            watch_mode = True,
            segments_per_part = 50  # 30个30秒片段 = 15分钟
        )
    except KeyboardInterrupt:
        logging.warning("\n程序已被用户中断")
    except Exception as e:
        logging.error(f"\n程序执行出错: {str(e)}")
        traceback.print_exc()
    finally:
        logging.info("\n程序执行完毕。")