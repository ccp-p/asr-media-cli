"""
音频处理工具包
提供音频分割、识别和转写功能
"""

from .controllers.processor_controller import ProcessorController
from .core.audio_extractor import AudioExtractor
from .core.file_utils import check_ffmpeg_available, setup_logging

__all__ = ['ProcessorController', 'AudioExtractor', 'check_ffmpeg_available', 'setup_logging']