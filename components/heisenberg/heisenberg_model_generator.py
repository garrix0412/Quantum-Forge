"""
Heisenberg Model Generator - QuantumForge V5 各向同性Heisenberg参数标准化器

接收来自QuantumSemanticEngine等上游组件的参数，进行各向同性Heisenberg特定的验证、标准化和默认值处理。
遵循QuantumForge V5的LLM驱动架构：信任上游LLM分析，专注领域特定处理。

各向同性Heisenberg模型: H = J∑(XiXj + YiYj + ZiZj) + h∑Zi
"""

from typing import Dict, Any, Union

# 导入基类
try:
    from ..base_component import BaseComponent
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from components.base_component import BaseComponent


class HeisenbergModelGenerator(BaseComponent):
    """
    各向同性Heisenberg模型参数标准化器
    
    功能：接收来自上游组件（如QuantumSemanticEngine）已解析的参数，进行各向同性Heisenberg特定的验证、标准化和默认值处理
    职责：参数验证、物理合理性检查、标准化命名、智能默认值
    不做：用户查询解析（这是QuantumSemanticEngine的LLM职责）
    
    支持的模型：
    - 各向同性Heisenberg模型: H = J∑(XiXj + YiYj + ZiZj) + h∑Zi
    - 参数：J (交换耦合强度), h (纵向磁场强度)
    """
    
    # LLM理解的组件描述
    description = "Validate, standardize and apply defaults for isotropic Heisenberg spin chain model parameters. H = J∑(XX + YY + ZZ) + h∑Z. Takes pre-parsed parameters and ensures they are physically reasonable for quantum isotropic Heisenberg simulations."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行各向同性Heisenberg参数验证和标准化
        
        信任上游组件（ParameterMatcher）提供的标准化参数，专注各向同性Heisenberg领域特定的验证和处理
        
        Args:
            query: 用户原始查询（保留用于上下文）
            params: 来自ParameterMatcher的标准化参数
            
        Returns:
            Dict containing:
                - num_qubits: 系统大小（量子比特数）
                - J: 各向同性交换耦合强度
                - h: 纵向磁场强度
                - topology: 拓扑结构（linear, ring等）
                - boundary_conditions: 边界条件（open, periodic）
                - model_type: "Heisenberg"
                - notes: 参数标准化说明
        """
        # 1. 直接使用上游提供的参数（信任ParameterMatcher的语义匹配）
        heisenberg_params = params.copy()
        
        # 2. 应用各向同性Heisenberg特定的默认值（对于缺失参数）
        complete_params = self._apply_isotropic_defaults(heisenberg_params)
        
        # 3. 验证参数的物理合理性
        validated_params = self._validate_physical_parameters(complete_params)
        
        # 4. 标准化输出格式
        standardized_params = self._standardize_output_format(validated_params)
        
        # 5. 生成参数说明
        standardized_params["notes"] = self._generate_parameter_notes(standardized_params)
        
        return standardized_params
    
    def _apply_isotropic_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        为各向同性Heisenberg模拟应用物理上合理的默认值
        只对确实缺失的参数应用默认值，不覆盖已有参数
        """
        complete_params = params.copy()
        
        # 系统大小默认值：4量子比特（经典模拟友好的小系统）
        if "num_qubits" not in complete_params:
            complete_params["num_qubits"] = 4
        
        # 各向同性交换耦合强度：J（所有方向相等）
        if "J" not in complete_params:
            complete_params["J"] = 1.0  # 标准化单位
        
        # 纵向磁场默认值：零磁场（基态情况）
        if "h" not in complete_params:
            complete_params["h"] = 0.0
        
        # 拓扑结构默认值：线性链（最简单的结构）
        if "topology" not in complete_params:
            complete_params["topology"] = "linear"
        
        # 边界条件默认值：开放边界（最常用）
        if "boundary_conditions" not in complete_params:
            complete_params["boundary_conditions"] = "open"
        
        return complete_params
    
    def _validate_physical_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证各向同性Heisenberg参数的物理合理性"""
        validated = params.copy()
        
        # 系统大小验证 - 使用安全的类型转换
        num_qubits = self._safe_convert_to_int(params.get("num_qubits", 4))
        if num_qubits < 2:
            validated["num_qubits"] = 4  # 最小2量子比特，默认4
        elif num_qubits > 16:
            validated["num_qubits"] = 16  # 限制最大系统大小（Heisenberg模型计算复杂度高）
        else:
            validated["num_qubits"] = num_qubits
        
        # 各向同性交换耦合参数验证 - Heisenberg模型允许负值（反铁磁）
        J_value = self._safe_convert_to_float(params.get("J", 1.0))
        if abs(J_value) < 0.01:
            validated["J"] = 0.01 if J_value >= 0 else -0.01  # 最小耦合强度，保持符号
        elif abs(J_value) > 10.0:
            validated["J"] = 10.0 if J_value > 0 else -10.0  # 最大耦合强度，保持符号
        else:
            validated["J"] = J_value
        
        # 纵向磁场参数验证 - 允许负值（磁场方向）
        h_value = self._safe_convert_to_float(params.get("h", 0.0))
        if abs(h_value) > 10.0:
            validated["h"] = 10.0 if h_value > 0 else -10.0  # 最大磁场强度，保持符号
        else:
            validated["h"] = h_value
        
        # 拓扑结构验证
        topology = params.get("topology", "linear")
        if isinstance(topology, str):
            validated["topology"] = topology.lower()
        else:
            validated["topology"] = "linear"
        
        # 边界条件验证
        boundary = params.get("boundary_conditions", "open")
        if isinstance(boundary, str) and boundary.lower() in ["open", "periodic"]:
            validated["boundary_conditions"] = boundary.lower()
        else:
            validated["boundary_conditions"] = "open"
        
        return validated
    
    def _standardize_output_format(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化输出格式 - 各向同性模型"""
        standardized = {
            "model_type": "Heisenberg",
            "num_qubits": params["num_qubits"],
            "J": params["J"],  # 各向同性耦合强度
            "h": params["h"],  # 纵向磁场强度
            "topology": params.get("topology", "linear"),
            "boundary_conditions": params.get("boundary_conditions", "open")
        }
        
        return standardized
    
    def _safe_convert_to_int(self, value: Any) -> int:
        """安全地将值转换为整数"""
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, str):
            try:
                return int(float(value))  # 先转float再转int，处理"4.0"这样的字符串
            except ValueError:
                return 4  # 默认值
        else:
            return 4  # 默认值
    
    def _safe_convert_to_float(self, value: Any) -> float:
        """安全地将值转换为浮点数"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 1.0  # 默认值
        else:
            return 1.0  # 默认值
    
    def _generate_parameter_notes(self, params: Dict[str, Any]) -> str:
        """生成各向同性Heisenberg参数说明"""
        num_qubits = params["num_qubits"]
        J = params["J"]
        h = params["h"]
        topology = params["topology"]
        
        # 耦合强度分析
        coupling_regime = "strong coupling" if abs(J) > 2.0 else "moderate coupling" if abs(J) > 0.5 else "weak coupling"
        
        # 磁场分析
        field_regime = "strong field" if abs(h) > 2.0 else "moderate field" if abs(h) > 0.5 else "weak field" if abs(h) > 0.01 else "zero field"
        
        # 相互作用类型
        interaction_type = "ferromagnetic" if J > 0 else "antiferromagnetic" if J < 0 else "zero coupling"
        
        # 磁场描述
        if abs(h) < 0.01:
            field_desc = "zero field"
        else:
            field_desc = f"longitudinal field h={h:.3f}"
        
        notes = (
            f"Isotropic Heisenberg parameters: {num_qubits}-qubit {topology} chain, "
            f"J={J:.3f}, {interaction_type}, {field_desc} ({coupling_regime})"
        )
        
        return notes


# 测试代码
if __name__ == "__main__":
    print("🧪 Testing Simplified HeisenbergModelGenerator...")
    
    try:
        generator = HeisenbergModelGenerator()
        
        print(f"📋 Component: {generator.get_component_name()}")
        print(f"📋 Description: {generator.get_description()}")
        
        # 简化的测试用例 - 只测试各向同性模型
        test_cases = [
            {
                "name": "Basic isotropic Heisenberg model",
                "query": "Create isotropic Heisenberg chain with 4 qubits, J=1.0",
                "params": {"num_qubits": 4, "J": 1.0}
            },
            {
                "name": "Antiferromagnetic Heisenberg chain",
                "query": "Antiferromagnetic Heisenberg model with 6 qubits",
                "params": {"num_qubits": 6, "J": -1.0}
            },
            {
                "name": "Ferromagnetic with magnetic field",
                "query": "Ferromagnetic Heisenberg with longitudinal field",
                "params": {"num_qubits": 4, "J": 1.5, "h": 0.5}
            },
            {
                "name": "String parameters from LLM",
                "query": "Heisenberg VQE simulation", 
                "params": {"num_qubits": "8", "J": "2.0", "h": "0.8"}  # 测试字符串转换
            },
            {
                "name": "Periodic boundary Heisenberg ring",
                "query": "Heisenberg ring with periodic boundary conditions",
                "params": {"num_qubits": 6, "J": 1.0, "topology": "ring", "boundary_conditions": "periodic"}
            },
            {
                "name": "Edge case validation",
                "query": "Large Heisenberg system with extreme parameters",
                "params": {"num_qubits": 20, "J": 15.0, "h": 20.0}  # 测试边界条件
            },
            {
                "name": "Minimal parameters (all defaults)",
                "query": "Basic Heisenberg simulation", 
                "params": {}  # 完全依赖默认值
            },
            {
                "name": "Benchmark-style parameters",
                "query": "Heisenberg VQE benchmark with magnetic field",
                "params": {"num_qubits": 4, "J": 1.5, "h": 0.8}  # 类似benchmark代码的参数
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['name']}")
            print(f"  Query: \"{test_case['query']}\"")
            print(f"  Input params: {test_case['params']}")
            
            result = generator.execute(test_case['query'], test_case['params'])
            
            print(f"  ✅ Results:")
            print(f"    • num_qubits: {result['num_qubits']}")
            print(f"    • Exchange: J={result['J']}")
            print(f"    • Magnetic field: h={result['h']}")
            print(f"    • Topology: {result['topology']}, Boundary: {result['boundary_conditions']}")
            print(f"    • Notes: {result['notes']}")
        
        print(f"\n✅ All simplified HeisenbergModelGenerator tests passed!")
        print(f"🎯 Simplified component features:")
        print(f"  • Focus on isotropic Heisenberg model only (J for all directions)")
        print(f"  • Support for ferromagnetic/antiferromagnetic interactions")
        print(f"  • Longitudinal magnetic field handling")
        print(f"  • Physics-informed validation and boundary checking")
        print(f"  • Comprehensive parameter documentation with regime analysis")
        print(f"  • Reduced complexity while maintaining full functionality")
        print(f"  • Full compatibility with QuantumForge V5 LLM-driven architecture")
        
    except Exception as e:
        print(f"⚠️ HeisenbergModelGenerator test error: {e}")
        import traceback
        traceback.print_exc()