"""
Qiskit Code Assembler

整合所有VQE组件为单一完整的可执行代码文件。
"""

import sys
import os
from datetime import datetime

# 添加父目录到路径以导入BaseTool
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, List, Tuple
from base_tool import BaseTool
import json


class QiskitCodeAssembler(BaseTool):
    """
    Qiskit代码整合器
    
    功能:
    - 从Memory中读取所有VQE工具的输出
    - 整合为单一完整的可执行代码
    - 基于LLM选择生成确定的optimizer和ansatz配置
    - 移除callback和cost function等不需要的部分
    - 可选择保存为.py文件
    """
    
    def __init__(self):
        super().__init__()
        
    def execute(self, context: str) -> Dict[str, Any]:
        """
        执行代码整合
        
        Args:
            context: 从Memory获取的上下文信息
            
        Returns:
            包含完整代码的结果
        """
        try:
            # 从上下文中提取所有VQE组件配置
            vqe_components = self._extract_all_vqe_components(context)
            
            # 调用LLM确定最终配置
            final_config = self._llm_determine_final_config(context, vqe_components)
            
            # 生成完整的单一代码文件
            complete_code = self._generate_complete_code(vqe_components, final_config)
            
            # 可选保存文件
            file_path = self._save_code_to_file(complete_code, final_config)
            
            return {
                "code": complete_code,
                "vqe_components": vqe_components,
                "final_config": final_config,
                "file_path": file_path,
                "notes": f"Generated complete VQE code for {vqe_components['num_qubits']}-qubit TFIM (saved to {file_path})"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "code": "",
                "notes": f"Failed to assemble VQE code: {str(e)}"
            }
    
    def _extract_all_vqe_components(self, context: str) -> Dict[str, Any]:
        """
        从上下文中提取所有VQE组件配置
        
        Args:
            context: 上下文信息
            
        Returns:
            完整的VQE组件配置字典
        """
        try:
            lines = context.split('\n')
            
            components = {}
            
            # 提取基本参数
            for line in lines:
                if 'num_qubits' in line and ('=' in line or ':' in line):
                    parts = line.split('=' if '=' in line else ':')
                    if len(parts) == 2:
                        try:
                            components['num_qubits'] = int(parts[1].strip().rstrip(',}'))
                        except:
                            pass
                
                elif 'coupling_strength' in line and ('=' in line or ':' in line):
                    parts = line.split('=' if '=' in line else ':')
                    if len(parts) == 2:
                        try:
                            components['coupling_strength'] = float(parts[1].strip().rstrip(',}'))
                        except:
                            pass
                
                elif 'field_strength' in line and ('=' in line or ':' in line):
                    parts = line.split('=' if '=' in line else ':')
                    if len(parts) == 2:
                        try:
                            components['field_strength'] = float(parts[1].strip().rstrip(',}'))
                        except:
                            pass
                
                elif 'ansatz_type' in line and ('=' in line or ':' in line):
                    parts = line.split('=' if '=' in line else ':')
                    if len(parts) == 2:
                        ansatz_type = parts[1].strip().strip('\"\'').rstrip(',}')
                        components['ansatz_type'] = ansatz_type
                
                elif 'ansatz_depth' in line and ('=' in line or ':' in line):
                    parts = line.split('=' if '=' in line else ':')
                    if len(parts) == 2:
                        try:
                            components['ansatz_depth'] = int(parts[1].strip().rstrip(',}'))
                        except:
                            pass
                
                elif 'optimizer_type' in line and ('=' in line or ':' in line):
                    parts = line.split('=' if '=' in line else ':')
                    if len(parts) == 2:
                        optimizer_type = parts[1].strip().strip('\"\'').rstrip(',}')
                        components['optimizer_type'] = optimizer_type
                
                elif 'parameter_count' in line and (':' in line or '=' in line):
                    parts = line.split(':' if ':' in line else '=')
                    if len(parts) == 2:
                        try:
                            components['parameter_count'] = int(parts[1].strip().rstrip(',}'))
                        except:
                            pass
                
                elif 'entanglement' in line and (':' in line or '=' in line):
                    parts = line.split(':' if ':' in line else '=')
                    if len(parts) == 2:
                        entanglement = parts[1].strip().strip('\"\'').rstrip(',}')
                        components['entanglement'] = entanglement
            
            # 设置默认值
            components.setdefault('num_qubits', 4)
            components.setdefault('coupling_strength', 1.0)
            components.setdefault('field_strength', 1.0)
            components.setdefault('ansatz_type', 'tfim_specific')
            components.setdefault('ansatz_depth', 2)
            components.setdefault('optimizer_type', 'L_BFGS_B')
            components.setdefault('parameter_count', components['num_qubits'] * 2)
            components.setdefault('entanglement', 'linear')
            
            return components
            
        except Exception as e:
            print(f"⚠️ Failed to extract VQE components: {e}")
            # 返回默认配置
            return {
                "num_qubits": 4,
                "coupling_strength": 1.0,
                "field_strength": 1.0,
                "ansatz_type": "tfim_specific",
                "ansatz_depth": 2,
                "optimizer_type": "L_BFGS_B", 
                "parameter_count": 8,
                "entanglement": "linear"
            }
    
    def _llm_determine_final_config(self, context: str, vqe_components: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM确定最终配置
        
        Args:
            context: 上下文信息
            vqe_components: VQE组件配置
            
        Returns:
            最终配置字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Based on the VQE execution context, determine the final optimal configuration for code generation:

VQE Components:
- Problem: {vqe_components['num_qubits']}-qubit TFIM
- Coupling strength (J): {vqe_components['coupling_strength']}
- Field strength (h): {vqe_components['field_strength']}
- Ansatz type: {vqe_components['ansatz_type']}
- Ansatz depth: {vqe_components['ansatz_depth']}
- Optimizer: {vqe_components['optimizer_type']}
- Parameters: {vqe_components['parameter_count']}

Requirements:
- Generate single complete code file
- No callback functions or cost monitoring
- Use StatevectorEstimator for exact simulation
- Simple VQE execution: vqe.compute_minimum_eigenvalue(hamiltonian)
- Include only the selected ansatz and optimizer

Respond with ONLY a JSON object:
{{
    "file_name": "<descriptive_filename>",
    "estimator_type": "StatevectorEstimator",
    "include_monitoring": false,
    "include_callback": false,
    "code_style": "simple",
    "save_file": true
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
            
            final_config = json.loads(response)
            return final_config
            
        except Exception as e:
            print(f"⚠️ Failed to determine final config via LLM: {e}")
            
            # 回退到默认配置
            return {
                "file_name": f"tfim_vqe_{vqe_components['num_qubits']}qubit",
                "estimator_type": "StatevectorEstimator",
                "include_monitoring": False,
                "include_callback": False,
                "code_style": "simple",
                "save_file": True
            }
    
    def _generate_complete_code(self, vqe_components: Dict[str, Any], final_config: Dict[str, Any]) -> str:
        """
        生成完整的VQE代码
        
        Args:
            vqe_components: VQE组件配置
            final_config: 最终配置
            
        Returns:
            完整的Python代码
        """
        num_qubits = vqe_components['num_qubits']
        coupling_strength = vqe_components['coupling_strength']
        field_strength = vqe_components['field_strength']
        ansatz_type = vqe_components['ansatz_type']
        ansatz_depth = vqe_components['ansatz_depth']
        optimizer_type = vqe_components['optimizer_type']
        entanglement = vqe_components['entanglement']
        
        # 生成时间戳和头部信息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        code = f"""# Complete TFIM VQE Implementation
# Generated by QuantumForge V4 on {timestamp}
# Problem: {num_qubits}-qubit TFIM with J={coupling_strength}, h={field_strength}

from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import {optimizer_type}
from qiskit.primitives import {final_config['estimator_type']}
from qiskit.quantum_info import SparsePauliOp
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
import numpy as np

print("🚀 TFIM VQE Ground State Energy Calculation")
print("=" * 50)

# === TFIM Model Parameters ===
num_qubits = {num_qubits}
coupling_strength = {coupling_strength}  # J parameter
field_strength = {field_strength}        # h parameter

print(f"TFIM Model: {{num_qubits}} qubits, J={{coupling_strength}}, h={{field_strength}}")

# === Build TFIM Hamiltonian ===
def build_tfim_hamiltonian(n_qubits: int, J: float, h: float) -> SparsePauliOp:
    \"\"\"
    Build TFIM Hamiltonian: H = -J * ∑ZZ - h * ∑X
    
    Args:
        n_qubits: Number of qubits
        J: Coupling strength
        h: Transverse field strength
        
    Returns:
        TFIM Hamiltonian as SparsePauliOp
    \"\"\"
    pauli_terms = []
    
    # Transverse field terms (X gates)
    for i in range(n_qubits):
        pauli_string = 'I' * n_qubits
        pauli_string = pauli_string[:i] + 'X' + pauli_string[i+1:]
        pauli_terms.append((pauli_string, -h))
    
    # Ising coupling terms (ZZ gates)
    for i in range(n_qubits - 1):
        pauli_string = 'I' * n_qubits
        pauli_string = pauli_string[:i] + 'Z' + pauli_string[i+1:]
        pauli_string = pauli_string[:i+1] + 'Z' + pauli_string[i+2:]
        pauli_terms.append((pauli_string, -J))
    
    return SparsePauliOp.from_list(pauli_terms)

hamiltonian = build_tfim_hamiltonian(num_qubits, coupling_strength, field_strength)
print(f"Hamiltonian: {{len(hamiltonian.paulis)}} Pauli terms")

# === Create VQE Ansatz ==="""

        # 根据选择的ansatz类型生成对应代码
        if ansatz_type == "tfim_specific":
            code += f"""
def create_tfim_ansatz(n_qubits: int, depth: int) -> QuantumCircuit:
    \"\"\"
    Create TFIM-specific ansatz with X rotations and ZZ entangling gates
    
    Args:
        n_qubits: Number of qubits
        depth: Circuit depth
        
    Returns:
        Parameterized quantum circuit
    \"\"\"
    qc = QuantumCircuit(n_qubits)
    
    for layer in range(depth):
        # X rotation layer (transverse field related)
        for qubit in range(n_qubits):
            theta = Parameter(f'rx_{{layer}}_{{qubit}}')
            qc.rx(theta, qubit)
        
        # ZZ entangling layer (coupling related)
        if "{entanglement}" == "linear":
            for qubit in range(n_qubits - 1):
                phi = Parameter(f'rzz_{{layer}}_{{qubit}}')
                qc.cx(qubit, qubit + 1)
                qc.rz(phi, qubit + 1)
                qc.cx(qubit, qubit + 1)
    
    # Final X rotation layer
    for qubit in range(n_qubits):
        theta = Parameter(f'rx_final_{{qubit}}')
        qc.rx(theta, qubit)
    
    return qc"""
        else:  # hardware_efficient
            code += f"""
def create_hardware_efficient_ansatz(n_qubits: int, depth: int) -> QuantumCircuit:
    \"\"\"
    Create hardware-efficient ansatz with RY rotations and CNOT gates
    
    Args:
        n_qubits: Number of qubits
        depth: Circuit depth
        
    Returns:
        Parameterized quantum circuit
    \"\"\"
    qc = QuantumCircuit(n_qubits)
    
    for layer in range(depth):
        # RY rotation layer
        for qubit in range(n_qubits):
            theta = Parameter(f'ry_{{layer}}_{{qubit}}')
            qc.ry(theta, qubit)
        
        # CNOT entangling layer
        if "{entanglement}" == "linear":
            for qubit in range(n_qubits - 1):
                qc.cx(qubit, qubit + 1)
    
    # Final RY rotation layer
    for qubit in range(n_qubits):
        theta = Parameter(f'ry_final_{{qubit}}')
        qc.ry(theta, qubit)
    
    return qc"""

        # 根据ansatz类型选择函数调用
        ansatz_function = "create_tfim_ansatz" if ansatz_type == "tfim_specific" else "create_hardware_efficient_ansatz"
        
        code += f"""

ansatz = {ansatz_function}(num_qubits, {ansatz_depth})
print(f"Ansatz: {{ansatz.depth()}} depth, {{len(ansatz.parameters)}} parameters")

# === Configure Optimizer ===
optimizer = {optimizer_type}()
print(f"Optimizer: {optimizer_type}")

# === Initialize Parameters ===
initial_point = np.random.uniform(0, 2*np.pi, len(ansatz.parameters))

# === Setup and Execute VQE ===
estimator = {final_config['estimator_type']}()
vqe = VQE(estimator, ansatz, optimizer)

print("\\nExecuting VQE algorithm...")
vqe_result = vqe.compute_minimum_eigenvalue(hamiltonian)
ground_state_energy = vqe_result.eigenvalue.real

# === Results ===
print("\\n" + "=" * 50)
print("🎯 VQE Results:")
print(f"Ground State Energy: {{ground_state_energy:.8f}}")
print(f"Optimizer Evaluations: {{vqe_result.cost_function_evals}}")
print(f"Optimal Parameters: {{len(vqe_result.optimal_parameters)}} values")
print("=" * 50)

# Final result
print(f"\\n✅ TFIM {num_qubits}-qubit ground state energy: {{ground_state_energy:.8f}}")
"""
        
        return code
    
    def _save_code_to_file(self, code: str, final_config: Dict[str, Any]) -> str:
        """
        保存代码到文件
        
        Args:
            code: 完整代码
            final_config: 最终配置
            
        Returns:
            保存的文件路径
        """
        try:
            if not final_config.get('save_file', True):
                return "not_saved"
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{final_config.get('file_name', 'tfim_vqe')}_{timestamp}.py"
            
            # 确定保存路径（当前目录）
            file_path = os.path.join(os.getcwd(), filename)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            print(f"💾 Code saved to: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"⚠️ Failed to save file: {e}")
            return "save_failed"


# 测试代码
if __name__ == "__main__":
    tool = QiskitCodeAssembler()
    
    # 模拟包含完整VQE流程的上下文
    test_context = """
Original Query: Calculate the ground state energy of a 4-qubit TFIM with coupling strength of 1.5
Current Step: 6

Execution History:
Step 1: TFIMModelGenerator
  Output: Parameters: {'num_qubits': 4, 'coupling_strength': 1.5, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}

Step 2: TFIMHamiltonianBuilder  
  Output: Built TFIM Hamiltonian with 7 Pauli terms

Step 3: TFIMVQECircuitBuilder
  Output: Built VQE circuit with tfim_specific ansatz for 4 qubits
  Ansatz Config: {'type': 'tfim_specific', 'depth': 2, 'entanglement': 'linear', 'parameter_count': 16}

Step 4: TFIMVQEOptimizer
  Output: Configured VQE with L_BFGS_B optimizer for 4-qubit TFIM

Step 5: QiskitTFIMExecutor
  Output: Generated complete VQE execution

Current State:
  Total Steps: 5
  Code Fragments: 5
  Parameters: num_qubits = 4, coupling_strength = 1.5, ansatz_type = "tfim_specific", optimizer_type = "L_BFGS_B"
"""
    
    result = tool.execute(test_context)
    print("Tool Result:")
    print(f"VQE Components: {result.get('vqe_components', 'None')}")
    print(f"Final Config: {result.get('final_config', 'None')}")
    print(f"File Path: {result.get('file_path', 'None')}")
    print(f"Code Length: {len(result.get('code', ''))} characters")
    print(f"Notes: {result.get('notes', 'None')}")