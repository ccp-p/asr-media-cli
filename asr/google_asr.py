import speech_recognition as sr
import logging
from typing import Union, List, Dict
from .base_asr import BaseASR, ASRDataSeg

class GoogleASR(BaseASR):
    """Google语音识别实现"""
    def __init__(self, audio_path: Union[str, bytes], use_cache: bool = False, language: str = 'zh-CN'):
        super().__init__(audio_path, use_cache)
        self.language = language
    
    def _run(self, callback=None):
        """执行识别过程"""
        if callback:
            callback(50, "正在识别...")
        
        result = self._recognize()
        
        if callback:
            callback(100, "识别完成")
        
        return {"text": result} if result else {"text": ""}
    
    def _make_segments(self, resp_data):
        """处理识别结果"""
        if resp_data and resp_data.get("text"):
            # 创建一个单一段落，没有时间戳
            return [ASRDataSeg(resp_data["text"], 0, 0)]
        return []
    
    def _recognize(self):
        """使用Google API识别音频"""
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(self.audio_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=self.language)
                logging.info(f"Google API识别成功: {self.audio_path}")
                return text
        except (sr.UnknownValueError, Exception) as e:
            logging.error(f"Google API识别失败: {str(e)}")
            return None
