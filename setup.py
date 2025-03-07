from setuptools import setup, find_packages

setup(
    name="segement_audio",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "SpeechRecognition>=3.8.1",
        "pydub>=0.25.1",
        "requests>=2.27.1",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="音频分段识别工具",
    keywords="speech recognition, audio processing",
    python_requires=">=3.6",
)
