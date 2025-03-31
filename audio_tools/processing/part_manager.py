import os
import logging
import re
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
        # 不再对文件名进行处理，保留完整的文件名
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # 如果是重建的虚拟路径，则使用最后一部分作为目录名
        if audio_path.startswith("__reconstructed__/"):
            base_name = os.path.basename(audio_path.replace("__reconstructed__/", ""))
        
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
        创建汇总索引文件，内容包含所有part的文本
        
        Args:
            audio_path: 音频文件路径
            processed_files: 已处理文件记录
            
        Returns:
            索引文件路径，如果未全部完成则返回None
        """
        import os
        
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
            
            # 写入目录
            f.write("\n## 目录\n\n")
            for i in range(file_record.get("total_parts", 0)):
                part_key = str(i)
                if part_key in file_record["parts"] and file_record["parts"][part_key].get("completed", False):
                    part_file = os.path.basename(file_record["parts"][part_key]["output_file"])
                    part_name = f"Part {i+1}"
                    # 计算每个部分的起始和结束时间
                    start_time, end_time = self.get_part_time_range(i)
                    f.write(f"- [{part_name}](./{part_file}) - "
                           f"{start_time/60:.1f}-{end_time/60:.1f}分钟\n")
            
            # 写入完整内容（所有part的总和）
            f.write("\n## 完整内容\n\n")
            
            # 按照part顺序读取并合并所有part内容
            for i in range(file_record.get("total_parts", 0)):
                part_key = str(i)
                if part_key in file_record["parts"] and file_record["parts"][part_key].get("completed", False):
                    part_file_path = file_record["parts"][part_key]["output_file"]
                    
                    # 添加part分隔标记
                    start_time, end_time = self.get_part_time_range(i)
                    f.write(f"\n### Part {i+1} ({start_time/60:.1f}-{end_time/60:.1f}分钟)\n\n")
                    
                    # 读取part文件内容并写入索引文件
                    try:
                        with open(part_file_path, 'r', encoding='utf-8') as part_file:
                            # 跳过part文件中的元数据部分（通常是文件开头的几行）
                            part_content = part_file.read()
                            
                            # 如果part文件有标题或元数据，可以尝试跳过
                            # 这里假设正文内容从第一个空行后开始
                            if "---" in part_content[:200]:
                                # 如果文件使用Markdown格式的元数据块
                                part_content = part_content.split("---", 2)[-1].strip()
                            elif "原始文件:" in part_content[:200]:
                                # 如果文件包含元数据但没有明确分隔符，尝试找到第一个空行
                                lines = part_content.split("\n")
                                metadata_end = 0
                                for idx, line in enumerate(lines[:10]):
                                    if not line.strip():
                                        metadata_end = idx + 1
                                        break
                                if metadata_end > 0:
                                    part_content = "\n".join(lines[metadata_end:]).strip()
                            
                            f.write(part_content)
                            f.write("\n\n")  # 在各部分之间添加空行
                    except Exception as e:
                        f.write(f"[无法读取Part {i+1}内容: {str(e)}]\n\n")
        
        return index_path

    def rebuild_index_files(self, output_folder: Optional[str] = None, processed_files: Optional[Dict] = None) -> Dict:
        """
        扫描输出目录，重新生成所有处理过的音频的索引文件，确保包含完整内容
        支持多种 part 文件命名格式
        
        Args:
            output_folder: 输出目录，如果为None则使用self.output_folder
            processed_files: 已处理文件记录，如果为None则重新扫描并构建
            
        Returns:
            处理结果统计: {"total": 总数, "updated": 更新数, "failed": 失败数, "skipped": 跳过数}
        """
        import os
        import glob
        import logging
        import json
        import re
        
        # 确定输出文件夹
        output_folder = output_folder or self.output_folder
        if not os.path.exists(output_folder):
            logging.error(f"输出文件夹不存在: {output_folder}")
            return {"total": 0, "updated": 0, "failed": 0, "skipped": 0}
        
        # 如果没有提供处理记录，尝试加载或重建
        if processed_files is None:
            processed_files = {}
            # 尝试从记录文件加载
            record_path = os.path.join(output_folder, "processed_records.json")
            if os.path.exists(record_path):
                try:
                    with open(record_path, 'r', encoding='utf-8') as f:
                        processed_files = json.load(f)
                    logging.info(f"已加载处理记录: {len(processed_files)} 个文件")
                except Exception as e:
                    logging.warning(f"加载处理记录文件失败: {str(e)}")
        
        # 编译正则表达式以匹配part文件
        part_pattern = re.compile(r'(?:^part_?\d+\.txt$|^.*_part_?\d+\.txt$)', re.IGNORECASE)
        
        # 统计数据
        stats = {"total": 0, "updated": 0, "failed": 0, "skipped": 0}
        
        # 递归查找所有包含 part 文件的目录
        def find_part_directories(root_dir):
            result = []
            for root, dirs, files in os.walk(root_dir):
                # 检查当前目录是否包含 part 文件
                has_part_files = any(part_pattern.match(f) for f in files)
                if has_part_files:
                    result.append(root)
            return result
        
        # 自定义排序函数，按照part索引排序
        def sort_part_files(filename):
            basename = os.path.basename(filename)
            # 尝试提取数字部分
            match = re.search(r'part_?(\d+)\.txt$', basename, re.IGNORECASE)
            if match:
                return int(match.group(1))
            # 尝试提取 _part 后的数字
            match = re.search(r'_part_?(\d+)\.txt$', basename, re.IGNORECASE)
            if match:
                return int(match.group(1))
            # 默认返回大数字，确保无法识别的文件排在后面
            return 9999
        
        # 获取所有包含 part 文件的目录
        audio_dirs = find_part_directories(output_folder)
        
        logging.info(f"开始扫描 {len(audio_dirs)} 个包含 part 文件的目录以重建索引文件")
        
        for audio_dir in audio_dirs:
            stats["total"] += 1
            audio_dir_name = os.path.basename(audio_dir)  # 获取目录名称
            
            # 检查是否存在part文件并获取它们
            # 使用通配符匹配各种可能的 part 文件模式
            potential_part_files = []
            # 匹配 part_1.txt 格式
            potential_part_files.extend(glob.glob(os.path.join(audio_dir, "part_*.txt")))
            # 匹配 part1.txt 格式
            potential_part_files.extend(glob.glob(os.path.join(audio_dir, "part*.txt")))
            # 匹配 *_part1.txt 和 *_part_1.txt 格式
            potential_part_files.extend(glob.glob(os.path.join(audio_dir, "*_part*.txt")))
            
            # 过滤重复文件并按自定义逻辑排序
            part_files = sorted(set(potential_part_files), key=sort_part_files)
            
            if not part_files:
                logging.warning(f"目录中没有找到part文件: {audio_dir}")
                stats["skipped"] += 1
                continue
            
            # 尝试构建或更新文件记录
            try:
                # 查找原始音频文件路径
                audio_path = None
                relative_dir = os.path.relpath(audio_dir, output_folder)
                
                if processed_files:
                    # 从现有记录中查找
                    for path, record in processed_files.items():
                        parts_data = record.get("parts", {})
                        if parts_data:
                            first_part_file = next(iter(parts_data.values())).get("output_file", "")
                            if first_part_file:
                                part_dir = os.path.dirname(first_part_file)
                                if os.path.normpath(part_dir) == os.path.normpath(audio_dir):
                                    audio_path = path
                                    break
                
                # 如果找不到原始路径，使用虚拟路径
                if not audio_path:
                    audio_path = f"__reconstructed__/{relative_dir}"
                    processed_files[audio_path] = {}
                
                file_record = processed_files.get(audio_path, {})
                
                # 重建文件记录
                if "parts" not in file_record:
                    file_record["parts"] = {}
                
                # 获取part数量
                total_parts = len(part_files)
                file_record["total_parts"] = total_parts
                file_record["filename"] = audio_dir_name
                
                # 估算总时长
                total_duration = total_parts * self.seconds_per_part
                file_record["total_duration"] = total_duration
                
                # 标记为已完成
                file_record["completed"] = True
                file_record["last_processed_time"] = file_record.get("last_processed_time") or "未知"
                
                # 跟踪已处理的part索引，确保不会有重复
                processed_indices = set()
                
                # 更新每个part的信息
                for i, part_file in enumerate(part_files):
                    part_filename = os.path.basename(part_file)
                    try:
                        # 从文件名中提取part索引
                        part_idx = None
                        
                        # 尝试使用正则表达式匹配不同的格式
                        match = re.search(r'(?:^|_)part_?(\d+)\.txt$', part_filename, re.IGNORECASE)
                        if match:
                            part_idx = int(match.group(1)) - 1
                        
                        # 如果无法提取索引，使用文件的顺序作为索引
                        if part_idx is None or part_idx in processed_indices:
                            part_idx = i
                        
                        processed_indices.add(part_idx)
                        part_key = str(part_idx)
                        
                        if part_key not in file_record["parts"]:
                            file_record["parts"][part_key] = {}
                        
                        file_record["parts"][part_key].update({
                            "completed": True,
                            "output_file": part_file,
                            "completed_time": file_record.get("last_processed_time") or "未知",
                        })
                    except Exception as e:
                        logging.warning(f"解析part文件名失败: {part_file}, 错误: {str(e)}")
                        continue
                
                # 更新处理记录
                processed_files[audio_path] = file_record
                
                # 生成新的索引文件
                index_path = self.create_index_file(audio_path, processed_files)
                if index_path:
                    logging.info(f"已更新索引文件: {index_path}")
                    stats["updated"] += 1
                else:
                    logging.warning(f"索引文件创建失败: {audio_dir}")
                    stats["failed"] += 1
                    
            except Exception as e:
                logging.error(f"重建索引文件时出错: {audio_dir}, 错误: {str(e)}")
                import traceback
                traceback.print_exc()
                stats["failed"] += 1
        
        # 保存更新后的处理记录
        record_path = os.path.join(output_folder, "processed_records.json")
        try:
            with open(record_path, 'w', encoding='utf-8') as f:
                json.dump(processed_files, f, ensure_ascii=False, indent=2)
            logging.info(f"已保存更新后的处理记录: {record_path}")
        except Exception as e:
            logging.error(f"保存处理记录失败: {str(e)}")
        
        # 打印统计信息
        logging.info(f"索引文件重建完成: 总共 {stats['total']} 个目录, "
                    f"更新 {stats['updated']} 个, 失败 {stats['failed']} 个, 跳过 {stats['skipped']} 个")
        
        return stats

if __name__ == "__main__":
    # 创建Part管理器
    # part_manager = PartManager(output_folder='D:/download/dest/',minutes_per_part=20)
    

    # 重建索引文件
    # part_manager.rebuild_index_files()
    pass