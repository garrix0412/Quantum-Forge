"""
Qiskit TFIM Executor

执行完整的TFIM VQE算法，计算基态能量。
"""

import sys
import os

# 添加父目录到路径以导入BaseTool
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, List, Tuple
from base_tool import BaseTool
import json


class QiskitTFIMExecutor(BaseTool):
    """
    Qiskit TFIM执行器
    
    功能:
    - 从Memory中读取所有VQE组件配置
    - 调用LLM分析执行策略和参数
    - 整合Hamiltonian、ansatz、optimizer执行VQE
    - 输出基态能量和完整的执行代码
    """
    
    def __init__(self):
        super().__init__()
        
    def execute(self, context: str) -> Dict[str, Any]:
        """
        执行TFIM VQE算法
        
        Args:
            context: 从Memory获取的上下文信息
            
        Returns:
            包含VQE执行代码和结果的字典
        """
        try:
            # 从上下文中提取VQE组件配置
            vqe_components = self._extract_vqe_components_from_context(context)
            
            if not vqe_components:
                # 如果没有找到配置，调用LLM分析
                vqe_components = self._llm_extract_vqe_components(context)
            
            # 调用LLM确定执行策略
            execution_config = self._llm_configure_execution(context, vqe_components)
            
            # 生成完整的VQE执行代码
            code = self._generate_vqe_execution_code(vqe_components, execution_config)
            
            return {
                "code": code,
                "vqe_components": vqe_components,
                "execution_config": execution_config,
                "notes": f"Generated complete VQE execution for {vqe_components['num_qubits']}-qubit TFIM with {execution_config['estimator_type']} estimator"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "code": "",
                "notes": f"Failed to execute TFIM VQE: {str(e)}"
            }
    
    def _extract_vqe_components_from_context(self, context: str) -> Dict[str, Any]:
        """
        从上下文中提取VQE组件配置
        
        Args:
            context: 上下文信息
            
        Returns:
            VQE组件配置字典，如果没有找到返回None
        """
        try:
            lines = context.split('\n')
            
            components = {}
            
            # 提取基本参数
            for line in lines:
                if 'num_qubits' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            components['num_qubits'] = int(parts[1].strip())
                        except:
                            pass
                
                elif 'coupling_strength' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            components['coupling_strength'] = float(parts[1].strip())
                        except:
                            pass
                
                elif 'field_strength' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            components['field_strength'] = float(parts[1].strip())
                        except:
                            pass
                
                elif 'ansatz_type' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        ansatz_type = parts[1].strip().strip('\"\'')
                        components['ansatz_type'] = ansatz_type
                
                elif 'ansatz_depth' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            components['ansatz_depth'] = int(parts[1].strip())
                        except:
                            pass
                
                elif 'optimizer_type' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        optimizer_type = parts[1].strip().strip('\"\'')
                        components['optimizer_type'] = optimizer_type
                
                elif 'parameter_count' in line and (':' in line or '=' in line):
                    # 处理 "parameter_count": 24 或 parameter_count = 24
                    if ':' in line:
                        parts = line.split(':')
                    else:
                        parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            components['parameter_count'] = int(parts[1].strip().rstrip(',}'))
                        except:
                            pass
                
                elif 'max_iterations' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            components['max_iterations'] = int(parts[1].strip())
                        except:
                            pass
            
            # 检查是否获取到了足够的信息
            required_keys = ['num_qubits']
            if all(key in components for key in required_keys):
                # 设置默认值
                components.setdefault('coupling_strength', 1.0)
                components.setdefault('field_strength', 1.0)
                components.setdefault('ansatz_type', 'tfim_specific')
                components.setdefault('ansatz_depth', 2)
                components.setdefault('optimizer_type', 'L_BFGS_B')
                components.setdefault('parameter_count', components['num_qubits'] * 2)
                components.setdefault('max_iterations', 200)
                return components
            
            return None
            
        except Exception as e:
            print(f"⚠️ Failed to extract VQE components from context: {e}")
            return None
    
    def _llm_extract_vqe_components(self, context: str) -> Dict[str, Any]:
        """
        使用LLM从上下文中提取VQE组件配置
        
        Args:
            context: 上下文信息
            
        Returns:
            VQE组件配置字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Based on the execution history below, extract all VQE components for final execution:

{context}

Please analyze the previous tool outputs and extract:
- num_qubits: number of qubits
- coupling_strength: J parameter
- field_strength: h parameter  
- ansatz_type: type of ansatz (hardware_efficient, tfim_specific, etc.)
- ansatz_depth: circuit depth
- optimizer_type: optimizer name (COBYLA, L_BFGS_B, etc.)
- parameter_count: number of variational parameters
- max_iterations: maximum optimization iterations

Respond with ONLY a JSON object:
{{
    "num_qubits": <number>,
    "coupling_strength": <float>,
    "field_strength": <float>,
    "ansatz_type": "<string>",
    "ansatz_depth": <number>,
    "optimizer_type": "<string>",
    "parameter_count": <number>,
    "max_iterations": <number>
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
            
            components = json.loads(response)
            return components
            
        except Exception as e:
            print(f"⚠️ Failed to extract VQE components via LLM: {e}")
            
            # 回退到默认配置
            return {
                "num_qubits": 4,
                "coupling_strength": 1.0,
                "field_strength": 1.0,
                "ansatz_type": "tfim_specific",
                "ansatz_depth": 2,
                "optimizer_type": "L_BFGS_B",
                "parameter_count": 8,
                "max_iterations": 200
            }
    
    def _llm_configure_execution(self, context: str, vqe_components: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM配置VQE执行策略
        
        Args:
            context: 上下文信息
            vqe_components: VQE组件配置
            
        Returns:
            执行配置字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Configure VQE execution strategy for the following TFIM problem:

VQE Components:
- Number of qubits: {vqe_components['num_qubits']}
- Parameter count: {vqe_components['parameter_count']}
- Ansatz type: {vqe_components['ansatz_type']}
- Optimizer: {vqe_components['optimizer_type']}
- Max iterations: {vqe_components['max_iterations']}

Available estimators:
1. "StatevectorEstimator": Exact simulation, good for small systems (≤10 qubits)
2. "Estimator": General estimator, compatible with backends
3. "SamplerQNN": For noisy simulation

Execution options:
- callback_frequency: How often to print progress (every N iterations)
- initial_point_strategy: "random", "zero", "small_random"
- convergence_tolerance: When to stop optimization early

Respond with ONLY a JSON object:
{{
    "estimator_type": "<estimator_name>",
    "callback_frequency": <number>,
    "initial_point_strategy": "<strategy>",
    "convergence_tolerance": <float>,
    "shots": <number_or_null>,
    "backend": "<backend_name_or_null>",
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
            
            execution_config = json.loads(response)
            return execution_config
            
        except Exception as e:
            print(f"⚠️ Failed to configure execution via LLM: {e}")
            
            # 回退到默认配置
            num_qubits = vqe_components['num_qubits']
            return {
                "estimator_type": "StatevectorEstimator" if num_qubits <= 10 else "Estimator",
                "callback_frequency": 10,
                "initial_point_strategy": "random",
                "convergence_tolerance": 1e-6,
                "shots": None,
                "backend": None,
                "reason": f"Default configuration for {num_qubits}-qubit system"
            }
    
    def _generate_vqe_execution_code(self, vqe_components: Dict[str, Any], execution_config: Dict[str, Any]) -> str:
        """
        生成完整的VQE执行代码
        
        Args:
            vqe_components: VQE组件配置
            execution_config: 执行配置
            
        Returns:
            生成的Python代码
        """
        num_qubits = vqe_components['num_qubits']
        coupling_strength = vqe_components['coupling_strength']
        field_strength = vqe_components['field_strength']
        ansatz_type = vqe_components['ansatz_type']
        ansatz_depth = vqe_components['ansatz_depth']
        optimizer_type = vqe_components['optimizer_type']
        parameter_count = vqe_components['parameter_count']
        max_iterations = vqe_components['max_iterations']
        
        estimator_type = execution_config['estimator_type']
        callback_freq = execution_config['callback_frequency']
        init_strategy = execution_config['initial_point_strategy']
        tolerance = execution_config['convergence_tolerance']
        
        code = f"""# Complete TFIM VQE Execution
# Generated by QuantumForge V4

from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA, SPSA, L_BFGS_B, SLSQP
from qiskit.primitives import StatevectorEstimator, Estimator
from qiskit.quantum_info import SparsePauliOp
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
import numpy as np
import time

print("🚀 Starting Complete TFIM VQE Execution")
print("=" * 50)

# === STEP 1: TFIM Model Parameters ===
print("\\n📋 TFIM Model Configuration:")
num_qubits = {num_qubits}
coupling_strength = {coupling_strength}  # J parameter
field_strength = {field_strength}        # h parameter
topology = "linear"
boundary_conditions = "open"

print(f"  - Qubits: {{num_qubits}}")
print(f"  - Coupling (J): {{coupling_strength}}")
print(f"  - Field (h): {{field_strength}}")
print(f"  - Topology: {{topology}}")

# === STEP 2: Build TFIM Hamiltonian ===
print("\\n🔨 Building TFIM Hamiltonian:")

def build_tfim_hamiltonian(num_qubits: int, J: float, h: float) -> SparsePauliOp:
    \"\"\"Build TFIM Hamiltonian: H = -J * ∑ZZ - h * ∑X\"\"\"
    pauli_terms = []
    
    # Transverse field terms (X gates)
    for i in range(num_qubits):
        pauli_string = 'I' * num_qubits
        pauli_string = pauli_string[:i] + 'X' + pauli_string[i+1:]
        pauli_terms.append((pauli_string, -h))
    
    # Ising coupling terms (ZZ gates)
    for i in range(num_qubits - 1):
        pauli_string = 'I' * num_qubits
        pauli_string = pauli_string[:i] + 'Z' + pauli_string[i+1:]
        pauli_string = pauli_string[:i+1] + 'Z' + pauli_string[i+2:]
        pauli_terms.append((pauli_string, -J))
    
    return SparsePauliOp.from_list(pauli_terms)

hamiltonian = build_tfim_hamiltonian(num_qubits, coupling_strength, field_strength)
print(f"  - Pauli terms: {{len(hamiltonian.paulis)}}")
print(f"  - Hamiltonian norm: {{hamiltonian.norm():.4f}}")

# === STEP 3: Create VQE Ansatz ===
print("\\n🔧 Creating VQE Ansatz:")
ansatz_type = "{ansatz_type}"
ansatz_depth = {ansatz_depth}

def create_tfim_ansatz(num_qubits: int, depth: int) -> QuantumCircuit:
    \"\"\"Create TFIM-specific ansatz with X rotations and ZZ entanglers\"\"\"
    qc = QuantumCircuit(num_qubits)
    parameters = []
    
    for layer in range(depth):
        # X rotation layer (transverse field related)
        for qubit in range(num_qubits):
            theta = Parameter(f'rx_{{layer}}_{{qubit}}')
            parameters.append(theta)
            qc.rx(theta, qubit)
        
        # ZZ entangling layer (coupling related)
        for qubit in range(num_qubits - 1):
            phi = Parameter(f'rzz_{{layer}}_{{qubit}}')
            parameters.append(phi)
            qc.cx(qubit, qubit + 1)
            qc.rz(phi, qubit + 1)
            qc.cx(qubit, qubit + 1)
    
    # Final X rotation layer
    for qubit in range(num_qubits):
        theta = Parameter(f'rx_final_{{qubit}}')
        parameters.append(theta)
        qc.rx(theta, qubit)
    
    return qc

ansatz = create_tfim_ansatz(num_qubits, ansatz_depth)
print(f"  - Ansatz type: {{ansatz_type}}")
print(f"  - Circuit depth: {{ansatz.depth()}}")
print(f"  - Parameters: {{len(ansatz.parameters)}}")
print(f"  - Gates: {{ansatz.count_ops()}}")

# === STEP 4: Configure Optimizer ===
print("\\n⚙️ Configuring Optimizer:")
optimizer_name = "{optimizer_type}"
max_iter = {max_iterations}

def create_optimizer(name: str):
    optimizers = {{
        "COBYLA": COBYLA(maxiter=max_iter, tol={tolerance}),
        "SPSA": SPSA(maxiter=max_iter),
        "L_BFGS_B": L_BFGS_B(maxfun=max_iter*10, ftol={tolerance}),
        "SLSQP": SLSQP(maxiter=max_iter, tol={tolerance})
    }}
    return optimizers.get(name, optimizers["COBYLA"])

optimizer = create_optimizer(optimizer_name)
print(f"  - Optimizer: {{optimizer_name}}")
print(f"  - Max iterations: {{max_iter}}")
print(f"  - Tolerance: {tolerance}")

# === STEP 5: Initialize Parameters ===
print("\\n🎲 Initializing Parameters:")
param_count = len(ansatz.parameters)
init_strategy = "{init_strategy}"

def initialize_parameters(count: int, strategy: str) -> np.ndarray:
    if strategy == "random":
        return np.random.uniform(0, 2*np.pi, count)
    elif strategy == "zero":
        return np.zeros(count)
    elif strategy == "small_random":
        return np.random.normal(0, 0.1, count)
    else:
        return np.random.uniform(0, 2*np.pi, count)

initial_point = initialize_parameters(param_count, init_strategy)
print(f"  - Strategy: {{init_strategy}}")
print(f"  - Parameter count: {{param_count}}")
print(f"  - Initial point range: [{{initial_point.min():.3f}}, {{initial_point.max():.3f}}]")

# === STEP 6: Setup VQE Algorithm ===
print("\\n🧮 Setting up VQE Algorithm:")
estimator_type = "{estimator_type}"

# Create estimator
if estimator_type == "StatevectorEstimator":
    estimator = StatevectorEstimator()
else:
    estimator = Estimator()

print(f"  - Estimator: {{estimator_type}}")

# Progress callback
iteration_count = 0
start_time = time.time()
energy_history = []

def vqe_callback(eval_count, parameters, mean, std):
    global iteration_count, start_time, energy_history
    iteration_count = eval_count
    energy_history.append(mean)
    
    if eval_count % {callback_freq} == 0:
        elapsed = time.time() - start_time
        print(f"  Iteration {{eval_count:3d}}: Energy = {{mean:.8f}} ({{elapsed:.1f}}s)")

# Create VQE instance
vqe = VQE(
    estimator=estimator,
    ansatz=ansatz,
    optimizer=optimizer,
    initial_point=initial_point,
    callback=vqe_callback
)

print("  - VQE algorithm configured ✓")

# === STEP 7: Execute VQE ===
print("\\n🏃 Executing VQE Algorithm:")
print(f"  Target: Find ground state energy of {{num_qubits}}-qubit TFIM")
print(f"  Expected runtime: ~{{max_iter//10}}-{{max_iter//5}} seconds")
print()

# Run VQE
execution_start = time.time()
try:
    vqe_result = vqe.compute_minimum_eigenvalue(hamiltonian)
    execution_time = time.time() - execution_start
    
    # Extract results
    ground_state_energy = vqe_result.eigenvalue.real
    optimal_parameters = vqe_result.optimal_parameters
    optimizer_evals = vqe_result.cost_function_evals
    
    # === STEP 8: Results Analysis ===
    print("\\n📊 VQE Results:")
    print("=" * 50)
    print(f"✅ Ground State Energy: {{ground_state_energy:.8f}}")
    print(f"🔄 Optimizer Evaluations: {{optimizer_evals}}")
    print(f"⏱️  Execution Time: {{execution_time:.2f}} seconds")
    print(f"📈 Final Convergence: {{energy_history[-1]:.8f}}")
    print(f"🎯 Parameter Count: {{len(optimal_parameters)}}")
    
    # Theoretical comparison (for small systems)
    if num_qubits <= 6:
        print(f"\\n🧮 Theoretical Reference:")
        print(f"  - For TFIM with J={{coupling_strength}}, h={{field_strength}}")
        print(f"  - Exact diagonalization would give precise ground state")
        print(f"  - VQE approximation: {{ground_state_energy:.8f}}")
    
    print(f"\\n🎉 VQE execution completed successfully!")
    print(f"📝 Ground state energy for {{num_qubits}}-qubit TFIM: {{ground_state_energy:.8f}}")
    
except Exception as e:
    print(f"❌ VQE execution failed: {{e}}")
    ground_state_energy = None

# === Summary ===
print("\\n" + "=" * 50)
print("📋 Execution Summary:")
print(f"  - Problem: {{num_qubits}}-qubit TFIM (J={{coupling_strength}}, h={{field_strength}})")
print(f"  - Method: VQE with {{ansatz_type}} ansatz")
print(f"  - Optimizer: {{optimizer_name}} ({{optimizer_evals if 'optimizer_evals' in locals() else 'N/A'}} evaluations)")
print(f"  - Result: {{ground_state_energy if ground_state_energy else 'Failed'}}")
print(f"  - Status: {{'Success' if ground_state_energy else 'Failed'}}")
print("=" * 50)
"""
        
        return code


# 测试代码
if __name__ == "__main__":
    tool = QiskitTFIMExecutor()
    
    # 模拟包含完整VQE配置的上下文
    test_context = """
Original Query: Calculate the ground state energy of a 6-qubit TFIM with strong coupling strength of 2.0 using VQE algorithm
Current Step: 5

Execution History:
Step 1: TFIMModelGenerator
  Output: Parameters: {'num_qubits': 6, 'coupling_strength': 2.0, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}

Step 2: TFIMHamiltonianBuilder  
  Output: Built TFIM Hamiltonian with 11 Pauli terms

Step 3: TFIMVQECircuitBuilder
  Output: Built VQE circuit with tfim_specific ansatz for 6 qubits
  Ansatz Config: {'type': 'tfim_specific', 'depth': 2, 'entanglement': 'linear', 'parameter_count': 24}

Step 4: TFIMVQEOptimizer
  Output: Configured VQE with L_BFGS_B optimizer for 6-qubit TFIM
  Optimizer Config: {'type': 'L_BFGS_B', 'max_iterations': 1000, 'tolerance': 0.0001}

Current State:
  Total Steps: 4
  Code Fragments: 4
  Parameters: num_qubits = 6, coupling_strength = 2.0, ansatz_type = "tfim_specific", optimizer_type = "L_BFGS_B"
"""
    
    result = tool.execute(test_context)
    print("Tool Result:")
    print(f"VQE Components: {result.get('vqe_components', 'None')}")
    print(f"Execution Config: {result.get('execution_config', 'None')}")
    print(f"Code Length: {len(result.get('code', ''))} characters")
    print(f"Notes: {result.get('notes', 'None')}")