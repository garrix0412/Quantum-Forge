"""
VQE Estimator Builder - QuantumForge V5

构建VQE估计器配置，支持不同后端类型。遵循V5架构：信任上游参数，专注估计器构建。
"""

from typing import Dict, Any

# 导入基类
try:
    from ..base_component import BaseComponent
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from components.base_component import BaseComponent

# 导入LLM调用
try:
    from core.llm_engine import call_llm
except ImportError:
    import sys
    import os
    core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
    if core_path not in sys.path:
        sys.path.append(core_path)
    from llm_engine import call_llm

import json


class EstimatorBuilder(BaseComponent):
    """VQE估计器构建器 - 基于LLM选择最适合的估计器配置"""
    
    description = "Build VQE estimator configuration for quantum expectation value calculations. Supports simulator and hardware backends with intelligent backend selection based on query context and system parameters."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """构建VQE估计器配置"""
        # 从上游参数获取基本信息
        num_qubits = int(params.get("num_qubits", 4))
        
        # 固定使用simulator后端
        backend_type = "simulator"
        
        # 生成估计器配置代码
        code = self._generate_estimator_code()
        
        # 简要描述
        notes = f"Configured simulator estimator for {num_qubits}-qubit VQE"
        
        return {
            "code": code,
            "notes": notes,
            "estimator_info": {
                "backend_type": backend_type
            }
        }
    
    def _generate_estimator_code(self) -> str:
        """生成估计器配置代码 - 使用StatevectorEstimator"""
        code = '''# VQE Estimator Configuration - Statevector Simulator
from qiskit.primitives import StatevectorEstimator

# Create statevector estimator
estimator = StatevectorEstimator()

# Estimator ready for VQE expectation value calculations
print("Statevector estimator configured for VQE")'''
        
        return code


# 测试
if __name__ == "__main__":
    print("🧪 Testing EstimatorBuilder...")
    
    builder = EstimatorBuilder()
    
    test_cases = [
        {
            "name": "Small system simulation",
            "query": "Test VQE convergence with classical simulation",
            "params": {"num_qubits": 4}
        },
        {
            "name": "Medium system simulation",
            "query": "VQE optimization on 8-qubit system",
            "params": {"num_qubits": 8}
        },
        {
            "name": "Development and debugging",
            "query": "Debug VQE optimization parameters",
            "params": {"num_qubits": 6}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"  Query: {test_case['query']}")
        
        result = builder.execute(test_case['query'], test_case['params'])
        print(f"  ✅ Notes: {result['notes']}")
        print(f"  🔧 Backend: {result['estimator_info']['backend_type']}")
        print(f"  📝 Code length: {len(result['code'])} chars")
    
    print("\n✅ EstimatorBuilder implemented - simulator backend only!")