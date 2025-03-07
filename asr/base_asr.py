import logging
from typing import Union, List, Dict

class ASRDataSeg:
    """语音识别结果段落"""
    def __init__(self, text: str, start_time: float, end_time: float):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time

class BaseASR:
    """语音识别基础类"""
    def __init__(self, audio_path: Union[str, bytes], use_cache: bool = False):
        self.audio_path = audio_path
        self.use_cache = use_cache
        self._load_file()
        self._calculate_crc32()
    
    def _load_file(self):
        """加载音频文件到内存"""
        if isinstance(self.audio_path, bytes):
            self.file_binary = self.audio_path
        else:
            with open(self.audio_path, 'rb') as f:
                self.file_binary = f.read()
    
    def _calculate_crc32(self):
        """计算文件的CRC32校验和"""
        import zlib
        self.crc32 = zlib.crc32(self.file_binary)
        self.crc32_hex = format(self.crc32 & 0xFFFFFFFF, '08x')
    
    def get_result(self, callback=None):
        """获取识别结果"""
        resp = self._run(callback)
        segments = self._make_segments(resp)
        return segments
    
    def _run(self, callback=None):
        """执行识别过程，需要被子类重写"""
        raise NotImplementedError
    
    def _make_segments(self, resp_data):
        """处理识别结果，需要被子类重写"""
        raise NotImplementedError
    
    def _get_key(self):
        """获取缓存键，需要被子类重写"""
        return f"{self.__class__.__name__}-{self.crc32_hex}"
