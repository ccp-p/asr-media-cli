import requests
import logging
from typing import Union, List, Dict

from .base_asr import BaseASR, ASRDataSeg

class KuaiShouASR(BaseASR):
    """快手语音识别实现"""
    def __init__(self, audio_path: Union[str, bytes], use_cache: bool = False):
        super().__init__(audio_path, use_cache)
    
    def _run(self, callback=None):
        """执行识别过程"""
        if callback:
            callback(50, "正在识别...")
            
        result = self._submit()
        
        if callback:
            callback(100, "识别完成")
            
        return result

    def _make_segments(self, resp_data: dict) -> List[ASRDataSeg]:
        """处理识别结果"""
        try:
            return [ASRDataSeg(u['text'], u['start_time'], u['end_time']) for u in resp_data['data']['text']]
        except (KeyError, TypeError) as e:
            logging.error(f"快手ASR结果解析失败: {str(e)}")
            return []

    def _submit(self) -> dict:
        """提交识别请求"""
        try:
            payload = {
                "typeId": "1"
            }
            files = [('file', ('test.mp3', self.file_binary, 'audio/mpeg'))]
            result = requests.post("https://ai.kuaishou.com/api/effects/subtitle_generate", data=payload, files=files)
            return result.json()
        except Exception as e:
            logging.error(f"快手ASR请求失败: {str(e)}")
            return {"data": {"text": []}}
