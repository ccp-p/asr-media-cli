import os
import tempfile
import shutil
import time
import json
import concurrent.futures
from pathlib import Path
import logging
import requests
import sys
import signal
from pydub import AudioSegment
from datetime import datetime, timedelta

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

def format_time_duration(seconds):
    """
    将秒数格式化为更易读的时间格式 (HH:MM:SS)
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

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
    # 记录总体开始时间
    total_start_time = time.time()
    processed_files_count = 0
    
    # 注册ASR服务
    register_asr_services(use_jianying_first, use_kuaishou, use_bcut)
    
    os.makedirs(output_folder, exist_ok=True)
    
    # 记录文件路径
    processed_record_file = os.path.join(output_folder, "processed_audio_files.json")
    processed_files = load_processed_records(processed_record_file)
    
    # 创建临时目录用于存储分割的音频片段
    temp_dir = tempfile.mkdtemp()
    # 确保segments目录存在
    temp_segments_dir = os.path.join(temp_dir, "segments")
    os.makedirs(temp_segments_dir, exist_ok=True)
    
    # 定义中断处理函数
    interrupt_received = False
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    
    def handle_interrupt(sig, frame):
        nonlocal interrupt_received
        print("\n\n⚠️ 接收到中断信号，正在安全终止程序...\n稍等片刻，正在保存已处理的数据...\n")
        interrupt_received = True
        # 不立即退出，允许程序完成当前处理和清理
    
    # 设置中断处理
    signal.signal(signal.SIGINT, handle_interrupt)
    
    try:
        for filename in os.listdir(mp3_folder):
            if interrupt_received:
                print("程序被用户中断，停止处理新文件。")
                break
                
            if filename.endswith(".mp3"):
                input_path = os.path.join(mp3_folder, filename)
                
                # 检查文件是否已处理
                if input_path in processed_files:
                    print(f"跳过 {filename}（已处理）")
                    continue
                
                try:
                    # 记录单个文件处理开始时间
                    file_start_time = time.time()
                    
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
                        
                        # 收集结果，并添加中断检查
                        try:
                            for future in concurrent.futures.as_completed(future_to_segment):
                                if interrupt_received:
                                    print("检测到中断，正在取消剩余任务...")
                                    executor.shutdown(wait=False, cancel_futures=True)
                                    break
                                    
                                i, segment_file = future_to_segment[future]
                                try:
                                    text = future.result(timeout=60)  # 添加超时以避免无限等待
                                    if text:
                                        segment_results[i] = text
                                        print(f"  ├─ 成功识别: {segment_file}")
                                    else:
                                        print(f"  ├─ 识别失败: {segment_file}")
                                except concurrent.futures.TimeoutError:
                                    print(f"  ├─ 识别超时: {segment_file}")
                                except Exception as exc:
                                    print(f"  ├─ 识别出错: {segment_file} - {str(exc)}")
                        except KeyboardInterrupt:
                            print("检测到用户中断，正在取消剩余任务...")
                            executor.shutdown(wait=False, cancel_futures=True)
                            interrupt_received = True
                    
                    # 如果处理被中断，保存当前结果并退出
                    if interrupt_received:
                        print("处理被中断，尝试保存已完成的识别结果...")
                        # 继续执行以下代码，保存已处理的结果
                    
                    # 统计识别结果
                    success_count = len(segment_results)
                    fail_count = len(segment_files) - success_count
                    
                    # 如果没有中断并且有失败的片段，则进行重试
                    if not interrupt_received and fail_count > 0:
                        print(f"\n开始重试 {fail_count} 个失败的片段...")
                        failed_segments = [(i, segment_files[i]) for i in range(len(segment_files)) if i not in segment_results]
                        
                        for retry_round in range(1, max_retries + 1):
                            if not failed_segments or interrupt_received:
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
                                
                                try:
                                    for future in concurrent.futures.as_completed(future_to_failed):
                                        if interrupt_received:
                                            print("检测到中断，正在取消剩余重试任务...")
                                            retry_executor.shutdown(wait=False, cancel_futures=True)
                                            break
                                            
                                        idx, segment_file = future_to_failed[future]
                                        try:
                                            text = future.result(timeout=60)
                                            if text:
                                                segment_results[idx] = text
                                                print(f"  ├─ 重试成功: {segment_file}")
                                            else:
                                                still_failed.append((idx, segment_file))
                                                print(f"  ├─ 重试失败: {segment_file}")
                                        except concurrent.futures.TimeoutError:
                                            still_failed.append((idx, segment_file))
                                            print(f"  ├─ 重试超时: {segment_file}")
                                        except Exception as exc:
                                            still_failed.append((idx, segment_file))
                                            print(f"  ├─ 重试出错: {segment_file} - {str(exc)}")
                                except KeyboardInterrupt:
                                    print("检测到用户中断，正在取消剩余重试任务...")
                                    retry_executor.shutdown(wait=False, cancel_futures=True)
                                    interrupt_received = True
                            
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
                            include_timestamps=include_timestamps,
                            separate_segments=True  # 启用分片分隔
                        )
                    else:
                        # 如果不格式化，仍使用原来的合并方式
                        full_text = "\n\n".join([text for text in all_text if text and text != "[无法识别的音频片段]"])
                    
                    output_file = os.path.join(output_folder, filename.replace(".mp3", ".txt"))
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(full_text)
                    
                    success_count = len(segment_results)
                    fail_count = len(segment_files) - success_count
                    
                    # 计算并显示单个文件处理时长
                    file_duration = time.time() - file_start_time
                    formatted_duration = format_time_duration(file_duration)
                    
                    status = "（部分完成 - 已中断）" if interrupt_received else ""
                    print(f"✅ {filename} 转换完成{status}: 成功识别 {success_count}/{len(segment_files)} 片段" + 
                          (f", 失败 {fail_count} 片段" if fail_count > 0 else "") + 
                          f" - 耗时: {formatted_duration}")
                    
                    # 不再重命名MP3文件，只更新处理记录
                    
                    # 更新已处理记录
                    processed_files[input_path] = {
                        "processed_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "output_file": output_file,
                        "interrupted": interrupt_received,
                        "success_rate": f"{success_count}/{len(segment_files)}"
                    }
                    save_processed_records(processed_record_file, processed_files)
                    
                    print(f"✅ 文件已处理完成并记录: {os.path.basename(input_path)}")
                    
                    # 更新处理文件计数
                    processed_files_count += 1
                    
                    if interrupt_received:
                        print("用户中断处理，退出处理循环")
                        break
                        
                except Exception as e:
                    print(f"❌ {filename} 失败: {str(e)}")
                    if interrupt_received:
                        break
        
        # 计算并显示总处理时长
        total_duration = time.time() - total_start_time
        formatted_total_duration = format_time_duration(total_duration)
        
        # 所有识别完成后，显示服务使用统计
        stats = asr_selector.get_service_stats()
        print("\nASR服务使用统计:")
        for name, stat in stats.items():
            print(f"  {name}: 使用次数 {stat['count']}, 成功率 {stat['success_rate']}, 可用状态: {'可用' if stat['available'] else '禁用'}")
                    
        # 打印总结信息
        print(f"\n总结: 处理了 {processed_files_count} 个文件, 总耗时: {formatted_total_duration}")
        # 显示平均每个文件处理时长
        if processed_files_count > 0:
            avg_time = total_duration / processed_files_count
            formatted_avg_time = format_time_duration(avg_time)
            print(f"平均每个文件处理时长: {formatted_avg_time}")
            
    finally:
        # 恢复原始信号处理程序
        signal.signal(signal.SIGINT, original_sigint_handler)
        
        # 清理临时文件
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"✓ 临时文件已清理: {temp_dir}")
        except Exception as e:
            print(f"⚠️ 清理临时文件失败: {str(e)}")
        
        if interrupt_received:
            print("\n程序已安全终止，已保存处理进度。您可以稍后继续处理剩余文件。")

if __name__ == "__main__":
    # 添加异常处理
    try:
        # 修改这几个路径即可
        convert_mp3_to_txt(
            mp3_folder = r"D:\download",  # 如：r"C:\Users\用户名\Music"
            output_folder = r"D:\download\dest",  # 如：r"D:\output"
            max_retries = 3,  # 集中重试的最大次数
            max_workers = 6,   # 线程池中的线程数，可根据CPU配置调整
            use_jianying_first = True,  # 设置为True表示优先使用剪映API进行识别
            use_kuaishou = True,   # 设置为True表示使用快手API进行识别
            use_bcut = True,  # 设置为True表示优先使用B站ASR进行识别（优先级最高）
            format_text = True,  # 格式化输出文本，提高可读性
            include_timestamps = True  # 在格式化文本中包含时间戳
        )
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"\n程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n程序执行完毕。")