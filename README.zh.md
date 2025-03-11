# 音频转写工具

一个功能强大的音频/视频处理工具，可以自动分割、识别并转写音频内容为文本。支持多种ASR服务，并行处理，提高效率。

*[English Version](README.md)*

## 主要功能

- ✅ 自动分割长音频为小片段，便于处理
- ✅ 支持多种ASR（自动语音识别）服务
- ✅ 并行处理音频文件，提高效率
- ✅ 支持音视频文件（自动提取视频中的音频）
- ✅ 自动重试失败的片段
- ✅ 支持进度条显示处理过程
- ✅ 完整的日志记录
- ✅ 监视模式：自动处理新添加的文件

## 安装

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

## 使用方法

1. 准备您的音频/视频文件，放入media文件夹

2. 运行主程序：
   ```
   python main.py
   ```
   
   启用监视模式（自动处理新添加的文件）：
   ```
   python main.py --watch
   ```

3. 查看output文件夹中的输出文件

## 配置选项

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
    extract_audio_only=False,         # 仅提取音频
    watch_mode=False                  # 监视模式
)
```

## 监视模式

监视模式会持续监控media文件夹，当检测到新的音频或视频文件时自动处理：

- 实时监控新文件
- 自动开始处理
- 避免重复处理已完成的文件
