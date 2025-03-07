import logging
import random
import threading
from typing import List, Dict, Tuple, Type, Optional

from .base_asr import BaseASR

class ASRServiceSelector:
    """
    ASR服务选择器，负责在多个ASR服务之间进行负载均衡
    实现多种策略：轮询、随机、优先级等
    """
    
    def __init__(self):
        # 锁用于保护共享状态
        self._lock = threading.RLock()
        # 服务计数器，用于记录每个服务的使用次数
        self._service_counters: Dict[str, int] = {}
        # 服务成功率，用于记录每个服务的成功率
        self._service_success_rates: Dict[str, Tuple[int, int]] = {}  # (成功次数, 总调用次数)
        # 服务可用状态，如果一个服务短时间内多次失败，将被标记为不可用
        self._service_available: Dict[str, bool] = {}
        # 当前轮询索引
        self._round_robin_index: int = 0
        # 已配置的服务及其权重
        self._services: List[Tuple[str, Type[BaseASR], int]] = []  # (名称, 类, 权重)
        
    def register_service(self, name: str, service_class: Type[BaseASR], weight: int = 10):
        """
        注册一个ASR服务
        
        Args:
            name: 服务名称
            service_class: 服务类
            weight: 服务权重，值越大使用概率越高
        """
        with self._lock:
            self._services.append((name, service_class, weight))
            self._service_counters[name] = 0
            self._service_success_rates[name] = (0, 0)
            self._service_available[name] = True
            logging.info(f"注册ASR服务: {name}, 权重: {weight}")
    
    def report_result(self, service_name: str, success: bool):
        """
        报告服务调用结果
        
        Args:
            service_name: 服务名称
            success: 是否成功
        """
        with self._lock:
            if service_name in self._service_success_rates:
                success_count, total_count = self._service_success_rates[service_name]
                if success:
                    success_count += 1
                total_count += 1
                self._service_success_rates[service_name] = (success_count, total_count)
                
                # 如果连续失败次数过多，标记服务为不可用
                if not success and total_count > 5 and success_count / total_count < 0.2:
                    self._service_available[service_name] = False
                    logging.warning(f"ASR服务 {service_name} 成功率过低，临时禁用")
                elif success and not self._service_available[service_name]:
                    # 如果成功且之前被标记为不可用，恢复可用状态
                    self._service_available[service_name] = True
                    logging.info(f"ASR服务 {service_name} 恢复可用")
    
    def select_by_round_robin(self) -> Optional[Tuple[str, Type[BaseASR]]]:
        """使用轮询策略选择服务"""
        with self._lock:
            available_services = [(name, cls) for name, cls, _ in self._services 
                               if self._service_available[name]]
            if not available_services:
                return None
                
            self._round_robin_index = (self._round_robin_index + 1) % len(available_services)
            selected = available_services[self._round_robin_index]
            return selected
    
    def select_by_weighted_random(self) -> Optional[Tuple[str, Type[BaseASR]]]:
        """使用加权随机策略选择服务"""
        with self._lock:
            # 只考虑可用的服务
            available_services = [(name, cls, weight) for name, cls, weight in self._services 
                               if self._service_available[name]]
            if not available_services:
                return None
                
            # 计算总权重
            total_weight = sum(weight for _, _, weight in available_services)
            if total_weight <= 0:
                # 如果总权重为0，使用轮询
                return self.select_by_round_robin()
                
            # 随机选择
            r = random.uniform(0, total_weight)
            cumulative_weight = 0
            for name, cls, weight in available_services:
                cumulative_weight += weight
                if r <= cumulative_weight:
                    return (name, cls)
            
            # 默认返回第一个
            return (available_services[0][0], available_services[0][1])
    
    def select_service(self, strategy: str = 'weighted_random') -> Optional[Tuple[str, Type[BaseASR]]]:
        """
        根据策略选择一个ASR服务
        
        Args:
            strategy: 选择策略，支持'round_robin'和'weighted_random'
            
        Returns:
            元组 (服务名称, 服务类)，如果没有可用服务则返回None
        """
        with self._lock:
            if not self._services:
                return None
                
            # 根据策略选择服务
            if strategy == 'round_robin':
                result = self.select_by_round_robin()
            else:  # weighted_random
                result = self.select_by_weighted_random()
                
            if result:
                name, _ = result
                self._service_counters[name] = self._service_counters.get(name, 0) + 1
                
            return result
    
    def get_service_stats(self) -> Dict[str, Dict]:
        """获取服务使用统计信息"""
        with self._lock:
            stats = {}
            for name in self._service_counters:
                success, total = self._service_success_rates.get(name, (0, 0))
                success_rate = (success / total) * 100 if total > 0 else 0
                
                stats[name] = {
                    'count': self._service_counters.get(name, 0),
                    'success_rate': f"{success_rate:.1f}%",
                    'available': self._service_available.get(name, True)
                }
            return stats
