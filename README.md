# Audio Transcription Tool

A powerful audio/video processing tool that automatically segments, recognizes, and transcribes audio content into text. Supports multiple ASR services and parallel processing for improved efficiency.

*[中文版本](README.zh.md)*

## Key Features

- ✅ Automatic segmentation of long audio into smaller clips for processing
- ✅ Support for multiple ASR (Automatic Speech Recognition) services
- ✅ Parallel processing of audio files for improved efficiency
- ✅ Support for both audio and video files (automatically extracts audio from video)
- ✅ Automatic retry of failed segments
- ✅ Progress bar display for processing steps
- ✅ Comprehensive logging
- ✅ Watch mode: automatically process newly added files

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd segement_audio
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make sure FFmpeg is installed (required for video processing)

## Usage

1. Prepare your audio/video files and place them in the media folder

2. Run the main program:
   ```
   python main.py
   ```
   
   Enable watch mode (automatically process newly added files):
   ```
   python main.py --watch
   ```

3. Check the output files in the output folder

## Configuration Options

You can customize processing parameters as follows:

```python
processor = AudioProcessor(
    media_folder='./media',           # Media folder path
    output_folder='./output',         # Output folder path
    max_retries=3,                    # Maximum number of retries
    max_workers=4,                    # Maximum parallel processing threads
    use_jianying_first=True,          # Prioritize Jianying ASR
    use_kuaishou=True,                # Use Kuaishou ASR
    use_bcut=True,                    # Use BCut ASR
    format_text=True,                 # Format text
    include_timestamps=True,          # Include timestamps
    show_progress=True,               # Show progress bars
    process_video=True,               # Process video files
    extract_audio_only=False,         # Extract audio only
    watch_mode=False                  # Watch mode
)
```

## Watch Mode

Watch mode continuously monitors the media folder and automatically processes new audio or video files when detected:

- Real-time monitoring of new files
- Automatically starts processing
- Avoids reprocessing completed files

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
