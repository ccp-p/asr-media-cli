import os
import subprocess
import logging
from typing import Optional

def check_ffmpeg_available():
    """检查是否安装了FFmpeg"""
    try:
        process = subprocess.Popen(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate()
        return process.returncode == 0
    except Exception:
        return False

def convert_ts_to_mp4(input_file: str, output_file: Optional[str] = None) -> str:
    """
    将TS文件转换为MP4格式
    
    Args:
        input_file: 输入的TS文件路径
        output_file: 输出的MP4文件路径，不指定则使用相同名称但后缀为.mp4
        
    Returns:
        str: 转换后的MP4文件路径
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"找不到输入文件: {input_file}")
    
    # 如果未指定输出文件，则使用相同名称但改为.mp4后缀
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + ".mp4"
    
    try:
        # 检查是否安装了FFmpeg
        if not check_ffmpeg_available():
            raise Exception("未检测到FFmpeg，请先安装FFmpeg")
            
        # 使用ffmpeg进行转换
        logging.info(f"正在将 {input_file} 转换为 {output_file}")
        
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-c:v", "copy",   # 复制视频流，不重新编码
            "-c:a", "aac",    # 将音频转换为AAC编码
            "-y",             # 覆盖输出文件
            output_file
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            logging.error(f"转换失败: {stderr}")
            raise Exception(f"TS到MP4转换失败: {stderr}")
        
        logging.info(f"成功将 {input_file} 转换为 {output_file}")
        return output_file
        
    except Exception as e:
        logging.error(f"转换过程中出错: {str(e)}")
        raise

def extract_audio_from_video(input_file: str, output_file: Optional[str] = None) -> str:
    """
    从视频文件中提取音频为MP3格式
    
    Args:
        input_file: 输入的视频文件路径
        output_file: 输出的MP3文件路径，不指定则使用相同名称但后缀为.mp3
        
    Returns:
        str: 提取的MP3文件路径
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"找不到输入文件: {input_file}")
    
    # 如果未指定输出文件，则使用相同名称但改为.mp3后缀
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + ".mp3"
    
    try:
        # 检查是否安装了FFmpeg
        if not check_ffmpeg_available():
            raise Exception("未检测到FFmpeg，请先安装FFmpeg")
            
        logging.info(f"正在从 {input_file} 提取音频到 {output_file}")
        
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-q:a", "0",      # 最高音频质量
            "-map", "a",      # 只处理音频流
            "-y",             # 覆盖输出文件
            output_file
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            logging.error(f"音频提取失败: {stderr}")
            raise Exception(f"音频提取失败: {stderr}")
        
        logging.info(f"成功从 {input_file} 提取音频到 {output_file}")
        return output_file
        
    except Exception as e:
        logging.error(f"音频提取过程中出错: {str(e)}")
        raise

def process_media_file(file_path: str, temp_dir: Optional[str] = None) -> str:
    """
    处理媒体文件：
    - 如果是TS格式，先转换为MP4，然后提取音频为MP3
    - 如果是其他视频格式，直接提取音频为MP3
    - 如果是MP3格式，直接返回路径
    
    Args:
        file_path: 媒体文件路径
        temp_dir: 临时文件存放目录，不指定则使用文件所在目录
        
    Returns:
        str: 处理后的MP3文件路径
    """
    # 获取文件扩展名
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # 设置临时目录
    if not temp_dir:
        temp_dir = os.path.dirname(file_path)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 生成临时文件名
    base_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    # 处理TS文件
    if ext == ".ts":
        logging.info(f"检测到TS文件: {file_path}，开始转换流程")
        # 转换为MP4
        mp4_path = os.path.join(temp_dir, file_name_without_ext + ".mp4")
        mp4_path = convert_ts_to_mp4(file_path, mp4_path)
        
        # 提取音频
        mp3_path = os.path.join(temp_dir, file_name_without_ext + ".mp3")
        mp3_path = extract_audio_from_video(mp4_path, mp3_path)
        
        return mp3_path
    
    # 处理其他视频格式
    elif ext in [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"]:
        logging.info(f"检测到视频文件: {file_path}，提取音频")
        mp3_path = os.path.join(temp_dir, file_name_without_ext + ".mp3")
        mp3_path = extract_audio_from_video(file_path, mp3_path)
        
        return mp3_path
    
    # 如果是MP3格式，直接返回
    elif ext == ".mp3":
        return file_path
    
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
