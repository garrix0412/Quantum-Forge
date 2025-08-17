"""
QuantumForge V4 Base Tool

所有工具的抽象基类，定义统一接口。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """
    工具抽象基类
    
    所有量子代码生成工具必须继承此类并实现execute方法
    """
    
    def __init__(self):
        """初始化工具"""
        self.name = self.__class__.__name__
    
    @abstractmethod
    def execute(self, context: str) -> Dict[str, Any]:
        """
        执行工具逻辑
        
        Args:
            context: 从Memory获取的上下文信息
            
        Returns:
            工具执行结果，包含:
            - code: 生成的代码字符串
            - parameters: 提取或生成的参数
            - notes: 执行说明或备注
        """
        pass
    
    def get_name(self) -> str:
        """获取工具名称"""
        return self.name
    
    def get_description(self) -> str:
        """获取工具描述"""
        return self.__doc__ or f"{self.name} - No description available"


