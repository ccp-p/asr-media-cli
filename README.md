# 音频分段识别工具

这个项目可以将MP3音频文件分割成小片段，并使用多种ASR（自动语音识别）服务进行转写。

## 支持的ASR服务

- Google Speech Recognition
- 剪映ASR
- 快手ASR
- B站ASR (必剪)

## 安装

```bash
# 创建虚拟环境
python -m venv venv
# 激活虚拟环境
venv\Scripts\activate  # Windows
# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
python covert.py
```

### 重新识别失败片段

```bash
python recheck_recognition.py --output_folder "D:\download\dest" --use_jianying --use_kuaishou --use_bcut
```

## 参数说明

- mp3_folder: MP3文件所在文件夹
- output_folder: 输出结果文件夹
- use_jianying_first: 是否优先使用剪映ASR
- use_kuaishou: 是否使用快手ASR
- use_bcut: 是否优先使用B站ASR
