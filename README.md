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
