"""
TFIM Hamiltonian Builder

构建TFIM (Transverse Field Ising Model) 哈密顿量的Qiskit代码。
"""

import sys
import os

# 添加父目录到路径以导入BaseTool
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, List, Tuple
from base_tool import BaseTool
import json


class TFIMHamiltonianBuilder(BaseTool):
    """
    TFIM哈密顿量构建器
    
    功能:
    - 从Memory中读取TFIM模型参数
    - 调用LLM分析参数并确定哈密顿量构建策略
    - 生成TFIM哈密顿量的Qiskit SparsePauliOp代码
    """
    
    def __init__(self):
        super().__init__()
        
    def execute(self, context: str) -> Dict[str, Any]:
        """
        执行TFIM哈密顿量构建
        
        Args:
            context: 从Memory获取的上下文信息
            
        Returns:
            包含哈密顿量构建代码的结果
        """
        try:
            # 从上下文中提取TFIM参数
            parameters = self._extract_parameters_from_context(context)
            
            if not parameters:
                # 如果没有找到参数，调用LLM分析
                parameters = self._llm_extract_parameters(context)
            
            # 构建Pauli项
            pauli_terms = self._build_pauli_terms(parameters)
            
            # 生成哈密顿量代码
            code = self._generate_hamiltonian_code(parameters, pauli_terms)
            
            return {
                "code": code,
                "parameters": parameters,
                "pauli_terms": pauli_terms,
                "notes": f"Built TFIM Hamiltonian with {len(pauli_terms)} Pauli terms"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "code": "",
                "notes": f"Failed to build TFIM Hamiltonian: {str(e)}"
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
            required_keys = ['num_qubits', 'coupling_strength', 'field_strength']
            if all(key in parameters for key in required_keys):
                # 设置默认值
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
Based on the execution history below, extract the TFIM model parameters for Hamiltonian construction:

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
    
    def _build_pauli_terms(self, parameters: Dict[str, Any]) -> List[Tuple[str, float]]:
        """
        构建TFIM的Pauli项
        
        Args:
            parameters: TFIM参数
            
        Returns:
            Pauli项列表 [(pauli_string, coefficient), ...]
        """
        num_qubits = parameters['num_qubits']
        J = parameters['coupling_strength']
        h = parameters['field_strength']
        topology = parameters.get('topology', 'linear')
        boundary = parameters.get('boundary_conditions', 'open')
        
        pauli_terms = []
        
        # 构建横向磁场项 (X terms)
        for i in range(num_qubits):
            pauli_string = 'I' * num_qubits
            pauli_string = pauli_string[:i] + 'X' + pauli_string[i+1:]
            pauli_terms.append((pauli_string, -h))  # -h * X_i
        
        # 构建耦合项 (ZZ terms)
        if topology == 'linear':
            # 线性链：相邻量子比特耦合
            for i in range(num_qubits - 1):
                pauli_string = 'I' * num_qubits
                pauli_string = pauli_string[:i] + 'Z' + pauli_string[i+1:]
                pauli_string = pauli_string[:i+1] + 'Z' + pauli_string[i+2:]
                pauli_terms.append((pauli_string, -J))  # -J * Z_i * Z_{i+1}
            
            # 如果是周期边界条件，添加首尾耦合
            if boundary == 'periodic' and num_qubits > 2:
                pauli_string = 'I' * num_qubits
                pauli_string = 'Z' + pauli_string[1:]  # 第0位
                pauli_string = pauli_string[:-1] + 'Z'  # 最后一位
                pauli_terms.append((pauli_string, -J))
                
        elif topology == 'circular':
            # 圆形拓扑：所有相邻量子比特耦合，包括首尾
            for i in range(num_qubits):
                j = (i + 1) % num_qubits
                pauli_string = 'I' * num_qubits
                pauli_string = pauli_string[:i] + 'Z' + pauli_string[i+1:]
                pauli_string = pauli_string[:j] + 'Z' + pauli_string[j+1:]
                pauli_terms.append((pauli_string, -J))
        
        return pauli_terms
    
    def _generate_hamiltonian_code(self, parameters: Dict[str, Any], pauli_terms: List[Tuple[str, float]]) -> str:
        """
        生成哈密顿量构建代码
        
        Args:
            parameters: TFIM参数
            pauli_terms: Pauli项列表
            
        Returns:
            生成的Python代码
        """
        code = f"""# TFIM Hamiltonian Construction
# Generated by QuantumForge V4

from qiskit.quantum_info import SparsePauliOp
import numpy as np

# TFIM Parameters (from previous step)
num_qubits = {parameters['num_qubits']}
coupling_strength = {parameters['coupling_strength']}  # J parameter
field_strength = {parameters['field_strength']}        # h parameter
topology = "{parameters['topology']}"
boundary_conditions = "{parameters['boundary_conditions']}"

# Build TFIM Hamiltonian: H = -J * ∑ZZ - h * ∑X
pauli_list = [
"""
        
        # 添加Pauli项
        for i, (pauli_string, coeff) in enumerate(pauli_terms):
            code += f"    ('{pauli_string}', {coeff})"
            if i < len(pauli_terms) - 1:
                code += ","
            code += f"  # {'Transverse field' if 'X' in pauli_string else 'Ising coupling'}\n"
        
        code += """]

# Create the Hamiltonian operator
hamiltonian = SparsePauliOp.from_list(pauli_list)

print(f"TFIM Hamiltonian constructed:")
print(f"  - {num_qubits} qubits")
print(f"  - {len([term for term in pauli_list if 'X' in term[0]])} transverse field terms")
print(f"  - {len([term for term in pauli_list if 'Z' in term[0] and term[0].count('Z') > 1])} coupling terms")
print(f"  - Topology: {topology}")
print(f"  - Boundary: {boundary_conditions}")

# Hamiltonian is ready for VQE
# Next step: Create ansatz circuit
"""
        
        return code


# 测试代码
if __name__ == "__main__":
    tool = TFIMHamiltonianBuilder()
    
    # 模拟包含TFIM参数的上下文
    test_context = """
Original Query: Create a 6-qubit TFIM with strong coupling strength of 2.0
Current Step: 2

Execution History:
Step 1: TFIMModelGenerator
  Output: Parameters: {'num_qubits': 6, 'coupling_strength': 2.0, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}

Current State:
  Total Steps: 1
  Code Fragments: 1
  Parameters: {'num_qubits': 6, 'coupling_strength': 2.0, 'field_strength': 1.0, 'topology': 'linear', 'boundary_conditions': 'open'}
"""
    
    result = tool.execute(test_context)
    print("Tool Result:")
    print(f"Parameters: {result.get('parameters', 'None')}")
    print(f"Pauli Terms: {len(result.get('pauli_terms', []))} terms")
    print(f"Code:\\n{result.get('code', 'None')}")
    print(f"Notes: {result.get('notes', 'None')}")