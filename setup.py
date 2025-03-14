from setuptools import setup, find_packages

setup(
    name="audio_tools",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydub>=0.25.1",
        "tqdm>=4.65.0",
        "requests>=2.28.0",
        "watchdog>=3.0.0"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="音频处理工具包，提供音频分割、识别和转写功能",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords="audio,speech recognition,transcription",
    url="https://github.com/yourusername/audio_tools",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio",
    ],
    python_requires=">=3.7",
)
