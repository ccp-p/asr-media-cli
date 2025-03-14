import os
import logging
import sys
from audio_tools.core.audio_extractor import AudioExtractor
from audio_tools.controllers.processor_controller import ProcessorController
from audio_tools.core.file_utils import check_ffmpeg_available

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join('output', 'audio_processing.log'), encoding='utf-8')
        ]
    )

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
            watch_mode=True
        )
        
        # 开始处理
        controller.start_processing()
        
    except KeyboardInterrupt:
        logging.warning("\n程序已被用户中断")
    except Exception as e:
        logging.error(f"\n程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        logging.info("\n程序执行完毕。")

if __name__ == "__main__":
    main()