"""
VQE Circuit Builder - QuantumForge V5 

基于TFIM参数生成VQE ansatz量子线路代码，支持三种ansatz选择。简化版本：只返回code+notes。
"""

from typing import Dict, Any, Optional

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


class VQECircuitBuilder(BaseComponent):
    """VQE线路构建器 - 基于LLM选择的ansatz类型生成代码"""
    
    description = "Build VQE ansatz circuits for TFIM optimization. Supports three ansatz types: hardware_efficient (practical NISQ), tfim_specific (physics-informed), real_amplitudes (amplitude-focused). Uses LLM for intelligent ansatz selection based on query context."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成VQE ansatz线路代码"""
        # 参数获取
        num_qubits = int(params.get("num_qubits", 4))
        J = float(params.get("J", 1.0))
        h = float(params.get("h", 0.5))
        topology = params.get("topology", "linear")
        boundary = params.get("boundary_conditions", "open")
        
        # LLM选择ansatz类型
        ansatz_config = self._llm_select_ansatz(query, params)
        ansatz_type = ansatz_config["type"]
        depth = ansatz_config["depth"]
        entanglement = ansatz_config.get("entanglement", "linear")
        
        # 生成对应的ansatz代码
        code = self._generate_ansatz_code(params, ansatz_config)
        
        # 计算circuit_info
        circuit_info = self._calculate_circuit_info(num_qubits, ansatz_type, depth, entanglement)
        
        # ansatz_info
        ansatz_info = {
            "type": ansatz_type,
            "depth": depth,
            "entanglement": entanglement
        }
        
        # 简要描述
        notes = f"VQE {ansatz_type} ansatz: {num_qubits} qubits, depth {depth}"
        
        return {
            "code": code, 
            "notes": notes,
            "circuit_info": circuit_info,
            "ansatz_info": ansatz_info
        }
    
    def _llm_select_ansatz(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """使用LLM基于用户查询选择合适的ansatz类型"""
        num_qubits = params.get("num_qubits", 4)
        J = params.get("J", 1.0)
        h = params.get("h", 0.5)
        
        prompt = f"""
Based on the user query and TFIM parameters, select the most appropriate VQE ansatz type:

User Query: "{query}"

TFIM Parameters:
- Qubits: {num_qubits}
- Coupling J: {J}
- Field h: {h}
- Topology: {params.get('topology', 'linear')}
- Boundary: {params.get('boundary_conditions', 'open')}

Available Ansatz Options:

1. **hardware_efficient**: 
   - Description: Practical ansatz for NISQ devices using RY rotations and CNOT gates
   - Best for: Hardware optimization, minimal gate count, general-purpose VQE
   - Keywords: "hardware", "efficient", "practical", "NISQ", "minimal gates"

2. **tfim_specific**:
   - Description: Physics-informed ansatz matching TFIM structure (RX rotations + ZZ interactions)
   - Best for: Physics problems, natural model structure, TFIM correspondence
   - Keywords: "physics", "model", "structure", "TFIM", "natural", "informed"

3. **real_amplitudes**:
   - Description: Real-valued states without complex phases, using only RY rotations
   - Best for: Large-scale simulations, amplitude encoding, phase-insensitive problems
   - Keywords: "real", "amplitudes", "large", "simulation", "classical"

Select the ansatz that best matches the user's intent and requirements.

Respond with ONLY a JSON object:
{{
    "type": "<ansatz_type>",
    "reasoning": "<brief explanation>",
    "depth": <recommended_depth_1_to_3>,
    "entanglement": "<linear|circular>",
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
            
            # 验证ansatz类型
            valid_types = ["hardware_efficient", "tfim_specific", "real_amplitudes"]
            if result.get("type") not in valid_types:
                result["type"] = "hardware_efficient"  # 默认
            
            return result
            
        except Exception as e:
            print(f"⚠️ LLM ansatz selection failed: {e}")
            # 回退到默认选择
            return {
                "type": "hardware_efficient",
                "reasoning": "Default fallback selection",
                "depth": 2 if num_qubits <= 6 else 1,
                "entanglement": "linear",
                "confidence": 0.5
            }
    
    def _generate_ansatz_code(self, params: Dict[str, Any], ansatz_config: Dict[str, Any]) -> str:
        """生成ansatz线路代码"""
        num_qubits = params["num_qubits"]
        J = params.get("J", params.get("coupling_J", 1.0))
        h = params.get("h", params.get("field_h", 1.0))
        topology = params.get("topology", "linear")
        boundary = params.get("boundary_conditions", "open")
        
        ansatz_type = ansatz_config["type"]
        depth = ansatz_config["depth"]
        entanglement = ansatz_config.get("entanglement", "linear")
        
        # 基础代码框架
        code = f'''# TFIM VQE Ansatz Circuit - Generated by QuantumForge V5
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
import numpy as np

# TFIM Parameters
num_qubits = {num_qubits}
J = {J}  # Coupling strength
h = {h}  # Transverse field strength
topology = "{topology}"
boundary = "{boundary}"

# VQE Ansatz Configuration
ansatz_type = "{ansatz_type}"
depth = {depth}
entanglement = "{entanglement}"

def create_vqe_ansatz(num_qubits: int, depth: int) -> tuple:
    """
    Create VQE ansatz circuit for TFIM optimization
    
    Returns:
        tuple: (circuit, parameters)
    """
    qc = QuantumCircuit(num_qubits)
    parameters = []
    
'''

        # 根据ansatz类型生成对应代码
        if ansatz_type == "hardware_efficient":
            code += self._generate_hardware_efficient_code(depth, entanglement)
        elif ansatz_type == "tfim_specific":
            code += self._generate_tfim_specific_code(depth, entanglement)
        elif ansatz_type == "real_amplitudes":
            code += self._generate_real_amplitudes_code(depth, entanglement)
        
        # 结束代码
        code += '''
    return qc, parameters

# Create the ansatz
ansatz_circuit, theta_params = create_vqe_ansatz(num_qubits, depth)

print(f"VQE ansatz created: {ansatz_type}")
print(f"Circuit depth: {ansatz_circuit.depth()}")
print(f"Parameters: {len(theta_params)}")
'''
        
        return code
    
    def _calculate_circuit_info(self, num_qubits: int, ansatz_type: str, depth: int, entanglement: str) -> Dict[str, Any]:
        """计算电路关键指标"""
        # 基础参数计算
        if ansatz_type == "hardware_efficient":
            # 每层：num_qubits个RY + entanglement gates + 最后一层RY
            params_per_layer = num_qubits
            total_parameters = depth * params_per_layer + num_qubits  # 最后一层
            
            # 门数计算
            ry_gates = total_parameters  # 每个参数对应一个RY门
            if entanglement == "linear":
                cnot_gates = depth * (num_qubits - 1)
            elif entanglement == "circular":
                cnot_gates = depth * num_qubits
            else:
                cnot_gates = depth * (num_qubits - 1)  # 默认linear
                
        elif ansatz_type == "tfim_specific":
            # 每层：num_qubits个RX + coupling gates + 最后一层RX
            params_per_layer = num_qubits
            if entanglement == "linear":
                params_per_layer += (num_qubits - 1)  # ZZ interaction parameters
            elif entanglement == "circular":
                params_per_layer += num_qubits
                
            total_parameters = depth * params_per_layer + num_qubits
            
            # 门数计算 (RX + 2*CNOT + RZ for each ZZ)
            rx_gates = depth * num_qubits + num_qubits
            if entanglement == "linear":
                zz_blocks = depth * (num_qubits - 1)
                cnot_gates = zz_blocks * 2  # 每个ZZ需要2个CNOT
                rz_gates = zz_blocks
            else:
                zz_blocks = depth * num_qubits  
                cnot_gates = zz_blocks * 2
                rz_gates = zz_blocks
                
            ry_gates = 0
            total_gates = rx_gates + cnot_gates + rz_gates
            
        elif ansatz_type == "real_amplitudes":
            # 类似hardware_efficient但只用RY
            params_per_layer = num_qubits
            total_parameters = depth * params_per_layer + num_qubits
            
            ry_gates = total_parameters
            if entanglement == "linear":
                cnot_gates = depth * (num_qubits - 1)
            elif entanglement == "circular":
                cnot_gates = depth * num_qubits
            else:
                cnot_gates = depth * (num_qubits - 1)
                
        else:
            # 默认估算
            total_parameters = depth * num_qubits + num_qubits
            ry_gates = total_parameters
            cnot_gates = depth * (num_qubits - 1)
        
        # 计算电路深度 (估算)
        if ansatz_type == "tfim_specific":
            circuit_depth = depth * 4 + 1  # RX + CNOT + RZ + CNOT per layer + final RX
        else:
            circuit_depth = depth * 2 + 1  # RY + CNOT layer + final RY
            
        # 总门数
        if ansatz_type == "tfim_specific":
            total_gates = rx_gates + cnot_gates + rz_gates
        else:
            total_gates = ry_gates + cnot_gates
        
        return {
            "parameter_count": total_parameters,
            "circuit_depth": circuit_depth,
            "gate_count": total_gates,
            "cnot_count": cnot_gates
        }
    
    def _generate_hardware_efficient_code(self, depth: int, entanglement: str) -> str:
        """生成Hardware Efficient ansatz代码"""
        return f'''    # Hardware Efficient Ansatz
    for layer in range({depth}):
        # RY rotation layer
        for qubit in range(num_qubits):
            theta = Parameter(f'ry_{{layer}}_{{qubit}}')
            parameters.append(theta)
            qc.ry(theta, qubit)
        
        # CNOT entanglement layer
        if "{entanglement}" == "linear":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
        elif "{entanglement}" == "circular":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
            if num_qubits > 2:
                qc.cx(num_qubits - 1, 0)
    
    # Final RY layer
    for qubit in range(num_qubits):
        theta = Parameter(f'ry_final_{{qubit}}')
        parameters.append(theta)
        qc.ry(theta, qubit)
'''
    
    def _generate_tfim_specific_code(self, depth: int, entanglement: str) -> str:
        """生成TFIM-specific ansatz代码"""
        return f'''    # TFIM-Specific Ansatz (RX + ZZ interactions)
    for layer in range({depth}):
        # RX rotation layer (transverse field direction)
        for qubit in range(num_qubits):
            theta = Parameter(f'rx_{{layer}}_{{qubit}}')
            parameters.append(theta)
            qc.rx(theta, qubit)
        
        # ZZ interaction layer (Ising coupling)
        if "{entanglement}" == "linear":
            for qubit in range(num_qubits - 1):
                phi = Parameter(f'rzz_{{layer}}_{{qubit}}')
                parameters.append(phi)
                # ZZ gate implementation
                qc.cx(qubit, qubit + 1)
                qc.rz(phi, qubit + 1)
                qc.cx(qubit, qubit + 1)
        elif "{entanglement}" == "circular":
            for qubit in range(num_qubits):
                next_qubit = (qubit + 1) % num_qubits
                phi = Parameter(f'rzz_{{layer}}_{{qubit}}')
                parameters.append(phi)
                qc.cx(qubit, next_qubit)
                qc.rz(phi, next_qubit)
                qc.cx(qubit, next_qubit)
    
    # Final RX layer
    for qubit in range(num_qubits):
        theta = Parameter(f'rx_final_{{qubit}}')
        parameters.append(theta)
        qc.rx(theta, qubit)
'''
    
    def _generate_real_amplitudes_code(self, depth: int, entanglement: str) -> str:
        """生成Real Amplitudes ansatz代码"""
        return f'''    # Real Amplitudes Ansatz (RY only, no phases)
    for layer in range({depth}):
        # RY rotation layer
        for qubit in range(num_qubits):
            theta = Parameter(f'ry_{{layer}}_{{qubit}}')
            parameters.append(theta)
            qc.ry(theta, qubit)
        
        # CNOT entanglement layer
        if "{entanglement}" == "linear":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
        elif "{entanglement}" == "circular":
            for qubit in range(num_qubits - 1):
                qc.cx(qubit, qubit + 1)
            if num_qubits > 2:
                qc.cx(num_qubits - 1, 0)
    
    # Final RY layer
    for qubit in range(num_qubits):
        theta = Parameter(f'ry_final_{{qubit}}')
        parameters.append(theta)
        qc.ry(theta, qubit)
'''


# 测试
if __name__ == "__main__":
    print("🧪 Testing VQECircuitBuilder...")
    
    builder = VQECircuitBuilder()
    
    test_cases = [
        {
            "name": "Hardware-focused query",
            "query": "Create efficient VQE circuit for NISQ hardware",
            "params": {"num_qubits": 4, "J": 1.0, "h": 0.5, "topology": "linear"}
        },
        {
            "name": "Physics-focused query", 
            "query": "Build TFIM-specific ansatz that matches the model structure",
            "params": {"num_qubits": 6, "J": 1.5, "h": 1.0, "topology": "linear"}
        },
        {
            "name": "Large simulation query",
            "query": "Generate real amplitudes circuit for large-scale simulation", 
            "params": {"num_qubits": 8, "J": 2.0, "h": 0.8, "topology": "linear"}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"  Query: {test_case['query']}")
        
        result = builder.execute(test_case['query'], test_case['params'])
        print(f"  ✅ Notes: {result['notes']}")
        print(f"  📝 Code length: {len(result['code'])} chars")
        print(f"  🔧 Ansatz: {result['ansatz_info']}")
        print(f"  ⚡ Circuit: {result['circuit_info']}")
    
    print("\n✅ VQECircuitBuilder implemented with LLM ansatz selection!")