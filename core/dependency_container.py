"""
依赖注入容器
用于管理和注入各种依赖，使组件之间解耦
"""
import os
import logging
from typing import Dict, Any, Type, Optional, Callable


class DependencyContainer:
    """依赖注入容器，用于管理所有组件依赖"""

    def __init__(self):
        """初始化依赖容器"""
        self._dependencies: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}

    def register(self, name: str, instance_or_class: Any, singleton: bool = True):
        """
        注册一个依赖
        
        Args:
            name: 依赖名称
            instance_or_class: 依赖实例或类
            singleton: 是否为单例
        """
        self._dependencies[name] = instance_or_class
        self._singletons[name] = singleton
        logging.debug(f"已注册依赖: {name}")

    def register_factory(self, name: str, factory: Callable, singleton: bool = True):
        """
        注册一个工厂函数来创建依赖
        
        Args:
            name: 依赖名称
            factory: 创建依赖的工厂函数
            singleton: 是否为单例
        """
        self._factories[name] = factory
        self._singletons[name] = singleton
        logging.debug(f"已注册工厂: {name}")

    def get(self, name: str) -> Any:
        """
        获取依赖实例
        
        Args:
            name: 依赖名称
            
        Returns:
            依赖实例
        """
        # 如果依赖已存在且是单例，直接返回
        if name in self._dependencies and self._singletons.get(name, True):
            dependency = self._dependencies[name]
            if not isinstance(dependency, type):  # 如果不是类型而是实例，直接返回
                return dependency
        
        # 如果有工厂函数，使用工厂创建
        if name in self._factories:
            instance = self._factories[name](self)
            if self._singletons.get(name, True):
                self._dependencies[name] = instance  # 缓存单例
            return instance
            
        # 直接创建实例
        if name in self._dependencies:
            dependency = self._dependencies[name]
            if isinstance(dependency, type):  # 如果是类型，创建实例
                instance = dependency()
                if self._singletons.get(name, True):
                    self._dependencies[name] = instance  # 缓存单例
                return instance
            return dependency
            
        raise KeyError(f"未注册的依赖: {name}")

    def clear(self):
        """清除所有依赖"""
        self._dependencies.clear()
        self._factories.clear()
        self._singletons.clear()


# 创建一个全局容器实例
container = DependencyContainer()
