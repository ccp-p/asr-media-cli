import os
import logging
import subprocess
import tempfile
from typing import Dict, Tuple, List, Optional, Any, Type, Set, Callable
import random

# 导入ASR模块
from asr import GoogleASR, JianYingASR, KuaiShouASR, BcutASR, ASRDataSeg, ASRServiceSelector

class ASRManager:
    """
    ASR服务管理器，负责服务选择、失败处理和统计
    """
    
    def __init__(self, use_jianying_first: bool = False, 
                 use_kuaishou: bool = False, use_bcut: bool = False):
        """
        初始化ASR服务管理器
        
        Args:
            use_jianying_first: 是否优先使用剪映ASR
            use_kuaishou: 是否使用快手ASR
            use_bcut: 是否使用B站ASR
        """
        self.use_jianying_first = use_jianying_first
        self.use_kuaishou = use_kuaishou
        self.use_bcut = use_bcut
        
        # 创建ASR服务选择器
        self.selector = ASRServiceSelector()
        
        # 注册ASR服务
        self._register_services()
        
    def _register_services(self):
        """注册ASR服务到服务选择器"""
        # 根据用户配置设置权重
        google_weight = 5 if (self.use_jianying_first or self.use_kuaishou or self.use_bcut) else 20
        jianying_weight = 20 if self.use_jianying_first else 10
        kuaishou_weight = 25 if self.use_kuaishou else 0  # 0表示不使用
        bcut_weight = 30 if self.use_bcut else 0  # 0表示不使用
        
        # 注册服务
        self.selector.register_service("Google", GoogleASR, weight=google_weight)
        self.selector.register_service("剪映", JianYingASR, weight=jianying_weight)
        
        if self.use_kuaishou:
            self.selector.register_service("快手", KuaiShouASR, weight=kuaishou_weight)
        
        if self.use_bcut:
            self.selector.register_service("B站", BcutASR, weight=bcut_weight)
        
        logging.info("ASR服务注册完成")
    
    def select_service(self) -> Optional[Tuple[str, Type]]:
        """
        选择一个ASR服务
        
        Returns:
            服务名称和服务类的元组，无可用服务时返回None
        """
        return self.selector.select_service()
    
    def report_result(self, service_name: str, success: bool):
        """
        报告服务使用结果
        
        Args:
            service_name: 服务名称
            success: 是否成功
        """
        self.selector.report_result(service_name, success)
    
    def recognize_audio(self, audio_path: str, max_attempts: int = 3) -> Optional[str]:
        """
        识别单个音频片段，尝试多个ASR服务
        
        Args:
            audio_path: 音频文件路径
            max_attempts: 最大尝试次数
            
        Returns:
            识别结果文本，失败返回None
        """
        attempts = 0
        # 已尝试的服务，避免重复使用
        tried_services: Set[str] = set()
        
        while attempts < max_attempts:
            # 选择一个ASR服务
            service_result = self.select_service()
            if not service_result:
                logging.warning("没有可用的ASR服务")
                break
                
            name, service_class = service_result
            
            # 如果已经尝试过该服务，且还有其他服务可用，则继续选择
            if name in tried_services and attempts < max_attempts - 1:
                attempts += 1
                continue
                
            tried_services.add(name)
            
            logging.info(f"尝试使用 {name} ASR识别: {os.path.basename(audio_path)}")
            try:
                # 创建ASR实例并识别
                asr = service_class(audio_path)
                segments = asr.get_result(
                    callback=lambda p, m: logging.info(f"{name}识别进度: {p}% - {m}")
                )
                
                if segments:
                    result_text = " ".join([seg.text for seg in segments if seg.text])
                    if result_text:
                        logging.info(f"{name} ASR识别成功: {os.path.basename(audio_path)}")
                        self.report_result(name, True)  # 报告成功
                        return result_text
                
                logging.warning(f"{name} ASR未能识别文本")
                self.report_result(name, False)  # 报告失败
                
            except Exception as e:
                logging.error(f"{name} ASR识别出错: {str(e)}")
                self.report_result(name, False)  # 报告失败
            
            attempts += 1
        
        # 所有服务都失败了
        logging.error(f"所有ASR服务均未能识别: {os.path.basename(audio_path)}")
        return None
    
    def get_service_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取服务使用统计数据
        
        Returns:
            服务使用统计数据
        """
        return self.selector.get_service_stats()
    
    def is_video_file(self, file_path: str) -> bool:
        """
        判断文件是否为视频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为视频文件
        """
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
        _, ext = os.path.splitext(file_path.lower())
        return ext in video_extensions
        
    def extract_audio_from_video(self, video_path: str) -> str:
        """
        从视频提取音频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            提取的音频文件路径
        """
        # 创建临时文件用于存储提取的音频
        temp_dir = tempfile.gettempdir()
        video_filename = os.path.basename(video_path)
        audio_filename = f"{os.path.splitext(video_filename)[0]}_audio.wav"
        audio_path = os.path.join(temp_dir, audio_filename)
        
        try:
            # 使用FFmpeg提取音频
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-q:a', '0',
                '-map', 'a',
                '-y',  # 覆盖已存在的文件
                audio_path
            ]
            
            logging.info(f"正在从视频提取音频: {video_filename}")
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"音频提取成功: {audio_filename}")
            
            return audio_path
        except subprocess.CalledProcessError as e:
            logging.error(f"音频提取失败: {str(e)}")
            raise RuntimeError(f"无法从视频提取音频: {str(e)}")
        except Exception as e:
            logging.error(f"处理视频时出错: {str(e)}")
            raise
    
    def recognize_media(self, media_path: str, max_attempts: int = 3) -> Optional[str]:
        """
        识别音频或视频文件内容
        
        Args:
            media_path: 媒体文件路径（音频或视频）
            max_attempts: 最大尝试次数
            
        Returns:
            识别结果文本，失败返回None
        """
        try:
            # 判断输入是视频还是音频
            if self.is_video_file(media_path):
                # 视频先提取音频
                audio_path = self.extract_audio_from_video(media_path)
                result = self.recognize_audio(audio_path, max_attempts)
                
                # 尝试删除临时音频文件
                try:
                    os.remove(audio_path)
                except:
                    logging.warning(f"无法删除临时音频文件: {audio_path}")
                    
                return result
            else:
                # 直接作为音频处理
                return self.recognize_audio(media_path, max_attempts)
        except Exception as e:
            logging.error(f"媒体识别过程出错: {str(e)}")
            return None
