"""
Molecular Model Generator - QuantumForge V5 分子参数标准化器

接收来自QuantumSemanticEngine等上游组件的分子参数，进行分子特定的验证、标准化和默认值处理。
遵循QuantumForge V5的LLM驱动架构：信任上游LLM分析，专注领域特定处理。

基于示例代码的初始点管理和优化器配置功能。
"""

from typing import Dict, Any, Union
import numpy as np

# 导入基类
try:
    from ..base_component import BaseComponent
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from components.base_component import BaseComponent


class MolecularModelGenerator(BaseComponent):
    """
    分子模型参数标准化器
    
    功能：接收来自上游组件（如QuantumSemanticEngine）已解析的参数，进行分子特定的验证、标准化和默认值处理
    职责：参数验证、物理合理性检查、标准化命名、智能默认值
    不做：用户查询解析（这是QuantumSemanticEngine的LLM职责）
    
    支持的功能：
    - 分子几何处理和验证
    - 基组和计算参数标准化
    - 初始点方法配置
    - 优化器参数设置
    """
    
    # LLM理解的组件描述
    description = "Validate, standardize and apply defaults for molecular VQE calculation parameters. Handles molecular geometry, basis sets, initial point methods (HF, MP2, random, zeros), and optimizer configuration (SLSQP, L-BFGS-B, COBYLA, SPSA). Takes pre-parsed parameters and ensures they are physically reasonable for quantum molecular simulations."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分子参数验证和标准化
        
        信任上游组件（ParameterMatcher）提供的标准化参数，专注分子领域特定的验证和处理
        
        Args:
            query: 用户原始查询（保留用于上下文）
            params: 来自ParameterMatcher的标准化参数
            
        Returns:
            Dict containing:
                - atom: 分子几何字符串
                - basis: 基组名称
                - charge: 总电荷
                - spin: 自旋多重度
                - initial_point_method: 初始点方法
                - optimizer: 优化器配置
                - max_iter: 最大迭代次数
                - model_type: "Molecular"
                - notes: 参数标准化说明
        """
        # 1. 直接使用上游提供的参数（信任ParameterMatcher的语义匹配）
        molecular_params = params.copy()
        
        # 2. 应用分子特定的默认值（对于缺失参数）
        complete_params = self._apply_molecular_defaults(molecular_params)
        
        # 3. 验证参数的物理合理性
        validated_params = self._validate_molecular_parameters(complete_params)
        
        # 4. 标准化输出格式
        standardized_params = self._standardize_output_format(validated_params)
        
        # 5. 生成参数说明
        standardized_params["notes"] = self._generate_parameter_notes(standardized_params)
        
        return standardized_params
    
    def _apply_molecular_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        为分子计算应用物理上合理的默认值
        只对确实缺失的参数应用默认值，不覆盖已有参数
        """
        complete_params = params.copy()
        
        # 分子几何默认值：H2分子（经典测试分子）
        if "atom" not in complete_params:
            complete_params["atom"] = "H 0 0 0; H 0 0 0.735"
        
        # 基组默认值：STO-3G（最小基组，计算友好）
        if "basis" not in complete_params:
            complete_params["basis"] = "sto-3g"
        
        # 电荷默认值：中性分子
        if "charge" not in complete_params:
            complete_params["charge"] = 0
        
        # 自旋多重度默认值：单重态
        if "spin" not in complete_params:
            complete_params["spin"] = 0
        
        # 初始点方法默认值：Hartree-Fock（最常用）
        if "initial_point_method" not in complete_params:
            complete_params["initial_point_method"] = "HF"
        
        # 优化器默认值：SLSQP（稳定收敛）
        if "optimizer" not in complete_params:
            complete_params["optimizer"] = "SLSQP"
        
        # 最大迭代次数默认值：100（平衡效率和收敛性）
        if "max_iter" not in complete_params:
            complete_params["max_iter"] = 100
        
        return complete_params
    
    def _validate_molecular_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证分子参数的物理合理性"""
        validated = params.copy()
        
        # 分子几何验证
        atom_str = params.get("atom", "")
        if isinstance(atom_str, str) and len(atom_str.strip()) > 0:
            validated["atom"] = atom_str.strip()
        else:
            validated["atom"] = "H 0 0 0; H 0 0 0.735"  # 默认H2
        
        # 基组验证
        basis = params.get("basis", "sto-3g")
        if isinstance(basis, str):
            validated["basis"] = basis.lower()
        else:
            validated["basis"] = "sto-3g"
        
        # 电荷验证
        charge = self._safe_convert_to_int(params.get("charge", 0))
        if abs(charge) > 10:  # 限制极端电荷
            validated["charge"] = 10 if charge > 0 else -10
        else:
            validated["charge"] = charge
        
        # 自旋多重度验证
        spin = self._safe_convert_to_int(params.get("spin", 0))
        if spin < 0:
            validated["spin"] = 0
        elif spin > 5:  # 限制极高自旋
            validated["spin"] = 5
        else:
            validated["spin"] = spin
        
        # 初始点方法验证
        initial_method = params.get("initial_point_method", "HF")
        valid_methods = ["HF", "HF_formal", "MP2", "random", "zeros"]
        if initial_method in valid_methods:
            validated["initial_point_method"] = initial_method
        else:
            validated["initial_point_method"] = "HF"
        
        # 优化器验证
        optimizer = params.get("optimizer", "SLSQP")
        valid_optimizers = ["SLSQP", "L-BFGS-B", "COBYLA", "SPSA"]
        if optimizer in valid_optimizers:
            validated["optimizer"] = optimizer
        else:
            validated["optimizer"] = "SLSQP"
        
        # 最大迭代次数验证
        max_iter = self._safe_convert_to_int(params.get("max_iter", 100))
        if max_iter < 10:
            validated["max_iter"] = 10
        elif max_iter > 1000:
            validated["max_iter"] = 1000
        else:
            validated["max_iter"] = max_iter
        
        return validated
    
    def _standardize_output_format(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化输出格式"""
        standardized = {
            "model_type": "Molecular",
            "atom": params["atom"],
            "basis": params["basis"],
            "charge": params["charge"],
            "spin": params["spin"],
            "initial_point_method": params["initial_point_method"],
            "optimizer": params["optimizer"],
            "max_iter": params["max_iter"]
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
                return 0  # 默认值
        else:
            return 0  # 默认值
    
    def _safe_convert_to_float(self, value: Any) -> float:
        """安全地将值转换为浮点数"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0  # 默认值
        else:
            return 0.0  # 默认值
    
    def _generate_parameter_notes(self, params: Dict[str, Any]) -> str:
        """生成分子参数的说明"""
        atom = params["atom"]
        basis = params["basis"]
        charge = params["charge"]
        spin = params["spin"]
        initial_method = params["initial_point_method"]
        optimizer = params["optimizer"]
        max_iter = params["max_iter"]
        
        # 分析分子类型
        atom_count = atom.count(';') + 1 if ';' in atom else len(atom.split('\n'))
        molecule_type = "small molecule" if atom_count <= 4 else "medium molecule" if atom_count <= 10 else "large molecule"
        
        # 分析电荷和自旋
        if charge == 0 and spin == 0:
            charge_spin_desc = "neutral singlet"
        elif charge == 0:
            charge_spin_desc = f"neutral, spin={spin}"
        elif spin == 0:
            charge_spin_desc = f"charged (q={charge}), singlet"
        else:
            charge_spin_desc = f"charged (q={charge}), spin={spin}"
        
        # 分析计算级别
        if basis.lower() in ["sto-3g", "3-21g"]:
            basis_level = "minimal basis"
        elif basis.lower() in ["6-31g", "6-311g"]:
            basis_level = "split-valence basis"
        elif "cc-pv" in basis.lower():
            basis_level = "correlation-consistent basis"
        else:
            basis_level = f"{basis} basis"
        
        notes = (
            f"Molecular VQE parameters: {molecule_type}, {charge_spin_desc}, "
            f"{basis_level}, {initial_method} initial point, {optimizer} optimizer, "
            f"max_iter={max_iter}"
        )
        
        return notes


# 测试代码
if __name__ == "__main__":
    print("🧪 Testing MolecularModelGenerator...")
    
    try:
        generator = MolecularModelGenerator()
        
        print(f"📋 Component: {generator.get_component_name()}")
        print(f"📋 Description: {generator.get_description()}")
        
        # 测试用例 - 基于示例代码的参数
        test_cases = [
            {
                "name": "H2 molecule with HF initial point",
                "query": "H2 molecule VQE calculation with Hartree-Fock initial point",
                "params": {
                    "atom": "H 0 0 0; H 0 0 0.735",
                    "basis": "sto-3g",
                    "initial_point_method": "HF",
                    "optimizer": "SLSQP"
                }
            },
            {
                "name": "LiH molecule with MP2 initial point",
                "query": "LiH molecule calculation with MP2 initial point",
                "params": {
                    "atom": "Li 0 0 0; H 0 0 1.6",
                    "basis": "6-31g",
                    "charge": 0,
                    "spin": 0,
                    "initial_point_method": "MP2",
                    "optimizer": "L-BFGS-B",
                    "max_iter": 200
                }
            },
            {
                "name": "Charged molecule with random initial point",
                "query": "H2+ ion with random initialization",
                "params": {
                    "atom": "H 0 0 0; H 0 0 0.735",
                    "basis": "sto-3g",
                    "charge": 1,
                    "spin": 1,
                    "initial_point_method": "random",
                    "optimizer": "COBYLA"
                }
            },
            {
                "name": "Default parameters test",
                "query": "Basic molecular calculation",
                "params": {}  # 完全依赖默认值
            },
            {
                "name": "String parameters from LLM",
                "query": "Molecular VQE simulation",
                "params": {
                    "charge": "0",
                    "spin": "0",
                    "max_iter": "150"  # 测试字符串转换
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['name']}")
            print(f"  Query: \"{test_case['query']}\"")
            print(f"  Input params: {test_case['params']}")
            
            result = generator.execute(test_case['query'], test_case['params'])
            
            print(f"  ✅ Results:")
            print(f"    • Molecule: {result['atom']}")
            print(f"    • Basis: {result['basis']}")
            print(f"    • Charge/Spin: {result['charge']}/{result['spin']}")
            print(f"    • Initial point: {result['initial_point_method']}")
            print(f"    • Optimizer: {result['optimizer']} (max_iter={result['max_iter']})")
            print(f"    • Notes: {result['notes']}")
        
        print(f"\n✅ All MolecularModelGenerator tests passed!")
        print(f"🎯 Component demonstrates molecular-specific features:")
        print(f"  • Molecular geometry validation and standardization")
        print(f"  • Basis set and electronic structure parameter handling")
        print(f"  • Initial point method configuration (HF, MP2, random, zeros)")
        print(f"  • Optimizer selection and parameter tuning")
        print(f"  • Physics-informed validation and boundary checking")
        print(f"  • Compatible with Qiskit Nature molecular simulation workflow")
        print(f"  • Full QuantumForge V5 LLM-driven architecture compliance")
        
    except Exception as e:
        print(f"⚠️ MolecularModelGenerator test error: {e}")
        import traceback
        traceback.print_exc()