"""
配置管理器模块
负责管理和验证配置参数
"""
import os
import json
import logging
from typing import Any, Dict, Optional

class ConfigValidationError(Exception):
    """配置验证错误"""
    pass

class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        'media_folder': './media',
        'output_folder': './output',
        'max_retries': 3,
        'max_workers': 4,
        'use_jianying_first': True,
        'use_kuaishou': True,
        'use_bcut': True,
        'format_text': True,
        'include_timestamps': True,
        'show_progress': True,
        'process_video': True,
        'extract_audio_only': False,
        'watch_mode': False,
        'segment_length': 30,
        'max_segment_length': 2000,
        'min_segment_length': 10,
        'retry_delay': 1.0,
        'temp_dir': None,
        'log_level': 'INFO',
        'log_file': None,
        'max_part_time':20
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 可选的配置文件路径
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
    
    def load_config(self, config_file: str):
        """
        从文件加载配置
        
        Args:
            config_file: 配置文件路径
            
        Raises:
            ConfigValidationError: 如果配置无效
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # 更新配置，只接受已定义的配置项
            for key, value in user_config.items():
                if key in self.DEFAULT_CONFIG:
                    self.config[key] = value
                else:
                    logging.warning(f"忽略未知的配置项: {key}")
            
            # 验证配置
            self.validate_config()
            
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"配置文件格式错误: {str(e)}")
        except Exception as e:
            raise ConfigValidationError(f"加载配置文件失败: {str(e)}")
    
    def save_config(self, config_file: str):
        """
        保存配置到文件
        
        Args:
            config_file: 配置文件路径
        """
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise ConfigValidationError(f"保存配置文件失败: {str(e)}")
    
    def validate_config(self):
        """
        验证配置有效性
        
        Raises:
            ConfigValidationError: 如果配置无效
        """
        # 验证文件夹路径
        if not os.path.exists(self.config['media_folder']):
            try:
                os.makedirs(self.config['media_folder'])
            except Exception as e:
                raise ConfigValidationError(f"无法创建媒体文件夹: {str(e)}")
        
        if not os.path.exists(self.config['output_folder']):
            try:
                os.makedirs(self.config['output_folder'])
            except Exception as e:
                raise ConfigValidationError(f"无法创建输出文件夹: {str(e)}")
        
        # 验证数值范围
        if not 1 <= self.config['max_retries'] <= 10:
            raise ConfigValidationError("max_retries 必须在 1-10 之间")
        
        if not 1 <= self.config['max_workers'] <= 16:
            raise ConfigValidationError("max_workers 必须在 1-16 之间")
        
        if not 10 <= self.config['segment_length'] <= 300:
            raise ConfigValidationError("segment_length 必须在 10-300 秒之间")
        
        if not 100 <= self.config['max_segment_length'] <= 5000:
            raise ConfigValidationError("max_segment_length 必须在 100-5000 之间")
        
        if not 5 <= self.config['min_segment_length'] <= 100:
            raise ConfigValidationError("min_segment_length 必须在 5-100 之间")
        
        if not 0.1 <= self.config['retry_delay'] <= 10.0:
            raise ConfigValidationError("retry_delay 必须在 0.1-10.0 秒之间")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置项名称
            default: 默认值
            
        Returns:
            配置项的值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置项
        
        Args:
            key: 配置项名称
            value: 配置项的值
            
        Raises:
            ConfigValidationError: 如果配置项不存在或值无效
        """
        if key not in self.DEFAULT_CONFIG:
            raise ConfigValidationError(f"未知的配置项: {key}")
            
        self.config[key] = value
        # 验证新的配置
        self.validate_config()
    
    def update(self, config_dict: Dict[str, Any]):
        """
        批量更新配置
        
        Args:
            config_dict: 配置字典
            
        Raises:
            ConfigValidationError: 如果任何配置项无效
        """
        # 创建临时配置副本
        temp_config = self.config.copy()
        
        try:
            for key, value in config_dict.items():
                if key in self.DEFAULT_CONFIG:
                    temp_config[key] = value
                else:
                    logging.warning(f"忽略未知的配置项: {key}")
            
            # 验证新的配置
            old_config = self.config
            self.config = temp_config
            self.validate_config()
            
        except Exception as e:
            # 恢复原始配置
            self.config = old_config
            raise ConfigValidationError(f"更新配置失败: {str(e)}")
    
    def reset(self):
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
    
    def print_config(self):
        """打印当前配置"""
        logging.info("\n当前配置:")
        for key, value in self.config.items():
            logging.info(f"  {key}: {value}")
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """
        以字典形式返回配置
        
        Returns:
            配置字典的副本
        """
        return self.config.copy()