"""
功能测试工具
提供命令行工具来测试单个功能点
"""
import os
import sys
import argparse
import logging
import json
import pdb  # 添加Python调试器
from typing import List, Dict, Any

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dependency_container import container
from audio_tools.processing.transcription_processor import TranscriptionProcessor
from audio_tools.processing.text_processor import TextProcessor
from audio_tools.core.audio_extractor import AudioExtractor
from asr.jianying_asr import JianYingASR
from asr.kuaishou_asr import KuaiShouASR
from asr.bcut_asr import BcutASR


def setup_logging(level=logging.INFO):
    """设置日志"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def register_dependencies():
    """注册依赖"""
    # 注册ASR服务
    from core.asr_manager import ASRManager
    container.register('asr_manager', ASRManager(
        use_jianying_first=True,
        use_kuaishou=True,
        use_bcut=True
    ))
    
    # 注册其他基本组件
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    config = {
        'temp_dir': temp_dir,
        'temp_segments_dir': os.path.join(temp_dir, 'segments'),
        'output_dir': os.path.join(temp_dir, 'output'),
        'max_workers': 4,
        'max_retries': 3
    }
    
    container.register('config', config)
    
    # 创建临时片段目录
    os.makedirs(config['temp_segments_dir'], exist_ok=True)
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # 注册音频提取器
    container.register('audio_extractor', AudioExtractor(
        temp_segments_dir=config['temp_segments_dir']
    ))
    
    # 注册转录处理器
    container.register('transcription_processor', TranscriptionProcessor(
        asr_manager=container.get('asr_manager'),
        temp_segments_dir=config['temp_segments_dir'],
        max_workers=config['max_workers'],
        max_retries=config['max_retries']
    ))
    
    # 注册文本处理器
    container.register('text_processor', TextProcessor(
        output_folder=config['output_dir']
    ))


def test_asr_service(audio_path: str, service_name: str = 'all'):
    """测试ASR服务"""
    if not os.path.exists(audio_path):
        print(f"错误: 文件不存在: {audio_path}")
        return
        
    print(f"\n正在测试ASR服务: {service_name}, 文件: {audio_path}")
    
    if service_name == 'jianying' or service_name == 'all':
        try:
            print("\n--- 测试剪映ASR ---")
            asr = JianYingASR(audio_path)
            result = asr.get_result()
            print(f"识别结果: 共 {len(result)} 个片段")
            for i, seg in enumerate(result[:3]):
                print(f"片段 {i+1}: {seg.start_time}-{seg.end_time}s: {seg.text}")
            if len(result) > 3:
                print(f"... 还有 {len(result)-3} 个片段 ...")
        except Exception as e:
            print(f"剪映ASR测试失败: {str(e)}")
    
    if service_name == 'kuaishou' or service_name == 'all':
        try:
            print("\n--- 测试快手ASR ---")
            asr = KuaiShouASR(audio_path)
            result = asr.get_result()
            print(f"识别结果: 共 {len(result)} 个片段")
            for i, seg in enumerate(result[:3]):
                print(f"片段 {i+1}: {seg.start_time}-{seg.end_time}s: {seg.text}")
            if len(result) > 3:
                print(f"... 还有 {len(result)-3} 个片段 ...")
        except Exception as e:
            print(f"快手ASR测试失败: {str(e)}")
    
    if service_name == 'bcut' or service_name == 'all':
        try:
            print("\n--- 测试必剪ASR ---")
            asr = BcutASR(audio_path)
            result = asr.get_result()
            print(f"识别结果: 共 {len(result)} 个片段")
            for i, seg in enumerate(result[:3]):
                print(f"片段 {i+1}: {seg.start_time}-{seg.end_time}s: {seg.text}")
            if len(result) > 3:
                print(f"... 还有 {len(result)-3} 个片段 ...")
        except Exception as e:
            print(f"必剪ASR测试失败: {str(e)}")


def test_audio_extract(audio_or_video_path: str):
    """测试音频提取"""
    if not os.path.exists(audio_or_video_path):
        print(f"错误: 文件不存在: {audio_or_video_path}")
        return
        
    print(f"\n正在测试音频提取: {audio_or_video_path}")
    
    try:
        audio_extractor = container.get('audio_extractor')
        
        # 检查是否是视频文件
        _, ext = os.path.splitext(audio_or_video_path)
        if ext.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            print("检测到视频文件，提取音频...")
            output_dir = container.get('config')['output_dir']
            audio_path, is_new = audio_extractor.extract_audio_from_video(
                audio_or_video_path, output_dir
            )
            print(f"音频提取{'成功' if audio_path else '失败'}: {audio_path}")
            if is_new:
                print("新创建的音频文件")
            else:
                print("使用已存在的音频文件")
                
            if audio_path:
                audio_or_video_path = audio_path
        
        # 分割音频
        print("\n分割音频为片段...")
        segment_files = audio_extractor.split_audio_file(audio_or_video_path)
        print(f"分割结果: 共 {len(segment_files)} 个片段")
        for i, segment in enumerate(segment_files[:5]):
            print(f"片段 {i+1}: {os.path.basename(segment)}")
        if len(segment_files) > 5:
            print(f"... 还有 {len(segment_files)-5} 个片段 ...")
            
        return segment_files
    except Exception as e:
        print(f"音频提取测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def test_transcription(segment_files: List[str]):
    """测试音频转录"""
    if not segment_files:
        print("错误: 没有片段文件")
        return
        
    print(f"\n正在测试音频转录: {len(segment_files)} 个片段")
    
    try:
        transcription_processor = container.get('transcription_processor')
        
        # 处理片段
        print("处理音频片段...")
        segment_results = transcription_processor.process_audio_segments(segment_files)
        
        # 输出结果
        successful = sum(1 for r in segment_results.values() if r)
        print(f"\n转录结果: 共 {len(segment_results)} 个片段, 成功 {successful} 个")
        
        for i, (idx, result) in enumerate(segment_results.items()):
            if i >= 5:
                break
            status = "成功" if result else "失败"
            text = result[:50] + "..." if result and len(result) > 50 else result
            print(f"片段 {idx+1}: {status} - {text}")
        
        if len(segment_results) > 5:
            print(f"... 还有 {len(segment_results)-5} 个结果 ...")
            
        # 重试失败的片段
        failed = len(segment_results) - successful
        if failed > 0:
            print(f"\n重试 {failed} 个失败片段...")
            segment_results = transcription_processor.retry_failed_segments(
                segment_files, segment_results
            )
            
            # 更新成功数量
            successful = sum(1 for r in segment_results.values() if r)
            print(f"重试后结果: 共 {len(segment_results)} 个片段, 成功 {successful} 个")
        
        return segment_results
    except Exception as e:
        print(f"转录测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}


def test_text_processing(segment_files: List[str], segment_results: Dict[int, str]):
    """测试文本处理"""
    if not segment_files or not segment_results:
        print("错误: 没有片段文件或转录结果")
        return
        
    print(f"\n正在测试文本处理: {len(segment_results)} 个结果")
    
    try:
        text_processor = container.get('text_processor')
        
        # 准备元数据
        metadata = {
            "原始文件": "测试文件",
            "处理时间": "2023-01-01 12:00:00",
            "识别成功率": f"{sum(1 for r in segment_results.values() if r)}/{len(segment_results)} 片段"
        }
        
        # 处理文本
        print("准备结果文本...")
        result_text = text_processor.prepare_result_text(
            segment_files=segment_files,
            segment_results=segment_results,
            metadata=metadata
        )
        
        # 保存文件
        output_path = os.path.join(
            container.get('config')['output_dir'], 
            "test_output.txt"
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result_text)
            
        print(f"文本处理完成，已保存到: {output_path}")
        print(f"\n结果预览:\n{result_text[:500]}")
        if len(result_text) > 500:
            print("...")
    except Exception as e:
        print(f"文本处理测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="音频处理功能测试工具")
    
    parser.add_argument('file', help="要处理的音频或视频文件路径")
    
    parser.add_argument('--feature', choices=['asr', 'extract', 'transcribe', 'text', 'full'],
                        default='full', help="要测试的功能点")
    
    parser.add_argument('--asr-service', choices=['jianying', 'kuaishou', 'bcut', 'all'],
                        default='all', help="使用的ASR服务")
    
    parser.add_argument('--debug', action='store_true', help="启用调试模式")
    
    # 添加断点调试参数
    parser.add_argument('--pdb', action='store_true', help="启用断点调试")
    
    args = parser.parse_args()
    
    # 设置日志级别
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    
    # 注册依赖
    register_dependencies()
    
    # 如果启用了断点调试，在测试开始前设置断点
    if args.pdb:
        print("\n===== PDB调试模式已启用 =====")
        print("常用命令:")
        print("- c 或 continue : 继续执行程序直到下一个断点")
        print("- n 或 next    : 执行当前行，不进入函数内部")
        print("- s 或 step    : 执行当前行，并进入函数内部")
        print("- p 变量名      : 打印变量的值")
        print("- q 或 quit    : 退出调试器")
        print("- h 或 help    : 显示更多帮助")
        print("============================\n")
        pdb.set_trace()
    
    # 根据选择测试不同功能
    if args.feature == 'asr':
        test_asr_service(args.file, args.asr_service)
    elif args.feature == 'extract':
        test_audio_extract(args.file)
    elif args.feature == 'transcribe':
        segments = test_audio_extract(args.file)
        
        # 在开始转写前设置断点（可选）
        if args.pdb:
            print("\n准备开始转写处理，已在转写前设置断点")
            print("可使用 p segments 查看分割结果")
            print("使用 n 继续执行下一行")
            pdb.set_trace()
            
        if segments:
            test_transcription(segments)
    elif args.feature == 'text':
        segments = test_audio_extract(args.file)
        if segments:
            results = test_transcription(segments)
            if results:
                test_text_processing(segments, results)
    else:  # full
        segments = test_audio_extract(args.file)
        if segments:
            results = test_transcription(segments)
            if results:
                test_text_processing(segments, results)


if __name__ == '__main__':
    main()
