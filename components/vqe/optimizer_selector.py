"""
VQE Optimizer Selector - QuantumForge V5

选择和配置VQE优化器，基于用户查询和系统特征智能选择。
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


class OptimizerSelector(BaseComponent):
    """VQE优化器选择器 - 基于LLM智能选择最适合的优化算法"""
    
    description = "Select and configure VQE optimizers based on problem characteristics and user requirements. Supports gradient-based and gradient-free optimizers with intelligent selection."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """选择和配置VQE优化器"""
        # 从上游参数获取关键信息
        circuit_info = params.get("circuit_info", {})
        parameter_count = circuit_info.get("parameter_count", 12)
        estimator_info = params.get("estimator_info", {})
        backend_type = estimator_info.get("backend_type", "simulator")
        
        # 使用LLM选择优化器
        optimizer_config = self._llm_select_optimizer(query, parameter_count, backend_type)
        
        # 生成优化器配置代码
        code = self._generate_optimizer_code(optimizer_config)
        
        # 简要描述
        optimizer_type = optimizer_config["type"]
        notes = f"Selected {optimizer_type} optimizer for {parameter_count} parameters"
        
        return {
            "code": code,
            "notes": notes,
            "optimizer_info": {
                "type": optimizer_type,
                "max_iterations": optimizer_config["max_iterations"],
                "convergence_tolerance": optimizer_config.get("tolerance", 1e-6)
            }
        }
    
    def _llm_select_optimizer(self, query: str, parameter_count: int, backend_type: str) -> Dict[str, Any]:
        """使用LLM选择最适合的优化器"""
        prompt = f"""
Based on the user query and VQE optimization characteristics, select the most appropriate optimizer:

User Query: "{query}"

VQE System Info:
- Parameter count: {parameter_count}
- Backend type: {backend_type}

Available Optimizer Options:

1. **COBYLA** (Constrained Optimization BY Linear Approximation):
   - Type: Gradient-free, derivative-free
   - Best for: Noisy backends, small-medium parameter spaces, robust optimization
   - Pros: Handles noise well, no gradient computation needed
   - Cons: Slower convergence, less precise
   - Keywords: "robust", "noisy", "hardware", "stable"

2. **SLSQP** (Sequential Least Squares Programming):
   - Type: Gradient-based with finite differences
   - Best for: Clean backends, faster convergence, medium parameter spaces
   - Pros: Faster convergence, more precise
   - Cons: Sensitive to noise, requires gradient estimation
   - Keywords: "fast", "precise", "simulator", "gradient"

3. **SPSA** (Simultaneous Perturbation Stochastic Approximation):
   - Type: Stochastic gradient approximation
   - Best for: Large parameter spaces, noisy environments, hardware backends
   - Pros: Scales well, handles noise, efficient for high dimensions
   - Cons: Stochastic convergence, requires tuning
   - Keywords: "large", "stochastic", "high-dimensional", "scalable"

Selection Guidelines:
- COBYLA: Hardware backends, noisy environments, robust optimization
- SLSQP: Simulator backends, clean environments, fast convergence
- SPSA: Large parameter spaces (>20), hardware backends, scalable optimization

Respond with ONLY a JSON object:
{{
    "type": "<COBYLA|SLSQP|SPSA>",
    "max_iterations": <50-500>,
    "tolerance": <1e-4_to_1e-8>,
    "reasoning": "<brief selection rationale>",
    "confidence": <0.0_to_1.0>
}}

JSON:"""

        try:
            response = call_llm(prompt)
            
            # 清理并解析JSON响应
            response = response.strip()
            if '```' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    response = response[start:end]
            
            result = json.loads(response)
            
            # 验证优化器类型
            valid_optimizers = ["COBYLA", "SLSQP", "SPSA"]
            if result.get("type") not in valid_optimizers:
                result["type"] = "COBYLA"  # 保守默认
            
            # 验证参数范围
            result["max_iterations"] = max(50, min(500, result.get("max_iterations", 100)))
            result["tolerance"] = max(1e-8, min(1e-4, result.get("tolerance", 1e-6)))
            
            return result
            
        except Exception as e:
            print(f"⚠️ LLM optimizer selection failed: {e}")
            # 回退到启发式选择
            if backend_type == "hardware" or parameter_count > 20:
                optimizer_type = "COBYLA"  # 对噪声鲁棒
                max_iter = 200
                tolerance = 1e-5
            elif backend_type == "simulator" and parameter_count <= 15:
                optimizer_type = "SLSQP"   # 快速收敛
                max_iter = 100
                tolerance = 1e-6
            else:
                optimizer_type = "SPSA"    # 可扩展
                max_iter = 150
                tolerance = 1e-5
            
            return {
                "type": optimizer_type,
                "max_iterations": max_iter,
                "tolerance": tolerance,
                "reasoning": "Fallback heuristic selection",
                "confidence": 0.5
            }
    
    def _generate_optimizer_code(self, optimizer_config: Dict[str, Any]) -> str:
        """生成优化器配置代码"""
        optimizer_type = optimizer_config["type"]
        max_iter = optimizer_config["max_iterations"]
        tolerance = optimizer_config.get("tolerance", 1e-6)
        
        if optimizer_type == "COBYLA":
            code = f'''# VQE Optimizer Configuration - COBYLA
from qiskit_algorithms.optimizers import COBYLA

# Configure COBYLA optimizer (gradient-free, robust to noise)
optimizer = COBYLA(
    maxiter={max_iter},
    tol={tolerance}
)

print(f"Configured COBYLA optimizer: {{optimizer.settings}}")'''

        elif optimizer_type == "SLSQP":
            code = f'''# VQE Optimizer Configuration - SLSQP
from qiskit_algorithms.optimizers import SLSQP

# Configure SLSQP optimizer (gradient-based, fast convergence)
optimizer = SLSQP(
    maxiter={max_iter},
    ftol={tolerance}
)

print(f"Configured SLSQP optimizer: {{optimizer.settings}}")'''

        else:  # SPSA
            code = f'''# VQE Optimizer Configuration - SPSA
from qiskit_algorithms.optimizers import SPSA

# Configure SPSA optimizer (stochastic, scalable)
optimizer = SPSA(
    maxiter={max_iter}
)

print(f"Configured SPSA optimizer: {{optimizer.settings}}")'''
        
        return code


# 测试
if __name__ == "__main__":
    print("🧪 Testing OptimizerSelector...")
    
    selector = OptimizerSelector()
    
    test_cases = [
        {
            "name": "Small system on simulator",
            "query": "Fast VQE optimization with high precision",
            "params": {
                "circuit_info": {"parameter_count": 8},
                "estimator_info": {"backend_type": "simulator"}
            }
        },
        {
            "name": "Hardware backend optimization",
            "query": "Robust VQE optimization on quantum hardware",
            "params": {
                "circuit_info": {"parameter_count": 15},
                "estimator_info": {"backend_type": "hardware"}
            }
        },
        {
            "name": "Large parameter space",
            "query": "Scalable optimization for high-dimensional parameter space",
            "params": {
                "circuit_info": {"parameter_count": 25},
                "estimator_info": {"backend_type": "hardware"}
            }
        },
        {
            "name": "Stochastic optimization",
            "query": "SPSA-based stochastic optimization approach",
            "params": {
                "circuit_info": {"parameter_count": 12},
                "estimator_info": {"backend_type": "simulator"}
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"  Query: {test_case['query']}")
        
        result = selector.execute(test_case['query'], test_case['params'])
        print(f"  ✅ Notes: {result['notes']}")
        print(f"  🔧 Optimizer: {result['optimizer_info']}")
        print(f"  📝 Code length: {len(result['code'])} chars")
    
    print("\n✅ OptimizerSelector implemented with LLM intelligent selection!")