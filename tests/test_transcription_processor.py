"""
测试转录处理器模块
"""
import unittest
import os
import tempfile
from typing import Dict, List

from audio_tools.processing.transcription_processor import TranscriptionProcessor
from tests.test_utils import MockASRService, MockProgressReporter


class TestTranscriptionProcessor(unittest.TestCase):
    """测试转录处理器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_segments = self._create_test_segments()
        
        # 创建模拟ASR服务
        self.mock_asr_service = MockASRService({
            self.test_segments[0]: "这是第一个测试片段的结果",
            self.test_segments[1]: "这是第二个测试片段的结果",
            self.test_segments[2]: None,  # 模拟失败的情况
            self.test_segments[3]: "这是第四个测试片段的结果",
        })
        
        # 创建进度报告器
        self.progress_reporter = MockProgressReporter()
        
        # 创建转录处理器
        self.processor = TranscriptionProcessor(
            asr_manager=self.mock_asr_service,
            temp_segments_dir=self.temp_dir,
            max_workers=2,
            max_retries=2,
            progress_callback=self.progress_reporter.report_progress
        )
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
        
        # 确保线程池正确关闭
        if hasattr(self.processor, 'executor'):
            self.processor.executor.shutdown()
    
    def _create_test_segments(self) -> List[str]:
        """创建测试用的音频片段文件"""
        segments = []
        for i in range(5):
            segment_path = os.path.join(self.temp_dir, f"test_segment_{i}.mp3")
            # 创建空文件
            with open(segment_path, 'w') as f:
                f.write(f"Mock content for segment {i}")
            segments.append(segment_path)
        return segments
    
    def test_recognize_audio(self):
        """测试单个音频识别"""
        # 测试成功情况
        result = self.processor.recognize_audio(self.test_segments[0])
        self.assertEqual(result, "这是第一个测试片段的结果")
        
        # 测试失败情况
        result = self.processor.recognize_audio(self.test_segments[2])
        self.assertIsNone(result)
    
    def test_process_audio_segments(self):
        """测试批量处理音频片段"""
        # 处理所有片段
        results = self.processor.process_audio_segments(self.test_segments)
        
        # 验证结果
        self.assertEqual(len(results), 5)  # 应该有5个结果
        self.assertEqual(results[0], "这是第一个测试片段的结果")
        self.assertEqual(results[1], "这是第二个测试片段的结果")
        self.assertIsNone(results[2])  # 第三个应该是None
        self.assertEqual(results[3], "这是第四个测试片段的结果")
        
        # 验证进度回调
        self.assertTrue(len(self.progress_reporter.progress_history) > 0)
    
    def test_retry_failed_segments(self):
        """测试重试失败的片段"""
        # 先处理所有片段
        initial_results = {
            0: "这是第一个测试片段的结果",
            1: "这是第二个测试片段的结果",
            2: None,  # 这个需要重试
            3: "这是第四个测试片段的结果",
            4: None,  # 这个也需要重试
        }
        
        # 为第二轮重试设置不同的响应
        self.mock_asr_service.responses[self.test_segments[2]] = "这是重试后的第三个片段结果"
        
        # 重试失败的片段
        updated_results = self.processor.retry_failed_segments(self.test_segments, initial_results.copy())
        
        # 验证更新后的结果
        self.assertEqual(updated_results[0], "这是第一个测试片段的结果")  # 不需要重试的保持不变
        self.assertEqual(updated_results[2], "这是重试后的第三个片段结果")  # 重试成功
        self.assertIsNotNone(updated_results[4])  # 使用默认结果
    
    def test_interrupt_flag(self):
        """测试中断标志功能"""
        # 设置中断标志
        self.processor.set_interrupt_flag(True)
        
        # 尝试处理片段
        results = self.processor.process_audio_segments(self.test_segments[:2])
        
        # 验证中断被传递到ASR服务
        self.assertTrue(self.mock_asr_service.interrupt_flag)
        
        # 重置中断标志
        self.processor.set_interrupt_flag(False)
        self.assertFalse(self.mock_asr_service.interrupt_flag)


if __name__ == '__main__':
    unittest.main()
