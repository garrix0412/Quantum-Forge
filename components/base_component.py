"""
Base Component - QuantumForge V5 组件基类

所有量子代码生成组件的基类。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 1.3 设计。
"""

from typing import Dict, Any
from abc import ABC, abstractmethod
import math


class BaseComponent(ABC):
    """
    QuantumForge V5 所有组件的基类
    
    设计原则:
    - 每个组件只做一件事，职责单一
    - LLM可以理解组件功能描述
    - 标准化的输入输出接口
    - 简单纯粹，不添加额外功能
    """
    
    # 组件功能描述 - 供LLM理解和发现
    description: str = "Base component description for LLM understanding"
    
    @abstractmethod
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        组件核心执行方法
        
        Args:
            query: 用户原始查询（保持上下文）
            params: 组件执行所需的参数
            
        Returns:
            Dict[str, Any]: 组件执行结果
            {
                "output_key": "output_value",  # 组件的主要输出
                "notes": "执行说明",             # 可选：执行说明
                # 其他组件特定的输出字段
            }
        """
        pass
    
    def get_component_name(self) -> str:
        """获取组件名称"""
        return self.__class__.__name__
    
    def get_description(self) -> str:
        """获取组件功能描述"""
        return self.description
    
    # === 通用辅助函数 ===
    
    def _safe_calculate_qubits(self, vector_size: int) -> int:
        """安全地计算需要的量子比特数"""
        try:
            if vector_size <= 0:
                return 1  # 默认最小值
            return max(1, int(math.ceil(math.log2(vector_size))))
        except (ValueError, TypeError, OverflowError):
            return 1  # 安全的默认值
    
    def _safe_convert_to_int(self, value: Any) -> int:
        """安全地将值转换为整数"""
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return 1  # 默认值
        else:
            return 1  # 默认值
    
    def _safe_convert_to_float(self, value: Any) -> float:
        """安全地将值转换为浮点数"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 1.0  # 默认值
        else:
            return 1.0  # 默认值


# 测试代码
if __name__ == "__main__":
    print("🧪 Testing BaseComponent...")
    
    # 创建一个测试组件
    class TestQuantumComponent(BaseComponent):
        description = "Test quantum component for TFIM parameter extraction"
        
        def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "test_result": "success",
                "received_query": query,
                "received_params": params,
                "notes": "Test component executed successfully"
            }
    
    try:
        # 测试组件创建和基本功能
        test_comp = TestQuantumComponent()
        
        print(f"📋 Component name: {test_comp.get_component_name()}")
        print(f"📋 Component description: {test_comp.get_description()}")
        
        # 测试执行
        test_query = "4-qubit TFIM with J=1.5 h=1.0"
        test_params = {"num_qubits": 4, "J": 1.5, "h": 1.0}
        
        result = test_comp.execute(test_query, test_params)
        print(f"🎯 Execution result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        print("✅ BaseComponent test completed successfully")
        
    except Exception as e:
        print(f"⚠️ BaseComponent test error: {e}")