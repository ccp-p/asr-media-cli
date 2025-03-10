import os
import re
import logging
import json
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import time

# 导入现有的处理模块
from covert import convert_mp3_to_txt, load_processed_records

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_mp3_by_txt_name(txt_file_path: str, processed_records: Dict) -> str:
    """
    根据txt文件名找到对应的原始MP3文件
    
    Args:
        txt_file_path: txt文件路径
        processed_records: 已处理文件记录
        
    Returns:
        原始MP3文件路径，如果找不到则返回空字符串
    """
    # 从记录中查找
    for mp3_path, info in processed_records.items():
        if info.get("output_file") == txt_file_path:
            # 检查原始MP3文件是否存在
            if os.path.exists(mp3_path):
                return mp3_path
    
    # 如果记录中找不到，尝试通过名称猜测
    txt_name = os.path.basename(txt_file_path)
    txt_name_without_ext = os.path.splitext(txt_name)[0]
    
    # 尝试在相同目录查找
    mp3_dir = os.path.dirname(os.path.dirname(txt_file_path))  # 假设mp3在txt上级目录
    mp3_path = os.path.join(mp3_dir, f"{txt_name_without_ext}.mp3")
    
    if os.path.exists(mp3_path):
        return mp3_path
    
    return ""

def check_txt_file_for_unrecognized(txt_path: str) -> bool:
    """
    检查txt文件是否包含未识别的片段
    
    Args:
        txt_path: txt文件路径
        
    Returns:
        如果包含未识别片段则返回True，否则False
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查是否包含未识别标记
            return "[无法识别的音频片段]" in content
    except Exception as e:
        logging.error(f"读取文件 {txt_path} 出错: {e}")
        return False

def find_files_needing_recheck(output_folder: str, processed_record_file: str) -> List[Tuple[str, str]]:
    """
    查找需要重新识别的文件
    
    Args:
        output_folder: 输出文件夹
        processed_record_file: 处理记录文件
        
    Returns:
        需要重新识别的文件列表，格式为 [(mp3_path, txt_path), ...]
    """
    # 加载已处理记录
    processed_records = load_processed_records(processed_record_file)
    
    # 记录需要重新识别的文件
    files_to_recheck = []
    
    # 遍历输出文件夹中的txt文件
    for txt_file in Path(output_folder).glob("*.txt"):
        txt_path = str(txt_file)
        
        # 检查文件是否包含未识别片段
        if check_txt_file_for_unrecognized(txt_path):
            # 找到对应的mp3文件
            mp3_path = find_mp3_by_txt_name(txt_path, processed_records)
            
            if mp3_path:
                files_to_recheck.append((mp3_path, txt_path))
                logging.info(f"找到需要重新识别的文件: {os.path.basename(mp3_path)}")
            else:
                logging.warning(f"无法找到与 {os.path.basename(txt_path)} 对应的MP3文件")
    
    return files_to_recheck

def format_time_duration(seconds):
    """
    将秒数格式化为更易读的时间格式 (HH:MM:SS)
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def reprocess_audio_files(files_to_recheck: List[Tuple[str, str]], 
                         temp_output_folder: str,
                         use_jianying_first: bool = True, 
                         use_kuaishou: bool = True,
                         use_bcut: bool = True,
                         format_text: bool = True,
                         include_timestamps: bool = True):
    """
    重新处理音频文件
    
    Args:
        files_to_recheck: 需要重新处理的文件列表，格式为 [(mp3_path, txt_path), ...]
        temp_output_folder: 临时输出文件夹
        use_jianying_first: 是否优先使用剪映ASR
        use_kuaishou: 是否使用快手ASR
        use_bcut: 是否使用B站ASR
        format_text: 是否格式化文本
        include_timestamps: 是否包含时间戳
    """
    if not files_to_recheck:
        logging.info("没有找到需要重新识别的文件")
        return
    
    # 记录总开始时间
    total_start_time = time.time()
    
    # 创建临时文件夹
    os.makedirs(temp_output_folder, exist_ok=True)
    
    total_files = len(files_to_recheck)
    success_count = 0
    
    for i, (mp3_path, txt_path) in enumerate(files_to_recheck):
        try:
            # 记录单个文件开始时间
            file_start_time = time.time()
            
            logging.info(f"处理文件 {i+1}/{total_files}: {os.path.basename(mp3_path)}")
            
            # 复制mp3到临时目录（不再需要去除_recognized后缀）
            mp3_name = os.path.basename(mp3_path)
            
            temp_mp3_path = os.path.join(temp_output_folder, mp3_name)
            with open(mp3_path, 'rb') as src_file:
                with open(temp_mp3_path, 'wb') as dst_file:
                    dst_file.write(src_file.read())
            
            # 转换音频为文本，使用现有函数
            convert_mp3_to_txt(
                mp3_folder=temp_output_folder,
                output_folder=temp_output_folder,
                max_retries=3,
                max_workers=4,
                use_jianying_first=use_jianying_first,
                use_kuaishou=use_kuaishou,
                use_bcut=use_bcut,
                format_text=format_text,
                include_timestamps=include_timestamps
            )
            
            # 获取新生成的txt文件
            new_txt_path = os.path.join(temp_output_folder, os.path.basename(txt_path))
            if os.path.exists(new_txt_path):
                # 检查新生成的文件是否还有未识别片段
                if check_txt_file_for_unrecognized(new_txt_path):
                    logging.warning(f"文件 {os.path.basename(mp3_path)} 重新识别后仍有未识别片段")
                
                # 替换原有文件
                with open(new_txt_path, 'r', encoding='utf-8') as src_file:
                    with open(txt_path, 'w', encoding='utf-8') as dst_file:
                        dst_file.write(src_file.read())
                
                logging.info(f"成功替换文件: {os.path.basename(txt_path)}")
                success_count += 1
            else:
                logging.error(f"重新识别未生成新文件: {os.path.basename(txt_path)}")
            
            # 清理临时文件
            if os.path.exists(temp_mp3_path):
                os.remove(temp_mp3_path)
            if os.path.exists(new_txt_path):
                os.remove(new_txt_path)
            
            # 计算并打印文件处理时长
            file_duration = time.time() - file_start_time
            formatted_duration = format_time_duration(file_duration)
            logging.info(f"文件处理完成，耗时: {formatted_duration}")
                
        except Exception as e:
            logging.error(f"处理文件 {os.path.basename(mp3_path)} 时出错: {e}")
    
    # 计算总处理时长
    total_duration = time.time() - total_start_time
    formatted_total_duration = format_time_duration(total_duration)
    logging.info(f"重新识别完成，成功处理 {success_count}/{total_files} 个文件，总耗时: {formatted_total_duration}")
    
    # 计算平均处理时长
    if success_count > 0:
        avg_time = total_duration / success_count
        formatted_avg_time = format_time_duration(avg_time)
        logging.info(f"平均每个文件处理时长: {formatted_avg_time}")
    
    # 尝试清理临时文件夹
    try:
        os.rmdir(temp_output_folder)
    except:
        pass

def main():
    parser = argparse.ArgumentParser(description="检查并重新识别无法识别的音频片段")
     # default output_folder is  D:\download\dest if  path not provide
    parser.add_argument("--output_folder", type=str, default="D:\download\dest", help="输出文件夹路径")
    parser.add_argument("--temp_folder", type=str, default="temp_recheck", help="临时文件夹路径")
     # default use_jianying is  use if  path not provide
    parser.add_argument("--use_jianying", action="store_true", help="使用剪映ASR")
    parser.add_argument("--use_kuaishou", action="store_true", help="使用快手ASR")
    parser.add_argument("--use_bcut", action="store_true", help="使用B站ASR")
    parser.add_argument("--no_format", action="store_true", help="不格式化文本")
    parser.add_argument("--no_timestamps", action="store_true", help="不包含时间戳")
    
    args = parser.parse_args()
    
    output_folder = args.output_folder
    processed_record_file = os.path.join(output_folder, "processed_audio_files.json")
    temp_folder = os.path.join(os.path.dirname(output_folder), args.temp_folder)
    
    # 查找需要重新检查的文件
    logging.info(f"开始检查文件夹: {output_folder}")
    files_to_recheck = find_files_needing_recheck(output_folder, processed_record_file)
    
    if files_to_recheck:
        logging.info(f"找到 {len(files_to_recheck)} 个需要重新识别的文件")
        
        # 重新处理这些文件
        reprocess_audio_files(
            files_to_recheck,
            temp_folder,
            use_jianying_first=args.use_jianying,
            use_kuaishou=args.use_kuaishou,
            use_bcut=args.use_bcut,
            format_text=not args.no_format,
            include_timestamps=not args.no_timestamps
        )
    else:
        logging.info("未找到需要重新识别的文件")

if __name__ == "__main__":
   
    main()
