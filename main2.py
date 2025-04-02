import os
import logging
import sys

from tqdm import tqdm
from audio_tools.core.audio_extractor import AudioExtractor
from audio_tools.controllers.processor_controller import ProcessorController
from audio_tools.core.file_utils import check_ffmpeg_available


class TqdmLoggingHandler(logging.Handler):
    """让日志与tqdm进度条兼容的处理器"""
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    def emit(self, record):
        try:
            msg = self.format(record)
            # 使用tqdm.write而不是print，这样不会干扰进度条
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)
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
    
    if missing_modules:
        print("\n缺少必要的依赖模块:")
        for module, description in missing_modules:
            print(f"  - {module}: {description}")
        print("\n请使用以下命令安装所需依赖:")
        print("pip install -r requirements.txt")
        return False
    
    # 检查FFmpeg
    if not check_ffmpeg_available():
        print("\n警告: 未检测到FFmpeg，转换视频需要FFmpeg支持")
        print("请安装FFmpeg: https://ffmpeg.org/download.html")
        print("安装后确保将FFmpeg添加到系统PATH中\n")
        return False
    
    return True
def setup_logging(log_file=None):
    """配置日志系统，使其与tqdm兼容"""
    # 创建日志器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除所有现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 添加tqdm兼容的控制台处理器
    console_handler = TqdmLoggingHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    return logger
def main():
    # 设置日志
    setup_logging()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 设置代理(如需要)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
    
    try:
        # 创建处理器控制器
        controller = ProcessorController(
            media_folder='D:/download/',
            output_folder='D:/download/dest/',
            max_retries=3,
            max_workers=4,
            use_jianying_first=True,
            use_kuaishou=True,
            use_bcut=True,
            format_text=True,
            include_timestamps=True,
            show_progress=True,
            process_video=True,
            extract_audio_only=False,
            watch_mode=True,
            max_part_time=20,
            export_srt=True,  # 启用SRT导出
        )
        
        
        # 开始处理
        controller.start_processing()
        
    except KeyboardInterrupt:
        logging.warning("\n程序已被用户中断")
        if controller:
        # 确保中断被正确处理
         controller._handle_interrupt(None, None)

    except Exception as e:
        logging.error(f"\n程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        logging.info("\n程序执行完毕。")

if __name__ == "__main__":
    main()