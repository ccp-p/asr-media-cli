"""
核心功能模块
"""

# 导出工具函数
from .utils import setup_logging

# 导出音频处理器
from .audio_processor import AudioProcessor

# 导出视频转换功能
from .video_converter import process_media_file, check_ffmpeg_available

# 导出文件监控功能
from .file_watcher import start_file_watcher
