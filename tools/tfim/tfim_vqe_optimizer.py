"""
TFIM VQE Optimizer

配置和设置TFIM VQE算法的优化器和执行参数。
"""

import sys
import os

# 添加父目录到路径以导入BaseTool
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, List, Tuple
from base_tool import BaseTool
import json


class TFIMVQEOptimizer(BaseTool):
    """
    TFIM VQE优化器配置器
    
    功能:
    - 从Memory中读取TFIM模型参数、哈密顿量和ansatz配置
    - 调用LLM分析问题特征并选择最优的优化器
    - 配置VQE算法参数和初始化策略
    - 生成完整的VQE优化器设置代码
    """
    
    def __init__(self):
        super().__init__()
        
    def execute(self, context: str) -> Dict[str, Any]:
        """
        执行TFIM VQE优化器配置
        
        Args:
            context: 从Memory获取的上下文信息
            
        Returns:
            包含VQE优化器配置代码的结果
        """
        try:
            # 从上下文中提取参数和配置
            vqe_config = self._extract_vqe_config_from_context(context)
            
            if not vqe_config:
                # 如果没有找到配置，调用LLM分析
                vqe_config = self._llm_extract_vqe_config(context)
            
            # 调用LLM选择优化器
            optimizer_config = self._llm_select_optimizer(context, vqe_config)
            
            # 生成VQE优化器配置代码
            code = self._generate_vqe_optimizer_code(vqe_config, optimizer_config)
            
            return {
                "code": code,
                "vqe_config": vqe_config,
                "optimizer_config": optimizer_config,
                "notes": f"Configured VQE with {optimizer_config['type']} optimizer for {vqe_config['num_qubits']}-qubit TFIM"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "code": "",
                "notes": f"Failed to configure VQE optimizer: {str(e)}"
            }
    
    def _extract_vqe_config_from_context(self, context: str) -> Dict[str, Any]:
        """
        从上下文中提取VQE配置信息
        
        Args:
            context: 上下文信息
            
        Returns:
            VQE配置字典，如果没有找到返回None
        """
        try:
            lines = context.split('\n')
            
            config = {}
            
            # 提取基本参数
            for line in lines:
                if 'num_qubits' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            config['num_qubits'] = int(parts[1].strip())
                        except:
                            pass
                
                elif 'coupling_strength' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            config['coupling_strength'] = float(parts[1].strip())
                        except:
                            pass
                
                elif 'field_strength' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            config['field_strength'] = float(parts[1].strip())
                        except:
                            pass
                
                elif 'ansatz_type' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        ansatz_type = parts[1].strip().strip('\"\'')
                        config['ansatz_type'] = ansatz_type
                
                elif 'ansatz_depth' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            config['ansatz_depth'] = int(parts[1].strip())
                        except:
                            pass
                
                elif 'parameter_count' in line and ':' in line:
                    # 查找 "parameter_count": 16 这种格式
                    parts = line.split(':')
                    if len(parts) == 2:
                        try:
                            config['parameter_count'] = int(parts[1].strip().rstrip(',}'))
                        except:
                            pass
            
            # 检查是否获取到了足够的信息
            if 'num_qubits' in config:
                # 设置默认值
                config.setdefault('coupling_strength', 1.0)
                config.setdefault('field_strength', 1.0)
                config.setdefault('ansatz_type', 'hardware_efficient')
                config.setdefault('ansatz_depth', 2)
                config.setdefault('parameter_count', config['num_qubits'] * 2)
                return config
            
            return None
            
        except Exception as e:
            print(f"⚠️ Failed to extract VQE config from context: {e}")
            return None
    
    def _llm_extract_vqe_config(self, context: str) -> Dict[str, Any]:
        """
        使用LLM从上下文中提取VQE配置
        
        Args:
            context: 上下文信息
            
        Returns:
            VQE配置字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Based on the execution history below, extract VQE configuration for optimizer setup:

{context}

Please analyze the previous tool outputs and extract:
- num_qubits: number of qubits
- coupling_strength: J parameter
- field_strength: h parameter  
- ansatz_type: type of ansatz used
- ansatz_depth: circuit depth
- parameter_count: number of variational parameters

Respond with ONLY a JSON object:
{{
    "num_qubits": <number>,
    "coupling_strength": <float>,
    "field_strength": <float>,
    "ansatz_type": "<string>",
    "ansatz_depth": <number>,
    "parameter_count": <number>
}}

If some information is missing, use reasonable defaults.

JSON:"""

        try:
            response = call_llm(prompt, temperature=0.1)
            
            # 清理并解析JSON响应
            response = response.strip()
            if '```' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    response = response[start:end]
            
            config = json.loads(response)
            return config
            
        except Exception as e:
            print(f"⚠️ Failed to extract VQE config via LLM: {e}")
            
            # 回退到默认配置
            return {
                "num_qubits": 4,
                "coupling_strength": 1.0,
                "field_strength": 1.0,
                "ansatz_type": "hardware_efficient",
                "ansatz_depth": 2,
                "parameter_count": 8
            }
    
    def _llm_select_optimizer(self, context: str, vqe_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM选择最优的优化器
        
        Args:
            context: 上下文信息
            vqe_config: VQE配置
            
        Returns:
            优化器配置字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Based on the VQE problem characteristics below, select the optimal optimizer:

VQE Configuration:
- Number of qubits: {vqe_config['num_qubits']}
- Parameter count: {vqe_config['parameter_count']}
- Ansatz type: {vqe_config['ansatz_type']}
- Ansatz depth: {vqe_config['ansatz_depth']}
- Problem size: {vqe_config['coupling_strength']} (coupling), {vqe_config['field_strength']} (field)

Available optimizers:
1. "COBYLA": Gradient-free, good for noisy problems, robust but slow
2. "SPSA": Stochastic, efficient for large parameter spaces, noise-tolerant
3. "L_BFGS_B": Gradient-based, fast convergence, good for smooth landscapes
4. "SLSQP": Sequential least squares, handles constraints, moderate speed

Guidelines:
- Small systems (≤6 qubits, ≤20 params): L_BFGS_B or COBYLA
- Large systems (>6 qubits, >20 params): SPSA or COBYLA  
- Noisy environments: COBYLA or SPSA
- Smooth landscapes: L_BFGS_B

Respond with ONLY a JSON object:
{{
    "type": "<optimizer_name>",
    "max_iterations": <number>,
    "tolerance": <float>,
    "options": {{
        "disp": <boolean>,
        "maxfun": <number>
    }},
    "reason": "<brief_explanation>"
}}

JSON:"""

        try:
            response = call_llm(prompt, temperature=0.1)
            
            # 清理并解析JSON响应
            response = response.strip()
            if '```' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    response = response[start:end]
            
            optimizer_config = json.loads(response)
            return optimizer_config
            
        except Exception as e:
            print(f"⚠️ Failed to select optimizer via LLM: {e}")
            
            # 回退到默认优化器
            num_qubits = vqe_config['num_qubits']
            param_count = vqe_config['parameter_count']
            
            if num_qubits <= 6 and param_count <= 20:
                return {
                    "type": "L_BFGS_B",
                    "max_iterations": 200,
                    "tolerance": 1e-6,
                    "options": {"disp": True, "maxfun": 1000},
                    "reason": "Small system, gradient-based optimizer"
                }
            else:
                return {
                    "type": "COBYLA",
                    "max_iterations": 500,
                    "tolerance": 1e-4,
                    "options": {"disp": True, "maxfun": 2000},
                    "reason": "Large system, gradient-free optimizer"
                }
    
    def _generate_vqe_optimizer_code(self, vqe_config: Dict[str, Any], optimizer_config: Dict[str, Any]) -> str:
        """
        生成VQE优化器配置代码
        
        Args:
            vqe_config: VQE配置
            optimizer_config: 优化器配置
            
        Returns:
            生成的Python代码
        """
        num_qubits = vqe_config['num_qubits']
        param_count = vqe_config['parameter_count']
        optimizer_type = optimizer_config['type']
        max_iter = optimizer_config['max_iterations']
        tolerance = optimizer_config['tolerance']
        options = optimizer_config['options']
        
        code = f"""# TFIM VQE Optimizer Configuration
# Generated by QuantumForge V4

from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA, SPSA, L_BFGS_B, SLSQP
from qiskit.primitives import Estimator
import numpy as np

# VQE Configuration (from previous steps)
num_qubits = {num_qubits}
parameter_count = {param_count}
ansatz_type = "{vqe_config['ansatz_type']}"
ansatz_depth = {vqe_config['ansatz_depth']}

# Optimizer Configuration
optimizer_type = "{optimizer_type}"
max_iterations = {max_iter}
tolerance = {tolerance}

print(f"Configuring VQE optimizer: {{optimizer_type}}")
print(f"Problem size: {{num_qubits}} qubits, {{parameter_count}} parameters")

# Initialize optimizer based on selection
def create_optimizer(optimizer_name: str) -> object:
    \"\"\"
    Create and configure the selected optimizer
    
    Args:
        optimizer_name: Name of the optimizer to create
        
    Returns:
        Configured optimizer instance
    \"\"\"
    optimizers = {{
        "COBYLA": COBYLA(
            maxiter=max_iterations,
            tol=tolerance,
            disp={str(options.get('disp', True)).lower()}
        ),
        "SPSA": SPSA(
            maxiter=max_iterations,
            learning_rate=0.01,
            perturbation=0.1
        ),
        "L_BFGS_B": L_BFGS_B(
            maxfun={options.get('maxfun', 1000)},
            ftol=tolerance,
            gtol=tolerance
        ),
        "SLSQP": SLSQP(
            maxiter=max_iterations,
            tol=tolerance,
            disp={str(options.get('disp', True)).lower()}
        )
    }}
    
    if optimizer_name not in optimizers:
        print(f"⚠️ Unknown optimizer {{optimizer_name}}, using COBYLA")
        return optimizers["COBYLA"]
    
    return optimizers[optimizer_name]

# Create the optimizer
optimizer = create_optimizer(optimizer_type)

# Parameter initialization strategy
def initialize_parameters(param_count: int, strategy: str = "random") -> np.ndarray:
    \"\"\"
    Initialize variational parameters
    
    Args:
        param_count: Number of parameters
        strategy: Initialization strategy
        
    Returns:
        Initial parameter values
    \"\"\"
    if strategy == "random":
        # Random initialization in [0, 2π]
        return np.random.uniform(0, 2*np.pi, param_count)
    elif strategy == "zero":
        # Zero initialization
        return np.zeros(param_count)
    elif strategy == "small_random":
        # Small random values around zero
        return np.random.normal(0, 0.1, param_count)
    else:
        return np.random.uniform(0, 2*np.pi, param_count)

# Initialize parameters
initial_params = initialize_parameters(parameter_count, strategy="random")

print(f"Optimizer configured:")
print(f"  - Type: {{optimizer_type}}")
print(f"  - Max iterations: {{max_iterations}}")
print(f"  - Tolerance: {{tolerance}}")
print(f"  - Initial params: {{len(initial_params)}} parameters")
print(f"  - Selection reason: {optimizer_config.get('reason', 'Default selection')}")

# VQE Algorithm Setup
def setup_vqe_algorithm(hamiltonian, ansatz_circuit, optimizer, initial_parameters):
    \"\"\"
    Setup complete VQE algorithm
    
    Args:
        hamiltonian: TFIM Hamiltonian (SparsePauliOp)
        ansatz_circuit: Parameterized quantum circuit
        optimizer: Configured optimizer
        initial_parameters: Initial parameter values
        
    Returns:
        VQE algorithm instance
    \"\"\"
    # Create quantum computer estimator
    estimator = Estimator()
    
    # Create VQE algorithm
    vqe = VQE(
        estimator=estimator,
        ansatz=ansatz_circuit,
        optimizer=optimizer,
        initial_point=initial_parameters
    )
    
    return vqe

# Cost function for monitoring
def cost_function_callback(iteration: int, params: np.ndarray, cost: float):
    \"\"\"
    Callback function to monitor VQE progress
    
    Args:
        iteration: Current iteration
        params: Current parameter values
        cost: Current cost function value
    \"\"\"
    if iteration % 10 == 0:
        print(f"Iteration {{iteration:3d}}: Cost = {{cost:.6f}}")

print("\\nVQE optimizer ready for execution!")
print("Next step: Execute VQE algorithm to find ground state")

# Ready for VQE execution
# vqe_algorithm = setup_vqe_algorithm(hamiltonian, ansatz_circuit, optimizer, initial_params)
# result = vqe_algorithm.compute_minimum_eigenvalue(hamiltonian)
"""
        
        return code


# 测试代码
if __name__ == "__main__":
    tool = TFIMVQEOptimizer()
    
    # 模拟包含VQE配置信息的上下文
    test_context = """
Original Query: Create complete VQE setup for TFIM including model parameters, Hamiltonian construction, and parameterized ansatz circuit for 4 qubits
Current Step: 4

Execution History:
Step 1: TFIMModelGenerator
  Output: Parameters: {'num_qubits': 4, 'coupling_strength': 1.0, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}

Step 2: TFIMHamiltonianBuilder  
  Output: Built TFIM Hamiltonian with 7 Pauli terms

Step 3: TFIMVQECircuitBuilder
  Output: Built VQE circuit with tfim_specific ansatz for 4 qubits
  Ansatz Config: {'type': 'tfim_specific', 'depth': 2, 'entanglement': 'linear', 'parameter_count': 16}

Current State:
  Total Steps: 3
  Code Fragments: 3
  Parameters: num_qubits = 4, ansatz_type = "tfim_specific", ansatz_depth = 2
"""
    
    result = tool.execute(test_context)
    print("Tool Result:")
    print(f"VQE Config: {result.get('vqe_config', 'None')}")
    print(f"Optimizer Config: {result.get('optimizer_config', 'None')}")
    print(f"Code:\n{result.get('code', 'None')[:500]}...")
    print(f"Notes: {result.get('notes', 'None')}")