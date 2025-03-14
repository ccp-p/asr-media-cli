# Audio Processing Tool

A powerful audio processing tool that converts audio and video files to text.

## Features

- Support for multiple audio and video formats
- Automatic audio extraction from video
- Smart segmentation for long audio files
- Multiple ASR service polling with auto-retry
- Real-time progress display
- File monitoring mode
- Flexible configuration options

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd segement_audio
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg (for video processing):
- Windows: Download from https://ffmpeg.org/download.html and add to system PATH
- Linux: `sudo apt-get install ffmpeg`
- MacOS: `brew install ffmpeg`

## Usage

### Command Line Interface

Basic usage:
```bash
python main.py -m /path/to/media -o /path/to/output
```

Arguments:
- `-c, --config`: Configuration file path (default: config.json)
- `-m, --media-folder`: Media folder path
- `-o, --output-folder`: Output folder path
- `-w, --watch`: Enable watch mode
- `--no-video`: Don't process video files
- `--extract-only`: Only extract audio
- `--no-progress`: Don't show progress bars
- `--no-timestamps`: Don't include timestamps
- `--debug`: Enable debug mode

### Configuration File

Configure options in config.json:

```json
{
    "media_folder": "./media",          # Media folder path
    "output_folder": "./output",        # Output folder path
    "max_retries": 3,                   # Maximum retry attempts
    "max_workers": 4,                   # Maximum concurrent worker threads
    "use_jianying_first": true,         # Prioritize Jianying ASR
    "use_kuaishou": true,              # Use Kuaishou ASR
    "use_bcut": true,                  # Use Bcut ASR
    "format_text": true,               # Format output text
    "include_timestamps": true,         # Include timestamps
    "show_progress": true,             # Show progress bars
    "process_video": true,             # Process video files
    "extract_audio_only": false,        # Only extract audio
    "watch_mode": false,               # Watch mode
    "segment_length": 30,              # Audio segment length (seconds)
    "max_segment_length": 2000,        # Maximum text segment length
    "min_segment_length": 10,          # Minimum text segment length
    "retry_delay": 1.0,               # Retry delay (seconds)
    "log_level": "INFO",              # Logging level
    "log_file": "./output/audio_processing.log"  # Log file path
}
```

### Examples

1. Basic usage:
```bash
python main.py -m ./media -o ./output
```

2. Watch mode:
```bash
python main.py -m ./media -o ./output -w
```

3. With custom config:
```bash
python main.py -c my_config.json
```

4. Extract audio only:
```bash
python main.py -m ./media -o ./output --extract-only
```

## Output Format

Text output example:
```
# example.mp3
# Processed: 2023-12-25 14:30:00
# Total segments: 10
# Successfully transcribed: 10

[00:00 - 00:30] First transcribed text segment...

[00:30 - 01:00] Second transcribed text segment...
```

## Error Handling

- Automatic retry of failed recognition tasks
- Detailed error logging
- Process can be interrupted and progress saved
- Supports resuming from interruption

## Notes

1. FFmpeg is required for video processing
2. Python 3.7+ recommended
3. Ensure sufficient disk space for temporary files
4. Watch mode runs until manually stopped

## License

MIT License

# 依赖管理指南

## 冻结依赖

要冻结项目依赖，请运行：

```bash
# 将依赖冻结到默认的requirements.txt文件
python freeze_deps.py freeze

# 或指定输出文件
python freeze_deps.py freeze --file requirements_dev.txt
```

## 安装依赖

要从冻结的依赖文件中安装包：

```bash
# 从默认的requirements.txt文件安装
python freeze_deps.py install

# 或从指定文件安装
python freeze_deps.py install --file requirements_dev.txt
```

## 手动方法

你也可以直接使用pip命令：

```bash
# 冻结依赖
pip freeze > requirements.txt

# 安装依赖
pip install -r requirements.txt
```

## 冻结依赖问题排查

如果你发现某些包(如watchdog)没有出现在freeze生成的requirements.txt中，可能有以下原因:

1. **环境不匹配**: 确保你在正确的Python环境中运行freeze命令
2. **包未正确安装**: 某些包可能不是通过pip安装的
3. **虚拟环境问题**: 确保你在激活了正确的虚拟环境后再运行命令

## 使用增强版冻结脚本

我们提供了一个增强版的依赖冻结脚本，可以确保关键包被包含:

```bash
# 运行检查并冻结依赖
python check_and_freeze_deps.py
```

这个脚本会:
- 检查watchdog是否已安装
- 提供安装选项(如果未安装)
- 确保watchdog被添加到requirements.txt

## 手动添加watchdog

如果您仍然遇到问题，可以手动添加watchdog到您的requirements.txt:

```
watchdog==x.y.z  # 替换x.y.z为您需要的版本
```
