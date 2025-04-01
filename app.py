from flask import Flask, render_template, jsonify, request
import os
import sys
import json
import logging

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入核心功能模块
from core.utils import load_json_file, save_json_file, LogConfig
from core.asr_manager import ASRManager
from audio_tools.core.audio_extractor import AudioExtractor
from audio_tools.processing.transcription_processor import TranscriptionProcessor
from audio_tools.processing.file_processor import FileProcessor
import os
print(os.getcwd())
app = Flask(__name__)

# 全局设置
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# 加载配置
def load_config():
    default_config = {
        "media_folder": "D:/download/",
        "output_folder": "D:/download/output/",
        "temp_segments_dir": "D:/download/temp_segments/",
        "use_jianying_first": False,
        "use_kuaishou": True, 
        "use_bcut": True,
        "process_video": True,
        "extract_audio_only": False,
        "format_text": True,
        "include_timestamps": True,
        "max_part_time": 20,
        "log_level": "NORMAL",
        "watch": True,
        "additional_folders": ["D:/download/dest/"]
    }
    
    config = load_json_file(CONFIG_FILE)
    if not config:
        config = default_config
        save_json_file(CONFIG_FILE, config)
        
    return config

# API路由
@app.route('/')
def index():
    return render_template('/index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    config = load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    config = request.json
    save_json_file(CONFIG_FILE, config)
    return jsonify({"status": "success"})

@app.route('/api/asr-stats', methods=['GET'])
def get_asr_stats():
    # 创建临时ASR管理器来获取统计数据
    config = load_config()
    asr_settings = config.get("asr_settings", {})
    
    asr_manager = ASRManager(
        use_jianying_first=asr_settings.get("use_jianying_first", False),
        use_kuaishou=asr_settings.get("use_kuaishou", True),
        use_bcut=asr_settings.get("use_bcut", True)
    )
    
    stats = asr_manager.get_service_stats()
    return jsonify(stats)

@app.route('/api/processed-files', methods=['GET'])
def get_processed_files():
    config = load_config()
    output_folder = config.get("output_folder", "output")
    
    processed_record_file = os.path.join(output_folder, "processed_audio_files.json")
    processed_files = load_json_file(processed_record_file)
    
    # 格式化为前端所需的数据结构
    result = []
    for filepath, data in processed_files.items():
        result.append({
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "last_processed_time": data.get("last_processed_time", "未知"),
            "status": "完成" if data.get("completed", False) else "部分完成",
            "parts": len(data.get("parts", {})),
            "total_parts": data.get("total_parts", 1)
        })
    
    return jsonify(result)

@app.route('/api/start-processing', methods=['POST'])
def start_processing():
    try:
        config = load_config()
        file_path = request.json.get("filepath")
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({"status": "error", "message": "文件不存在"}), 400
            
        # 创建处理实例并处理文件
        media_folder = config.get("media_folder", "media")
        output_folder = config.get("output_folder", "output")
        temp_segments_dir = config.get("temp_segments_dir", "temp")
        
        # 创建必要的目录
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(temp_segments_dir, exist_ok=True)
        
        # 创建处理实例
        asr_settings = config.get("asr_settings", {})
        process_settings = config.get("process_settings", {})
        
        # 设置日志级别
        log_level = process_settings.get("log_level", "NORMAL")
        if log_level == "QUIET":
            LogConfig.set_log_mode(LogConfig.QUIET)
        elif log_level == "VERBOSE":
            LogConfig.set_log_mode(LogConfig.VERBOSE)
        else:
            LogConfig.set_log_mode(LogConfig.NORMAL)
        
        # 创建处理组件
        audio_extractor = AudioExtractor(temp_segments_dir)
        
        asr_manager = ASRManager(
            use_jianying_first=asr_settings.get("use_jianying_first", False),
            use_kuaishou=asr_settings.get("use_kuaishou", True),
            use_bcut=asr_settings.get("use_bcut", True)
        )
        
        transcription_processor = TranscriptionProcessor(
            asr_manager=asr_manager,
            temp_segments_dir=temp_segments_dir,
            max_workers=3
        )
        
        # 创建文件处理器
        file_processor = FileProcessor(
            media_folder=media_folder,
            output_folder=output_folder,
            temp_segments_dir=temp_segments_dir,
            transcription_processor=transcription_processor,
            audio_extractor=audio_extractor,
            process_video=process_settings.get("process_video", True),
            extract_audio_only=process_settings.get("extract_audio_only", False),
            format_text=process_settings.get("format_text", True),
            include_timestamps=process_settings.get("include_timestamps", True),
            max_part_time=process_settings.get("max_part_time", 20)
        )
        
        # 异步处理文件(实际项目中应该使用后台任务)
        import threading
        def process_in_background():
            try:
                file_processor.process_file(file_path)
            except Exception as e:
                logging.error(f"处理文件时出错: {str(e)}")
        
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "success", "message": "开始处理文件"})
        
    except Exception as e:
        logging.error(f"启动处理失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/toggle-monitor', methods=['POST'])
def toggle_monitor():
    try:
        action = request.json.get("action", "start")
        config = load_config()
        
        # 更新监控设置
        if action == "start":
            config["watch"] = True
        else:
            config["watch"] = False
            
        save_json_file(CONFIG_FILE, config)
        
        # 实际启动/停止监控的逻辑应该在这里实现
        # 由于监控需要持续运行，实际项目中应该使用后台服务
        
        return jsonify({"status": "success", "action": action})
        
    except Exception as e:
        logging.error(f"切换监控状态失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)