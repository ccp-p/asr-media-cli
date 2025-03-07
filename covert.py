import os
import tempfile
import shutil
import time
import json
import concurrent.futures
from pathlib import Path
import logging
import requests
from pydub import AudioSegment

# 导入ASR模块
from asr import GoogleASR, JianYingASR, KuaiShouASR, BcutASR, ASRDataSeg, ASRServiceSelector
from text_formatter import TextFormatter

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
print(requests.get("https://www.google.com").status_code)

# 创建全局的ASR服务选择器
asr_selector = ASRServiceSelector()

def load_processed_records(file_path):
    """加载已处理文件记录"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"读取记录文件 {file_path} 出错。创建新记录。")
    return {}

def save_processed_records(file_path, records):
    """保存已处理文件记录"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)

def register_asr_services(use_jianying_first=False, use_kuaishou=False, use_bcut=False):
    """
    注册ASR服务到服务选择器
    
    Args:
        use_jianying_first: 是否优先使用剪映
        use_kuaishou: 是否使用快手
        use_bcut: 是否使用B站
    """
    # 根据用户配置设置权重
    # 基础权重：Google=10, 其他通过参数控制
    google_weight = 5 if (use_jianying_first or use_kuaishou or use_bcut) else 20
    jianying_weight = 20 if use_jianying_first else 10
    kuaishou_weight = 25 if use_kuaishou else 0  # 0表示不使用
    bcut_weight = 30 if use_bcut else 0  # 0表示不使用
    
    # 注册所有启用的服务
    asr_selector.register_service("Google", GoogleASR, weight=google_weight)
    asr_selector.register_service("剪映", JianYingASR, weight=jianying_weight)
    
    if use_kuaishou:
        asr_selector.register_service("快手", KuaiShouASR, weight=kuaishou_weight)
    
    if use_bcut:
        asr_selector.register_service("B站", BcutASR, weight=bcut_weight)
    
    logging.info("ASR服务注册完成")

def recognize_audio(audio_path, language='zh-CN', retries=0, use_jianying_first=True, 
                   use_kuaishou=False, use_bcut=False):
    """
    使用服务选择器选择ASR服务识别音频
    
    Args:
        audio_path: 音频文件路径
        language: 语言代码，默认中文
        retries: 重试次数
        use_jianying_first: 是否优先使用剪映ASR
        use_kuaishou: 是否使用快手ASR
        use_bcut: 是否使用B站ASR
        
    Returns:
        识别的文本内容，失败返回None
    """
    # 最多尝试的服务数量
    max_attempts = 3
    attempts = 0
    
    # 已尝试的服务，避免重复使用
    tried_services = set()
    
    while attempts < max_attempts:
        # 选择一个ASR服务
        service_result = asr_selector.select_service()
        if not service_result:
            logging.warning("没有可用的ASR服务")
            break
            
        name, service_class = service_result
        
        # 如果已经尝试过该服务，且还有其他服务可用，则继续选择
        if name in tried_services and attempts < max_attempts - 1:
            attempts += 1
            continue
            
        tried_services.add(name)
        
        logging.info(f"尝试使用 {name} ASR识别: {audio_path}")
        try:
            # 创建ASR实例并识别
            asr = service_class(audio_path)
            segments = asr.get_result(callback=lambda p, m: logging.info(f"{name}识别进度: {p}% - {m}"))
            
            if segments:
                result_text = " ".join([seg.text for seg in segments if seg.text])
                if result_text:
                    logging.info(f"{name} ASR识别成功: {audio_path}")
                    asr_selector.report_result(name, True)  # 报告成功
                    return result_text
            
            logging.warning(f"{name} ASR未能识别文本")
            asr_selector.report_result(name, False)  # 报告失败
            
        except Exception as e:
            logging.error(f"{name} ASR识别出错: {str(e)}")
            asr_selector.report_result(name, False)  # 报告失败
        
        attempts += 1
    
    # 所有服务都失败了
    logging.error(f"所有ASR服务均未能识别: {audio_path}")
    return None

def split_audio(input_folder, output_folder, segment_length=55, file_pattern=None):
    """
    分割音频文件为指定时长的片段
    """
    # 创建输出目录
    os.makedirs(output_folder, exist_ok=True)
    
    # 遍历所有MP3文件
    for filename in os.listdir(input_folder):
        if filename.endswith(".mp3") and (file_pattern is None or filename == file_pattern):
            input_path = os.path.join(input_folder, filename)
            audio = AudioSegment.from_mp3(input_path)
            
            # 计算总时长（毫秒转秒）
            total_duration = len(audio) // 1000
            print(f"正在处理: {filename} (总时长: {total_duration}秒)")
            
            # 分割音频
            for i, start in enumerate(range(0, total_duration, segment_length)):
                end = min(start + segment_length, total_duration)
                segment = audio[start*1000:end*1000]
                
                # 导出为WAV格式（兼容语音识别API）
                output_filename = f"{os.path.splitext(filename)[0]}_part{i+1:03d}.wav"
                output_path = os.path.join(output_folder, output_filename)
                segment.export(
                    output_path,
                    format="wav",
                    parameters=["-ac", "1", "-ar", "16000"]  # 单声道，16kHz采样率
                )
                print(f"  ├─ 分割完成: {output_filename}")

def convert_mp3_to_txt(mp3_folder, output_folder, max_retries=3, max_workers=4, 
                      use_jianying_first=False, use_kuaishou=False, use_bcut=False,
                      format_text=True, include_timestamps=True):
    """
    批量将MP3文件转为文本，使用ASR服务轮询
    
    Args:
        mp3_folder: MP3文件所在文件夹
        output_folder: 输出结果文件夹
        max_retries: 最大重试次数
        max_workers: 线程池工作线程数
        use_jianying_first: 是否优先使用剪映ASR
        use_kuaishou: 是否使用快手ASR
        use_bcut: 是否使用B站ASR
        format_text: 是否格式化输出文本以提高可读性
        include_timestamps: 是否在格式化文本中包含时间戳
    """
    # 注册ASR服务
    register_asr_services(use_jianying_first, use_kuaishou, use_bcut)
    
    os.makedirs(output_folder, exist_ok=True)
    
    # 记录文件路径
    processed_record_file = os.path.join(output_folder, "processed_audio_files.json")
    processed_files = load_processed_records(processed_record_file)
    
    # 创建临时目录用于存储分割的音频片段
    temp_dir = tempfile.mkdtemp()
    
    try:
        for filename in os.listdir(mp3_folder):
            if filename.endswith(".mp3"):
                input_path = os.path.join(mp3_folder, filename)
                
                # 检查文件是否已处理
                if input_path in processed_files:
                    print(f"跳过 {filename}（已处理）")
                    continue
                
                # 检查文件名是否包含"_recognized"标记
                if "_recognized" in filename:
                    print(f"跳过 {filename}（已标记为已识别）")
                    continue
                
                try:
                    temp_segments_dir = os.path.join(temp_dir, "segments")
                    
                    # 分割音频为较小片段
                    print(f"正在分割 {filename} 为小片段...")
                    split_audio(
                        input_folder=os.path.dirname(input_path),
                        output_folder=temp_segments_dir,
                        segment_length=30,  # 调小片段长度，确保不超过10MB
                        file_pattern=filename  # 只处理当前文件
                    )
                    
                    # 使用字典存储每个片段的识别结果，确保按顺序合并
                    segment_results = {}
                    
                    # 处理每个分割的片段
                    segment_files = sorted([f for f in os.listdir(temp_segments_dir) 
                                          if f.startswith(os.path.splitext(filename)[0])])
                    
                    print(f"开始多线程识别 {len(segment_files)} 个音频片段...")
                    
                    # 使用线程池并行处理音频片段
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # 创建任务字典，映射片段索引和对应的Future对象
                        future_to_segment = {
                            executor.submit(recognize_audio, 
                                           os.path.join(temp_segments_dir, segment_file), 
                                           'zh-CN', 
                                           2,
                                           use_jianying_first,
                                           use_kuaishou,
                                           use_bcut): 
                            (i, segment_file)
                            for i, segment_file in enumerate(segment_files)
                        }
                        
                        # 收集结果
                        for future in concurrent.futures.as_completed(future_to_segment):
                            i, segment_file = future_to_segment[future]
                            try:
                                text = future.result()
                                if text:
                                    segment_results[i] = text
                                    print(f"  ├─ 成功识别: {segment_file}")
                                else:
                                    print(f"  ├─ 识别失败: {segment_file}")
                            except Exception as exc:
                                print(f"  ├─ 识别出错: {segment_file} - {str(exc)}")
                    
                    # 统计识别结果
                    success_count = len(segment_results)
                    fail_count = len(segment_files) - success_count
                    
                    # 集中重试失败的片段
                    if fail_count > 0:
                        print(f"\n开始重试 {fail_count} 个失败的片段...")
                        failed_segments = [(i, segment_files[i]) for i in range(len(segment_files)) if i not in segment_results]
                        
                        for retry_round in range(1, max_retries + 1):
                            if not failed_segments:
                                break
                                
                            print(f"第 {retry_round} 轮重试 ({len(failed_segments)} 个片段):")
                            still_failed = []
                            
                            # 对失败的片段进行多线程重试
                            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as retry_executor:
                                future_to_failed = {
                                    retry_executor.submit(recognize_audio, 
                                                         os.path.join(temp_segments_dir, segment_file), 
                                                         'zh-CN', 
                                                         1,
                                                         use_jianying_first,
                                                         use_kuaishou,
                                                         use_bcut): 
                                    (idx, segment_file)
                                    for idx, segment_file in failed_segments
                                }
                                
                                for future in concurrent.futures.as_completed(future_to_failed):
                                    idx, segment_file = future_to_failed[future]
                                    try:
                                        text = future.result()
                                        if text:
                                            segment_results[idx] = text
                                            print(f"  ├─ 重试成功: {segment_file}")
                                        else:
                                            still_failed.append((idx, segment_file))
                                            print(f"  ├─ 重试失败: {segment_file}")
                                    except Exception as exc:
                                        still_failed.append((idx, segment_file))
                                        print(f"  ├─ 重试出错: {segment_file} - {str(exc)}")
                            
                            failed_segments = still_failed
                    
                    # 按顺序合并所有文本片段
                    all_text = []
                    all_timestamps = []
                    for i in range(len(segment_files)):
                        if i in segment_results:
                            all_text.append(segment_results[i])
                            # 简单估算时间戳，每个片段30秒
                            all_timestamps.append({
                                'start': i * 30,
                                'end': (i + 1) * 30
                            })
                        else:
                            all_text.append("[无法识别的音频片段]")
                            all_timestamps.append({
                                'start': i * 30,
                                'end': (i + 1) * 30
                            })
                    
                    # 格式化文本以提高可读性
                    if format_text:
                        full_text = TextFormatter.format_segment_text(
                            all_text, 
                            timestamps=all_timestamps if include_timestamps else None,
                            include_timestamps=include_timestamps
                        )
                    else:
                        # 如果不格式化，仍使用原来的合并方式
                        full_text = " ".join(all_text)
                    
                    output_file = os.path.join(output_folder, filename.replace(".mp3", ".txt"))
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(full_text)
                    
                    success_count = len(segment_results)
                    fail_count = len(segment_files) - success_count
                    print(f"✅ {filename} 转换完成: 成功识别 {success_count}/{len(segment_files)} 片段" + 
                          (f", 失败 {fail_count} 片段" if fail_count > 0 else ""))
                    
                    # 重命名原文件，添加"_recognized"标识
                    base_name = os.path.basename(input_path)
                    dir_name = os.path.dirname(input_path)
                    name, ext = os.path.splitext(base_name)
                    new_path = os.path.join(dir_name, f"{name}_recognized{ext}")
                    os.rename(input_path, new_path)
                    
                    # 更新已处理记录
                    processed_files[input_path] = {
                        "processed_time": time.strftime("%Y-%m-%-%d %H:%M:%S"),
                        "new_path": new_path,
                        "output_file": output_file
                    }
                    save_processed_records(processed_record_file, processed_files)
                    
                    print(f"✅ 已重命名文件为: {os.path.basename(new_path)}")
                    
                except Exception as e:
                    print(f"❌ {filename} 失败: {str(e)}")
        
        # 所有识别完成后，显示服务使用统计
        stats = asr_selector.get_service_stats()
        print("\nASR服务使用统计:")
        for name, stat in stats.items():
            print(f"  {name}: 使用次数 {stat['count']}, 成功率 {stat['success_rate']}, 可用状态: {'可用' if stat['available'] else '禁用'}")
                    
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    # 修改这几个路径即可
    convert_mp3_to_txt(
        mp3_folder = r"D:\download",  # 如：r"C:\Users\用户名\Music"
        output_folder = r"D:\download\dest",  # 如：r"D:\output"
        max_retries = 3,  # 集中重试的最大次数
        max_workers = 4,   # 线程池中的线程数，可根据CPU配置调整
        use_jianying_first = True,  # 设置为True表示优先使用剪映API进行识别
        use_kuaishou = True,   # 设置为True表示使用快手API进行识别
        use_bcut = True,  # 设置为True表示优先使用B站ASR进行识别（优先级最高）
        format_text = True,  # 格式化输出文本，提高可读性
        include_timestamps = True  # 在格式化文本中包含时间戳
    )