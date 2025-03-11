# 音频转写工具 (Audio Transcription Tool)

[English](#audio-transcription-tool) | [中文](#音频转写工具)

## 音频转写工具

一个功能强大的音频/视频处理工具，可以自动分割、识别并转写音频内容为文本。支持多种ASR服务，并行处理，提高效率。

### 主要功能

- ✅ 自动分割长音频为小片段，便于处理
- ✅ 支持多种ASR（自动语音识别）服务
- ✅ 并行处理音频文件，提高效率
- ✅ 支持音视频文件（自动提取视频中的音频）
- ✅ 自动重试失败的片段
- ✅ 支持进度条显示处理过程
- ✅ 完整的日志记录

### 安装

1. 克隆代码仓库：
   ```
   git clone <仓库地址>
   cd segement_audio
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 确保安装了FFmpeg（用于处理视频文件）

### 使用方法

1. 准备您的音频/视频文件，放入media文件夹

2. 运行主程序：
   ```
   python main.py
   ```

3. 查看output文件夹中的输出文件

### 配置选项

您可以通过以下方式自定义处理参数：

```python
processor = AudioProcessor(
    media_folder='./media',           # 媒体文件夹路径
    output_folder='./output',         # 输出文件夹路径
    max_retries=3,                    # 最大重试次数
    max_workers=4,                    # 最大并行处理线程
    use_jianying_first=True,          # 优先使用剪映ASR
    use_kuaishou=True,                # 使用快手ASR
    use_bcut=True,                    # 使用必剪ASR
    format_text=True,                 # 格式化文本
    include_timestamps=True,          # 包含时间戳
    show_progress=True,               # 显示进度条
    process_video=True,               # 处理视频文件
    extract_audio_only=False          # 仅提取音频
)
```

---

## Audio Transcription Tool

A powerful audio/video processing tool that automatically segments, recognizes, and transcribes audio content into text. Supports multiple ASR services and parallel processing for improved efficiency.

### Key Features

- ✅ Automatic segmentation of long audio into smaller clips for processing
- ✅ Support for multiple ASR (Automatic Speech Recognition) services
- ✅ Parallel processing of audio files for improved efficiency
- ✅ Support for both audio and video files (automatically extracts audio from video)
- ✅ Automatic retry of failed segments
- ✅ Progress bar display for processing steps
- ✅ Comprehensive logging

### Installation

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

### Usage

1. Prepare your audio/video files and place them in the media folder

2. Run the main program:
   ```
   python main.py
   ```

3. Check the output files in the output folder

### Configuration Options

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
    extract_audio_only=False          # Extract audio only
)
```
