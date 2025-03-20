import os
import logging
import time
from typing import Dict, List, Tuple, Optional, Any

class PartManager:
    """管理大音频文件的分part处理和断点续传"""
    
    def __init__(self, output_folder: str, minutes_per_part: int = 20):
        """
        初始化Part管理器
        
        Args:
            output_folder: 输出文件夹路径
            minutes_per_part: 每个part的时长（分钟）
        """
        self.output_folder = output_folder
        self.minutes_per_part = minutes_per_part
        self.seconds_per_part = minutes_per_part * 60
        
    def get_parts_for_audio(self, audio_path: str, total_duration: float, 
                           processed_files: Dict) -> Tuple[Dict, List[int]]:
        """
        获取音频文件的parts信息
        
        Args:
            audio_path: 音频文件路径
            total_duration: 音频总时长（秒）
            processed_files: 已处理文件记录
            
        Returns:
            (parts信息, 待处理part列表)
        """
        # 计算总part数
        total_parts = self._calculate_total_parts(total_duration)
        
        # 获取或创建音频的处理记录
        file_record = processed_files.get(audio_path, {})
        
        # 初始化part信息
        if "parts" not in file_record:
            file_record["parts"] = {}
        if "total_parts" not in file_record:
            file_record["total_parts"] = total_parts
            
        # 更新文件记录
        file_record["filename"] = os.path.basename(audio_path)
        file_record["total_duration"] = total_duration
        processed_files[audio_path] = file_record
        
        # 获取待处理的parts
        pending_parts = []
        for part_idx in range(total_parts):
            part_key = str(part_idx)
            if part_key not in file_record["parts"] or not file_record["parts"][part_key].get("completed", False):
                pending_parts.append(part_idx)
                
        return file_record, pending_parts
    
    def _calculate_total_parts(self, duration_seconds: float) -> int:
        """
        计算音频总共需要分成多少part
        
        Args:
            duration_seconds: 音频总时长（秒）
        
        Returns:
            总part数
        """
        return max(1, int(duration_seconds / self.seconds_per_part) + 
                  (1 if duration_seconds % self.seconds_per_part > 0 else 0))
    
    def get_part_time_range(self, part_idx: int) -> Tuple[float, float]:
        """
        获取指定part的时间范围
        
        Args:
            part_idx: part索引（从0开始）
        
        Returns:
            (开始时间, 结束时间)，单位秒
        """
        start_time = part_idx * self.seconds_per_part
        end_time = (part_idx + 1) * self.seconds_per_part
        return start_time, end_time
    
    def get_segments_for_part(self, part_idx: int, segment_files: List[str], 
                             segment_duration: float = 30.0) -> List[str]:
        """
        获取指定part包含的音频片段列表
        
        Args:
            part_idx: part索引（从0开始）
            segment_files: 所有片段文件列表
            segment_duration: 每个片段的时长（秒）
            
        Returns:
            该part包含的片段文件列表
        """
        start_time, end_time = self.get_part_time_range(part_idx)
        
        # 计算片段的起始和结束索引
        start_segment_idx = int(start_time / segment_duration)
        end_segment_idx = min(int(end_time / segment_duration) + 1, len(segment_files))
        
        # 返回这个范围内的片段
        return segment_files[start_segment_idx:end_segment_idx]
    
    def create_part_output_folder(self, audio_path: str) -> str:
        """
        为分part处理创建输出文件夹
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            输出文件夹路径
        """
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = os.path.join(self.output_folder, base_name)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def save_part_text(self, audio_path: str, part_idx: int, 
                     text: str, processed_files: Dict) -> str:
        """
        保存part文本并更新处理状态
        
        Args:
            audio_path: 音频文件路径
            part_idx: part索引
            text: 转写文本
            processed_files: 已处理文件记录
            
        Returns:
            保存的文件路径
        """
        # 1. 创建输出文件夹
        output_dir = self.create_part_output_folder(audio_path)
        
        # 2. 获取文件记录
        file_record = processed_files.get(audio_path, {})
        if "parts" not in file_record:
            file_record["parts"] = {}
        
        # 3. 保存part文本
        part_filename = f"part_{part_idx+1}.txt"  # 从1开始编号，更友好
        output_path = os.path.join(output_dir, part_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # 4. 更新part状态
        part_key = str(part_idx)
        if part_key not in file_record["parts"]:
            file_record["parts"][part_key] = {}
            
        file_record["parts"][part_key].update({
            "completed": True,
            "output_file": output_path,
            "completed_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        
        # 5. 检查是否所有part都已完成
        completed_parts = sum(1 for p in file_record["parts"].values() 
                             if p.get("completed", False))
        file_record["completed"] = completed_parts >= file_record.get("total_parts", 0)
        file_record["last_processed_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        processed_files[audio_path] = file_record
        
        return output_path
    def _extract_asr_info(self, file_record: Dict) -> Dict:
        """
        从文件记录中提取 ASR 相关信息
        
        Args:
            file_record: 文件处理记录
            
        Returns:
            ASR 信息字典
        """
        asr_info = {}
        
        # 提取 ASR 模型信息
        if "asr_model" in file_record:
            asr_info["模型"] = file_record.get("asr_model", "未知")
        
        # 提取识别统计信息
        successful_segments = 0
        total_segments = 0
        
        for part_key, part_data in file_record.get("parts", {}).items():
            if "segment_stats" in part_data:
                successful_segments += part_data["segment_stats"].get("successful", 0)
                total_segments += part_data["segment_stats"].get("total", 0)
        
        if total_segments > 0:
            asr_info["识别成功率"] = f"{successful_segments}/{total_segments} 片段 ({successful_segments/total_segments:.1%})"
        
        return asr_info
    def create_index_file(self, audio_path: str, processed_files: Dict) -> Optional[str]:
        """
        创建汇总索引文件
        
        Args:
            audio_path: 音频文件路径
            processed_files: 已处理文件记录
            
        Returns:
            索引文件路径，如果未全部完成则返回None
        """
        file_record = processed_files.get(audio_path, {})
        
        # 如果未全部完成，不创建索引
        if not file_record.get("completed", False):
            return None
            
        output_dir = self.create_part_output_folder(audio_path)
        index_path = os.path.join(output_dir, "index.txt")
        
        with open(index_path, 'w', encoding='utf-8') as f:
            # 写入基本信息
            f.write(f"# {file_record.get('filename', '未知文件')}\n\n")
            f.write(f"- 总时长: {file_record.get('total_duration', 0)/60:.1f}分钟\n")
            f.write(f"- 共分{file_record.get('total_parts', 0)}个部分\n")
            f.write(f"- 完成时间: {file_record.get('last_processed_time', '')}\n")
            
            # 获取并写入 ASR 信息
            asr_info = self._extract_asr_info(file_record)
            if asr_info:
                f.write("\n## ASR 识别信息\n\n")
                for key, value in asr_info.items():
                    f.write(f"- {key}: {value}\n")
            
            # 写入各部分链接
            f.write("\n## 目录\n\n")
            for i in range(file_record.get("total_parts", 0)):
                part_key = str(i)
                if part_key in file_record["parts"] and file_record["parts"][part_key].get("completed", False):
                    part_file = os.path.basename(file_record["parts"][part_key]["output_file"])
                    part_name = f"Part {i+1}"
                    f.write(f"- [{part_name}](./{part_file}) - " 
                           f"{self.minutes_per_part}分钟\n")
        
        return index_path
        """
        创建汇总索引文件
        
        Args:
            audio_path: 音频文件路径
            processed_files: 已处理文件记录
            
        Returns:
            索引文件路径，如果未全部完成则返回None
        """
        file_record = processed_files.get(audio_path, {})
        
        # 如果未全部完成，不创建索引
        if not file_record.get("completed", False):
            return None
            
        output_dir = self.create_part_output_folder(audio_path)
        index_path = os.path.join(output_dir, "index.txt")
        
        with open(index_path, 'w', encoding='utf-8') as f:
            # 写入基本信息
            f.write(f"# {file_record.get('filename', '未知文件')}\n\n")
            f.write(f"- 总时长: {file_record.get('total_duration', 0)/60:.1f}分钟\n")
            f.write(f"- 共分{file_record.get('total_parts', 0)}个部分\n")
            f.write(f"- 完成时间: {file_record.get('last_processed_time', '')}\n\n")
            
            # 写入各部分链接
            f.write("## 目录\n\n")
            for i in range(file_record.get("total_parts", 0)):
                part_key = str(i)
                if part_key in file_record["parts"] and file_record["parts"][part_key].get("completed", False):
                    part_file = os.path.basename(file_record["parts"][part_key]["output_file"])
                    part_name = f"Part {i+1}"
                    f.write(f"- [{part_name}](./{part_file}) - " 
                           f"{self.minutes_per_part}分钟\n")
        
        return index_path