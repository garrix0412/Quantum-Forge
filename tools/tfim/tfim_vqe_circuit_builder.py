"""
TFIM VQE Circuit Builder

构建用于TFIM VQE算法的ansatz量子线路。
"""

import sys
import os

# 添加父目录到路径以导入BaseTool
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, List, Tuple
from base_tool import BaseTool
import json


class TFIMVQECircuitBuilder(BaseTool):
    """
    TFIM VQE线路构建器
    
    功能:
    - 从Memory中读取TFIM模型参数和哈密顿量信息
    - 调用LLM分析并选择合适的ansatz类型
    - 生成VQE ansatz量子线路的Qiskit代码
    """
    
    def __init__(self):
        super().__init__()
        
    def execute(self, context: str) -> Dict[str, Any]:
        """
        执行TFIM VQE线路构建
        
        Args:
            context: 从Memory获取的上下文信息
            
        Returns:
            包含VQE线路代码的结果
        """
        try:
            # 从上下文中提取TFIM参数
            parameters = self._extract_parameters_from_context(context)
            
            if not parameters:
                # 如果没有找到参数，调用LLM分析
                parameters = self._llm_extract_parameters(context)
            
            # 调用LLM选择ansatz类型
            ansatz_config = self._llm_select_ansatz(context, parameters)
            
            # 生成VQE线路代码
            code = self._generate_vqe_circuit_code(parameters, ansatz_config)
            
            return {
                "code": code,
                "parameters": parameters,
                "ansatz_config": ansatz_config,
                "notes": f"Built VQE circuit with {ansatz_config['type']} ansatz for {parameters['num_qubits']} qubits"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "code": "",
                "notes": f"Failed to build VQE circuit: {str(e)}"
            }
    
    def _extract_parameters_from_context(self, context: str) -> Dict[str, Any]:
        """
        从上下文中提取已有的TFIM参数
        
        Args:
            context: 上下文信息
            
        Returns:
            TFIM参数字典，如果没有找到返回None
        """
        try:
            # 查找上下文中的参数信息
            lines = context.split('\n')
            
            parameters = {}
            for line in lines:
                if 'num_qubits' in line and '=' in line:
                    # 提取 num_qubits = 4 这种格式
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            parameters['num_qubits'] = int(parts[1].strip())
                        except:
                            pass
                
                elif 'coupling_strength' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            parameters['coupling_strength'] = float(parts[1].strip())
                        except:
                            pass
                
                elif 'field_strength' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        try:
                            parameters['field_strength'] = float(parts[1].strip())
                        except:
                            pass
                
                elif 'topology' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        topology = parts[1].strip().strip('"\'')
                        parameters['topology'] = topology
                
                elif 'boundary_conditions' in line and '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        boundary = parts[1].strip().strip('"\'')
                        parameters['boundary_conditions'] = boundary
            
            # 检查是否获取到了足够的参数
            required_keys = ['num_qubits']
            if all(key in parameters for key in required_keys):
                # 设置默认值
                parameters.setdefault('coupling_strength', 1.0)
                parameters.setdefault('field_strength', 1.0)
                parameters.setdefault('topology', 'linear')
                parameters.setdefault('boundary_conditions', 'open')
                return parameters
            
            return None
            
        except Exception as e:
            print(f"⚠️ Failed to extract parameters from context: {e}")
            return None
    
    def _llm_extract_parameters(self, context: str) -> Dict[str, Any]:
        """
        使用LLM从上下文中提取TFIM参数
        
        Args:
            context: 上下文信息
            
        Returns:
            TFIM参数字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Based on the execution history below, extract the TFIM model parameters for VQE circuit construction:

{context}

Please find and extract TFIM parameters from the previous tool outputs. Look for:
- num_qubits: number of qubits
- coupling_strength: J parameter 
- field_strength: h parameter
- topology: linear/circular/2d_grid
- boundary_conditions: open/periodic

Respond with ONLY a JSON object:
{{
    "num_qubits": <number>,
    "coupling_strength": <float>,
    "field_strength": <float>,
    "topology": "<string>",
    "boundary_conditions": "<string>"
}}

If parameters are not found, use reasonable defaults (4 qubits, J=1.0, h=1.0, linear topology, open boundary).

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
            
            parameters = json.loads(response)
            return parameters
            
        except Exception as e:
            print(f"⚠️ Failed to extract parameters via LLM: {e}")
            
            # 回退到默认参数
            return {
                "num_qubits": 4,
                "coupling_strength": 1.0,
                "field_strength": 1.0,
                "topology": "linear",
                "boundary_conditions": "open"
            }
    
    def _llm_select_ansatz(self, context: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM选择合适的ansatz类型
        
        Args:
            context: 上下文信息
            parameters: TFIM参数
            
        Returns:
            ansatz配置字典
        """
        # 导入LLM调用函数
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core')
        if core_path not in sys.path:
            sys.path.append(core_path)
        from llm_engine import call_llm
        
        prompt = f"""
Based on the TFIM problem parameters below, select the most appropriate VQE ansatz:

TFIM Parameters:
- Number of qubits: {parameters['num_qubits']}
- Coupling strength (J): {parameters['coupling_strength']}
- Field strength (h): {parameters['field_strength']}
- Topology: {parameters['topology']}
- Boundary conditions: {parameters['boundary_conditions']}

Available ansatz types:
1. "hardware_efficient": Hardware-efficient ansatz with RY rotations and CNOT entanglers
2. "tfim_specific": TFIM-specific ansatz with X rotations and ZZ entanglers
3. "real_amplitudes": Real amplitudes ansatz (no phase rotations)

Guidelines:
- For small systems (≤6 qubits): hardware_efficient with depth 2-3
- For TFIM-specific problems: tfim_specific ansatz
- For larger systems (>6 qubits): real_amplitudes with depth 1-2

Respond with ONLY a JSON object:
{{
    "type": "<ansatz_type>",
    "depth": <number>,
    "entanglement": "<linear|circular|full>",
    "parameter_count": <estimated_number>
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
            
            ansatz_config = json.loads(response)
            return ansatz_config
            
        except Exception as e:
            print(f"⚠️ Failed to select ansatz via LLM: {e}")
            
            # 回退到默认ansatz
            num_qubits = parameters['num_qubits']
            return {
                "type": "hardware_efficient",
                "depth": 2 if num_qubits <= 6 else 1,
                "entanglement": "linear",
                "parameter_count": num_qubits * 2  # 估算
            }
    
    def _generate_vqe_circuit_code(self, parameters: Dict[str, Any], ansatz_config: Dict[str, Any]) -> str:
        """
        生成VQE线路代码
        
        Args:
            parameters: TFIM参数
            ansatz_config: ansatz配置
            
        Returns:
            生成的Python代码
        """
        num_qubits = parameters['num_qubits']
        ansatz_type = ansatz_config['type']
        depth = ansatz_config['depth']
        entanglement = ansatz_config.get('entanglement', 'linear')
        
        code = f"""# TFIM VQE Circuit Construction
# Generated by QuantumForge V4

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
import numpy as np

# TFIM Parameters (from previous steps)
num_qubits = {num_qubits}
coupling_strength = {parameters['coupling_strength']}  # J parameter
field_strength = {parameters['field_strength']}        # h parameter
topology = "{parameters['topology']}"
boundary_conditions = "{parameters['boundary_conditions']}"

# VQE Ansatz Configuration
ansatz_type = "{ansatz_type}"
ansatz_depth = {depth}
entanglement_pattern = "{entanglement}"

print(f"Building VQE ansatz: {{ansatz_type}} with depth {{ansatz_depth}}")

# Create parameterized ansatz circuit
def create_tfim_ansatz(num_qubits: int, depth: int) -> QuantumCircuit:
    \"\"\"
    Create VQE ansatz circuit for TFIM
    
    Args:
        num_qubits: Number of qubits
        depth: Circuit depth (number of repetitions)
        
    Returns:
        Parameterized quantum circuit
    \"\"\"
    # Initialize circuit
    qc = QuantumCircuit(num_qubits)
    
    # Parameters for the ansatz
    parameters = []
    
"""
        
        # 根据ansatz类型生成对应的线路构建代码
        if ansatz_type == "hardware_efficient":
            code += self._generate_hardware_efficient_ansatz_code(num_qubits, depth, entanglement)
        elif ansatz_type == "tfim_specific":
            code += self._generate_tfim_specific_ansatz_code(num_qubits, depth, entanglement)
        elif ansatz_type == "real_amplitudes":
            code += self._generate_real_amplitudes_ansatz_code(num_qubits, depth, entanglement)
        else:
            code += self._generate_hardware_efficient_ansatz_code(num_qubits, depth, entanglement)
        
        code += f"""
    return qc, parameters

# Create the ansatz
ansatz_circuit, theta_params = create_tfim_ansatz(num_qubits, ansatz_depth)

print(f"VQE ansatz created:")
print(f"  - Circuit depth: {{ansatz_circuit.depth()}}")
print(f"  - Parameter count: {{len(theta_params)}}")
print(f"  - Entanglement: {{entanglement_pattern}}")
print(f"  - Gates: {{ansatz_circuit.count_ops()}}")

# Ansatz is ready for VQE optimization
# Next step: Set up optimizer and execute VQE
"""
        
        return code
    
    def _generate_hardware_efficient_ansatz_code(self, num_qubits: int, depth: int, entanglement: str) -> str:
        """生成Hardware Efficient ansatz代码"""
        code = """    # Hardware Efficient Ansatz with RY rotations and CNOT gates
    for layer in range(depth):
        # Rotation layer
        for qubit in range(num_qubits):
            theta = Parameter(f'theta_{layer}_{qubit}')
            parameters.append(theta)
            qc.ry(theta, qubit)
        
        # Entanglement layer
        if entanglement_pattern == "linear":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
        elif entanglement_pattern == "circular":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
            if num_qubits > 2:
                qc.cx(num_qubits - 1, 0)  # Close the loop
        elif entanglement_pattern == "full":
            for i in range(num_qubits):
                for j in range(i + 1, num_qubits):
                    qc.cx(i, j)
    
    # Final rotation layer
    for qubit in range(num_qubits):
        theta = Parameter(f'theta_final_{qubit}')
        parameters.append(theta)
        qc.ry(theta, qubit)
"""
        return code
    
    def _generate_tfim_specific_ansatz_code(self, num_qubits: int, depth: int, entanglement: str) -> str:
        """生成TFIM-specific ansatz代码"""
        code = """    # TFIM-specific ansatz with X rotations and ZZ gates
    for layer in range(depth):
        # X rotation layer (related to transverse field)
        for qubit in range(num_qubits):
            theta = Parameter(f'rx_{layer}_{qubit}')
            parameters.append(theta)
            qc.rx(theta, qubit)
        
        # ZZ interaction layer (related to Ising coupling)
        if entanglement_pattern == "linear":
            for qubit in range(num_qubits - 1):
                phi = Parameter(f'rzz_{layer}_{qubit}')
                parameters.append(phi)
                qc.cx(qubit, qubit + 1)
                qc.rz(phi, qubit + 1)
                qc.cx(qubit, qubit + 1)
        elif entanglement_pattern == "circular":
            for qubit in range(num_qubits):
                next_qubit = (qubit + 1) % num_qubits
                phi = Parameter(f'rzz_{layer}_{qubit}')
                parameters.append(phi)
                qc.cx(qubit, next_qubit)
                qc.rz(phi, next_qubit)
                qc.cx(qubit, next_qubit)
    
    # Final X rotation layer
    for qubit in range(num_qubits):
        theta = Parameter(f'rx_final_{qubit}')
        parameters.append(theta)
        qc.rx(theta, qubit)
"""
        return code
    
    def _generate_real_amplitudes_ansatz_code(self, num_qubits: int, depth: int, entanglement: str) -> str:
        """生成Real Amplitudes ansatz代码"""
        code = """    # Real Amplitudes ansatz (no phase rotations)
    for layer in range(depth):
        # RY rotation layer
        for qubit in range(num_qubits):
            theta = Parameter(f'ry_{layer}_{qubit}')
            parameters.append(theta)
            qc.ry(theta, qubit)
        
        # Entanglement layer
        if entanglement_pattern == "linear":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
        elif entanglement_pattern == "circular":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
            if num_qubits > 2:
                qc.cx(num_qubits - 1, 0)
    
    # Final RY layer
    for qubit in range(num_qubits):
        theta = Parameter(f'ry_final_{qubit}')
        parameters.append(theta)
        qc.ry(theta, qubit)
"""
        return code


# 测试代码
if __name__ == "__main__":
    tool = TFIMVQECircuitBuilder()
    
    # 模拟包含TFIM参数和哈密顿量信息的上下文
    test_context = """
Original Query: Generate complete TFIM Hamiltonian including model parameters and Pauli operator construction for 6 qubits
Current Step: 3

Execution History:
Step 1: TFIMModelGenerator
  Output: Parameters: {'num_qubits': 6, 'coupling_strength': 1.0, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}

Step 2: TFIMHamiltonianBuilder
  Output: Built TFIM Hamiltonian with 11 Pauli terms
  Code: TFIM Hamiltonian Construction with SparsePauliOp

Current State:
  Total Steps: 2
  Code Fragments: 2
  Parameters: {'num_qubits': 6, 'coupling_strength': 1.0, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}
"""
    
    result = tool.execute(test_context)
    print("Tool Result:")
    print(f"Parameters: {result.get('parameters', 'None')}")
    print(f"Ansatz Config: {result.get('ansatz_config', 'None')}")
    print(f"Code:\n{result.get('code', 'None')}")
    print(f"Notes: {result.get('notes', 'None')}")