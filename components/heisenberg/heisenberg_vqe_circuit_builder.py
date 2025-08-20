"""
Heisenberg VQE Circuit Builder - QuantumForge V5

基于各向同性Heisenberg参数生成VQE ansatz量子线路代码。
针对各向同性Heisenberg模型的物理特性进行优化。
H = J∑(XiXj + YiYj + ZiZj) + h∑Zi
"""

from typing import Dict, Any, Optional
import json

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


class HeisenbergVQECircuitBuilder(BaseComponent):
    """
    各向同性Heisenberg VQE线路构建器 - 基于LLM选择的ansatz类型生成代码
    
    支持的各向同性Heisenberg专用ansatz类型：
    1. heisenberg_specific: 物理启发的ansatz，使用RXX+RYY+RZZ门直接模拟Heisenberg相互作用
    2. real_amplitudes: 实值态ansatz，适合大规模系统
    """
    
    description = "Build VQE ansatz circuits for isotropic Heisenberg spin chain optimization. Supports two ansatz types: heisenberg_specific (physics-informed with RXX/RYY/RZZ gates) and real_amplitudes (large-scale optimized). Uses LLM for intelligent ansatz selection based on isotropic Heisenberg model parameters."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成各向同性Heisenberg VQE ansatz线路代码"""
        # 简化参数获取
        num_qubits = int(params.get("num_qubits", 4))
        J = float(params.get("J", 1.0))  # 各向同性耦合强度
        h = float(params.get("h", 0.0))  # 纵向磁场强度
        topology = params.get("topology", "linear")
        boundary = params.get("boundary_conditions", "open")
        
        # LLM选择ansatz类型
        ansatz_config = self._llm_select_isotropic_ansatz(query, params)
        ansatz_type = ansatz_config["type"]
        depth = ansatz_config["depth"]
        entanglement = ansatz_config.get("entanglement", "linear")
        
        # 生成对应的ansatz代码
        code = self._generate_isotropic_ansatz_code(params, ansatz_config)
        
        # 计算circuit_info
        circuit_info = self._calculate_circuit_info(num_qubits, ansatz_type, depth, entanglement)
        
        # ansatz_info
        ansatz_info = {
            "type": ansatz_type,
            "depth": depth,
            "entanglement": entanglement,
            "adapted_for_heisenberg": True
        }
        
        # 简要描述
        notes = f"Isotropic Heisenberg VQE {ansatz_type} ansatz: {num_qubits} qubits, depth {depth}, J={J}"
        
        return {
            "code": code,
            "notes": notes,
            "circuit_info": circuit_info,
            "ansatz_info": ansatz_info
        }
    
    def _llm_select_isotropic_ansatz(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """使用LLM基于用户查询选择合适的各向同性Heisenberg ansatz类型"""
        num_qubits = params.get("num_qubits", 4)
        J = params.get("J", 1.0)
        h = params.get("h", 0.0)
        
        # 分析相互作用类型
        interaction_type = "ferromagnetic" if J > 0 else "antiferromagnetic" if J < 0 else "zero coupling"
        
        prompt = f"""
Based on the user query and isotropic Heisenberg model parameters, select the most appropriate VQE ansatz type:

User Query: "{query}"

Isotropic Heisenberg Model Parameters:
- Qubits: {num_qubits}
- Exchange coupling: J={J}
- Magnetic field: h={h}
- Interaction type: {interaction_type}
- Topology: {params.get('topology', 'linear')}
- Boundary: {params.get('boundary_conditions', 'open')}

Available Ansatz Options:

1. **heisenberg_specific**: 
   - Description: Physics-informed ansatz using RXX, RYY, RZZ gates that directly correspond to Heisenberg interactions
   - Best for: Small-medium systems (≤8 qubits), high accuracy, physics-motivated problems
   - Keywords: "physics", "accurate", "Heisenberg", "exchange", "specific", "motivated"

2. **real_amplitudes**:
   - Description: Real-valued states using only RY rotations, suitable for large-scale simulations
   - Best for: Large systems (>8 qubits), classical simulation, amplitude-focused problems
   - Keywords: "large", "scale", "simulation", "real", "amplitudes", "classical"

Selection Guidelines:
- For small systems (≤8 qubits) with physics focus: heisenberg_specific
- For large systems or fast simulation: real_amplitudes

Respond with ONLY a JSON object:
{{
    "type": "<ansatz_type>",
    "reasoning": "<brief explanation>",
    "depth": <recommended_depth_1_to_4>,
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
            
            # 验证ansatz类型（简化为两种）
            valid_types = ["heisenberg_specific", "real_amplitudes"]
            if result.get("type") not in valid_types:
                # 根据系统大小选择默认ansatz
                if num_qubits <= 8:
                    result["type"] = "heisenberg_specific"
                else:
                    result["type"] = "real_amplitudes"
            
            return result
            
        except Exception as e:
            print(f"⚠️ LLM isotropic ansatz selection failed: {e}")
            # 简化回退策略
            fallback_type = "heisenberg_specific" if num_qubits <= 8 else "real_amplitudes"
                
            return {
                "type": fallback_type,
                "reasoning": f"Fallback selection based on system size and {interaction_type} interaction",
                "depth": min(3, max(1, num_qubits // 2)),
                "entanglement": "linear",
                "confidence": 0.7
            }
    
    def _generate_isotropic_ansatz_code(self, params: Dict[str, Any], ansatz_config: Dict[str, Any]) -> str:
        """生成各向同性Heisenberg ansatz线路代码"""
        num_qubits = params["num_qubits"]
        J = params.get("J", 1.0)
        h = params.get("h", 0.0)
        topology = params.get("topology", "linear")
        boundary = params.get("boundary_conditions", "open")
        
        ansatz_type = ansatz_config["type"]
        depth = ansatz_config["depth"]
        entanglement = ansatz_config.get("entanglement", "linear")
        
        # 基础代码框架
        code = f'''# Isotropic Heisenberg VQE Ansatz Circuit - Generated by QuantumForge V5
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector
import numpy as np

# Isotropic Heisenberg Model Parameters
num_qubits = {num_qubits}
J = {J}  # Isotropic exchange coupling (Jx = Jy = Jz = J)
h = {h}  # Longitudinal magnetic field
topology = "{topology}"
boundary = "{boundary}"

# VQE Ansatz Configuration
ansatz_type = "{ansatz_type}"
depth = {depth}
entanglement = "{entanglement}"

def create_heisenberg_vqe_ansatz(num_qubits: int, depth: int) -> tuple:
    """
    Create isotropic Heisenberg VQE ansatz circuit optimized for spin chain models
    
    Ansatz type: {ansatz_type}
    H = J∑(XiXj + YiYj + ZiZj) + h∑Zi
    
    Returns:
        tuple: (circuit, parameters)
    """
    qc = QuantumCircuit(num_qubits)
    parameters = []
    
'''

        # 根据ansatz类型生成对应代码（简化为两种）
        if ansatz_type == "heisenberg_specific":
            code += self._generate_isotropic_heisenberg_code(depth, entanglement)
        elif ansatz_type == "real_amplitudes":
            code += self._generate_real_amplitudes_code(depth, entanglement)
        
        # 结束代码
        code += '''
    return qc, parameters

# Create the ansatz
ansatz_circuit, theta_params = create_heisenberg_vqe_ansatz(num_qubits, depth)

print(f"Isotropic Heisenberg VQE ansatz created: {ansatz_type}")
print(f"Isotropic coupling: J={J}")
print(f"Circuit depth: {ansatz_circuit.depth()}")
print(f"Parameters: {len(theta_params)}")
print(f"Topology: {topology}, Boundary: {boundary}")
'''
        
        return code
    
    def _generate_isotropic_heisenberg_code(self, depth: int, entanglement: str) -> str:
        """生成各向同性Heisenberg特定ansatz代码"""
        return f'''    # Isotropic Heisenberg-Specific Ansatz (Physics-Informed)
    # Directly corresponds to H = J*(XX + YY + ZZ) + h*Z
    
    for layer in range({depth}):
        # Exchange interaction layer - RXX, RYY, RZZ gates (all with same J)
        coupling_pairs = num_qubits - 1 if "{entanglement}" == "linear" else num_qubits
        
        for i in range(coupling_pairs):
            j = (i + 1) % num_qubits
            
            # XX interaction: corresponds to J*XᵢXⱼ term
            theta_xx = Parameter(f'xx_{{layer}}_{{i}}')
            parameters.append(theta_xx)
            qc.rxx(theta_xx, i, j)
            
            # YY interaction: corresponds to J*YᵢYⱼ term  
            theta_yy = Parameter(f'yy_{{layer}}_{{i}}')
            parameters.append(theta_yy)
            qc.ryy(theta_yy, i, j)
            
            # ZZ interaction: corresponds to J*ZᵢZⱼ term (isotropic)
            theta_zz = Parameter(f'zz_{{layer}}_{{i}}')
            parameters.append(theta_zz)
            qc.rzz(theta_zz, i, j)
        
        # Longitudinal magnetic field layer - Z rotations only
        if abs(h) > 1e-10:
            for i in range(num_qubits):
                # Z field: corresponds to h*Zᵢ term (longitudinal field only)
                theta_z = Parameter(f'rz_{{layer}}_{{i}}')
                parameters.append(theta_z)
                qc.rz(theta_z, i)
'''
    
    
    def _generate_real_amplitudes_code(self, depth: int, entanglement: str) -> str:
        """生成实振幅ansatz代码"""
        return f'''    # Real Amplitudes Ansatz (Large-Scale Optimized)
    # Real-valued states using only RY rotations
    
    for layer in range({depth}):
        # RY rotation layer (maintains real amplitudes)
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
    
    def _calculate_circuit_info(self, num_qubits: int, ansatz_type: str, depth: int, entanglement: str) -> Dict[str, Any]:
        """计算各向同性Heisenberg电路关键指标"""
        if ansatz_type == "heisenberg_specific":
            # 各向同性：每层3个交换门/对 + 1个局域Z场门/量子比特（如果有磁场）
            coupling_pairs = (num_qubits - 1) if entanglement == "linear" else num_qubits
            exchange_params_per_layer = 3 * coupling_pairs  # RXX + RYY + RZZ (同参数J)
            field_params_per_layer = num_qubits  # 只有RZ (纵向磁场)
            total_parameters = depth * (exchange_params_per_layer + field_params_per_layer)
            
            # 估算门数
            exchange_gates = 3 * depth * coupling_pairs  # RXX + RYY + RZZ
            field_gates = depth * num_qubits  # RZ gates
            total_gates = exchange_gates + field_gates
            circuit_depth = depth * 4  # 每层4个门深度（RXX+RYY+RZZ+RZ）
            
        elif ansatz_type == "real_amplitudes":
            # RY + CNOT ansatz
            params_per_layer = num_qubits
            total_parameters = depth * params_per_layer + num_qubits  # 最后一层
            
            ry_gates = total_parameters
            if entanglement == "linear":
                cnot_gates = depth * (num_qubits - 1)
            else:
                cnot_gates = depth * num_qubits
            total_gates = ry_gates + cnot_gates
            circuit_depth = depth * 2 + 1
            
        else:
            # 默认估算
            total_parameters = depth * num_qubits * 2
            total_gates = total_parameters + depth * num_qubits
            circuit_depth = depth * 3
        
        return {
            "parameter_count": total_parameters,
            "circuit_depth": circuit_depth,
            "gate_count": total_gates,
            "ansatz_type": ansatz_type,
            "heisenberg_optimized": True
        }


# 测试代码
if __name__ == "__main__":
    print("🧪 Testing Simplified HeisenbergVQECircuitBuilder...")
    
    try:
        builder = HeisenbergVQECircuitBuilder()
        
        print(f"📋 Component: {builder.get_component_name()}")
        print(f"📋 Description: {builder.get_description()}")
        
        # 简化的测试用例 - 只测试各向同性模型
        test_cases = [
            {
                "name": "Physics-informed Heisenberg ansatz",
                "query": "Build VQE ansatz for isotropic Heisenberg chain with physics-informed approach",
                "params": {
                    "num_qubits": 4,
                    "J": 1.0,
                    "h": 0.0,
                    "topology": "linear",
                    "boundary_conditions": "open"
                }
            },
            {
                "name": "Antiferromagnetic with magnetic field",
                "query": "VQE for antiferromagnetic Heisenberg model with longitudinal field",
                "params": {
                    "num_qubits": 6,
                    "J": -1.0,
                    "h": 0.5,
                    "topology": "linear",
                    "boundary_conditions": "open"
                }
            },
            {
                "name": "Large-scale real amplitudes ansatz",
                "query": "Create real amplitudes ansatz for large-scale Heisenberg simulation",
                "params": {
                    "num_qubits": 10,
                    "J": 1.0,
                    "h": 0.3,
                    "topology": "linear",
                    "boundary_conditions": "open"
                }
            },
            {
                "name": "Benchmark-style isotropic model",
                "query": "VQE ansatz for isotropic Heisenberg model with magnetic field",
                "params": {
                    "num_qubits": 4,
                    "J": 1.5,
                    "h": 0.8,
                    "topology": "linear",
                    "boundary_conditions": "open"
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['name']}")
            print(f"  Query: {test_case['query']}")
            print(f"  Parameters: {test_case['params']}")
            
            result = builder.execute(test_case['query'], test_case['params'])
            print(f"  ✅ Notes: {result['notes']}")
            print(f"  📝 Code length: {len(result['code'])} chars")
            print(f"  🔧 Ansatz: {result['ansatz_info']}")
            print(f"  ⚡ Circuit: {result['circuit_info']}")
            
            # 验证生成的代码包含关键组件
            code = result['code']
            assert "create_heisenberg_vqe_ansatz" in code
            assert "QuantumCircuit" in code
            assert "Parameter" in code
        
        print(f"\n✅ All simplified HeisenbergVQECircuitBuilder tests passed!")
        print(f"🎯 Simplified component features:")
        print(f"  • LLM-driven ansatz selection for isotropic Heisenberg models")
        print(f"  • Physics-informed heisenberg_specific ansatz with RXX/RYY/RZZ gates")
        print(f"  • Real-amplitudes ansatz for large-scale simulations")
        print(f"  • Focus on isotropic model (J parameter) with longitudinal field (h)")
        print(f"  • Intelligent fallback strategies for robust operation")
        print(f"  • Compatible with simplified benchmark code design")
        print(f"  • Full QuantumForge V5 LLM-driven architecture compliance")
        
    except Exception as e:
        print(f"⚠️ HeisenbergVQECircuitBuilder test error: {e}")
        import traceback
        traceback.print_exc()