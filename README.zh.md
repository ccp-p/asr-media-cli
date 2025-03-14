# 音频处理工具

一个强大的音频处理工具，支持将音频和视频文件转换为文本。

## 功能特点

- 支持多种音频和视频格式
- 自动提取视频中的音频
- 智能分段处理长音频
- 多ASR服务轮询和自动重试
- 实时进度显示
- 文件监控模式
- 灵活的配置选项

## 安装

1. 克隆仓库：
```bash
git clone [repository-url]
cd segement_audio
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装FFmpeg (用于视频处理)：
- Windows: 从 https://ffmpeg.org/download.html 下载并添加到系统PATH
- Linux: `sudo apt-get install ffmpeg`
- MacOS: `brew install ffmpeg`

## 使用方法

### 命令行使用

基本用法：
```bash
python main.py -m /path/to/media -o /path/to/output
```

参数说明：
- `-c, --config`: 配置文件路径 (默认: config.json)
- `-m, --media-folder`: 媒体文件夹路径
- `-o, --output-folder`: 输出文件夹路径
- `-w, --watch`: 启用监听模式
- `--no-video`: 不处理视频文件
- `--extract-only`: 仅提取音频
- `--no-progress`: 不显示进度条
- `--no-timestamps`: 不包含时间戳
- `--debug`: 启用调试模式

### 配置文件

可以通过config.json配置以下选项：

```json
{
    "media_folder": "./media",          # 媒体文件夹路径
    "output_folder": "./output",        # 输出文件夹路径
    "max_retries": 3,                   # 最大重试次数
    "max_workers": 4,                   # 最大并发工作线程数
    "use_jianying_first": true,         # 优先使用剪映ASR
    "use_kuaishou": true,              # 使用快手ASR
    "use_bcut": true,                  # 使用必剪ASR
    "format_text": true,               # 格式化输出文本
    "include_timestamps": true,         # 包含时间戳
    "show_progress": true,             # 显示进度条
    "process_video": true,             # 处理视频文件
    "extract_audio_only": false,        # 仅提取音频
    "watch_mode": false,               # 监听模式
    "segment_length": 30,              # 音频片段长度(秒)
    "max_segment_length": 2000,        # 最大文本段落长度
    "min_segment_length": 10,          # 最小文本段落长度
    "retry_delay": 1.0,               # 重试延迟时间(秒)
    "log_level": "INFO",              # 日志级别
    "log_file": "./output/audio_processing.log"  # 日志文件路径
}
```

### 示例

1. 基本使用：
```bash
python main.py -m ./media -o ./output
```

2. 监听模式：
```bash
python main.py -m ./media -o ./output -w
```

3. 使用自定义配置：
```bash
python main.py -c my_config.json
```

4. 仅提取音频：
```bash
python main.py -m ./media -o ./output --extract-only
```

## 输出格式

文本输出示例：
```
# example.mp3
# 处理时间: 2023-12-25 14:30:00
# 总片段数: 10
# 成功识别: 10

[00:00 - 00:30] 第一段转写文本...

[00:30 - 01:00] 第二段转写文本...
```

## 错误处理

- 程序会自动重试失败的识别任务
- 详细的错误日志记录
- 处理过程可随时中断并保存进度
- 支持断点续传

## 注意事项

1. 需要安装FFmpeg才能处理视频文件
2. 建议使用Python 3.7+
3. 确保有足够的磁盘空间用于临时文件
4. 监听模式会持续运行直到手动停止

## 许可证

MIT License
