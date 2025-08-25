"""
VQE Optimizer Selector - QuantumForge V5

VQE优化器参数标准化器，接收来自parameter_matcher的参数，进行优化器特定的验证、标准化和默认值处理。
遵循QuantumForge V5的LLM驱动架构：信任上游parameter_matcher分析，专注优化器选择逻辑。
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


class OptimizerSelector(BaseComponent):
    """VQE优化器选择器 - 信任parameter_matcher的智能参数分析，专注优化器选择"""
    
    description = "Select and configure VQE optimizers for non-molecular quantum problems (TFIM, Heisenberg, QAOA, etc.). Supports gradient-based and gradient-free optimizers with intelligent selection. Trusts parameter_matcher for optimizer selection. NOT for molecular/quantum chemistry problems - use MolecularOptimizer instead."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """选择和配置VQE优化器"""
        # 信任parameter_matcher提供的参数
        optimizer_params = params.copy()
        
        # 应用VQE Optimizer特定的默认值
        complete_params = self._apply_optimizer_defaults(optimizer_params)
        
        # 从上游参数获取关键信息
        circuit_info = complete_params.get("circuit_info", {})
        parameter_count = circuit_info.get("parameter_count", 12)
        estimator_info = complete_params.get("estimator_info", {})
        backend_type = estimator_info.get("backend_type", "simulator")
        
        # 从parameter_matcher获取优化器配置
        optimizer_config = self._select_optimizer_by_heuristics(complete_params, parameter_count, backend_type)
        
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
    
    def _apply_optimizer_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用VQE Optimizer特定的默认值 - 信任parameter_matcher"""
        # 设置VQE优化器默认值（不包括optimizer_type，让启发式选择决定）
        defaults = {
            "max_iterations": 1000,  # 默认迭代次数
            "tolerance": 1e-6  # 默认收敛容差
        }
        
        # 合并参数，保持parameter_matcher提供的参数优先
        complete_params = {**defaults, **params}
        
        return complete_params
    
    def _select_optimizer_by_heuristics(self, params: Dict[str, Any], parameter_count: int, backend_type: str) -> Dict[str, Any]:
        """基于启发式规则选择优化器 - 使用经过验证的选择逻辑"""
        # 从parameter_matcher获取优化器类型（如果提供）
        optimizer_type = params.get("optimizer_type")
        
        # 如果parameter_matcher没有提供，使用启发式选择
        if not optimizer_type:
            if backend_type == "hardware":
                optimizer_type = "COBYLA"  # 对噪声鲁棒
                max_iter = 1000
                tolerance = 1e-5
                reasoning = "Hardware backend: robust to noise"
            elif backend_type == "simulator" and 10 <= parameter_count <= 50:
                optimizer_type = "L_BFGS_B"   # 中等参数空间的精确优化
                max_iter = 1000
                tolerance = 1e-7
                reasoning = "Medium parameter space: memory-efficient quasi-Newton"
            elif backend_type == "simulator" and parameter_count < 10:
                optimizer_type = "SLSQP"   # 快速收敛
                max_iter = 1000
                tolerance = 1e-6
                reasoning = "Small parameter space: fast convergence"
            else:
                optimizer_type = "SPSA"    # 可扩展
                max_iter = 1000
                tolerance = 1e-5
                reasoning = "Large parameter space: scalable stochastic"
        else:
            # 使用parameter_matcher提供的配置
            max_iter = params.get("max_iterations", 1000)
            tolerance = params.get("tolerance", 1e-6)
            reasoning = "Parameter_matcher selection"
        
        # 验证优化器类型
        valid_optimizers = ["COBYLA", "SLSQP", "L_BFGS_B", "SPSA"]
        if optimizer_type not in valid_optimizers:
            optimizer_type = "COBYLA"  # 保守默认
            reasoning = "Fallback to robust default"
        
        # 验证参数范围
        max_iter = max(200, min(2000, max_iter))
        tolerance = max(1e-8, min(1e-4, tolerance))
        
        return {
            "type": optimizer_type,
            "max_iterations": max_iter,
            "tolerance": tolerance,
            "reasoning": reasoning,
            "confidence": 0.9  # 高置信度的启发式选择
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

        elif optimizer_type == "L_BFGS_B":
            code = f'''# VQE Optimizer Configuration - L_BFGS_B
from qiskit_algorithms.optimizers import L_BFGS_B
import numpy as np

# Configure L_BFGS_B optimizer (quasi-Newton with bounds)
# Parameter bounds (optional): None means unbounded
optimizer = L_BFGS_B(
    maxfun={max_iter},
    ftol={tolerance},
    eps=1e-8
)

print(f"Configured L_BFGS_B optimizer: {{optimizer.settings}}")'''

        else:  # SPSA
            code = f'''# VQE Optimizer Configuration - SPSA
from qiskit_algorithms.optimizers import SPSA

# Configure SPSA optimizer (stochastic, scalable)
optimizer = SPSA(
    maxiter={max_iter}
)

print(f"Configured SPSA optimizer: {{optimizer.settings}}")'''
        
        return code

