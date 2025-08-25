"""
Molecular Model Generator - QuantumForge V5

分子参数标准化器，接收来自parameter_matcher的参数，进行分子特定的验证、标准化和默认值处理。
遵循QuantumForge V5的LLM驱动架构：信任上游parameter_matcher分析，专注领域特定处理。
"""

from typing import Dict, Any, Union

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
    
    功能：接收来自上游组件（如parameter_matcher）已解析的参数，进行分子特定的验证、标准化和默认值处理
    职责：参数验证、物理合理性检查、标准化命名、智能默认值
    不做：用户查询解析（这是parameter_matcher的LLM职责）
    """
    
    # LLM理解的组件描述
    description = "Validate, standardize and apply defaults for molecular VQE calculation parameters. Takes pre-parsed parameters and ensures they are physically reasonable and properly formatted for molecular simulations."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分子参数验证和标准化
        
        信任上游组件（parameter_matcher）提供的标准化参数，专注分子领域特定的验证和处理
        
        Args:
            query: 用户原始查询（保留用于上下文）
            params: 来自parameter_matcher的标准化参数
            
        Returns:
            Dict containing:
                - molecule: 分子名称
                - geometry: 分子几何结构
                - basis: 基组名称
                - charge: 电荷
                - spin: 自旋
                - unit: 长度单位
                - mapper_type: 量子比特映射类型
                - notes: 参数标准化说明
        """
        # 1. 直接使用上游提供的参数（信任parameter_matcher的语义匹配）
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
        为分子模拟应用物理上合理的默认值
        只对确实缺失的参数应用默认值，不覆盖已有参数
        """
        complete_params = params.copy()
        
        # 分子名称默认值：H2（最简单的分子）
        if "molecule" not in complete_params:
            complete_params["molecule"] = "H2"
        
        # 几何结构默认值：简单的H2几何结构（信任parameter_matcher处理复杂分子）
        if "geometry" not in complete_params:
            complete_params["geometry"] = "H 0 0 0; H 0 0 0.735"  # H2标准键长
        
        # 基组默认值：sto3g（最小基组，适合小分子和测试）
        if "basis" not in complete_params:
            complete_params["basis"] = "sto3g"
        
        # 电荷默认值：0（中性分子）
        if "charge" not in complete_params:
            complete_params["charge"] = 0
        
        # 自旋默认值：0（闭壳层分子）
        if "spin" not in complete_params:
            complete_params["spin"] = 0
        
        # 单位默认值：angstrom（量子化学常用单位）
        if "unit" not in complete_params:
            complete_params["unit"] = "angstrom"
        
        # 映射类型默认值：jordan_wigner（最常用的映射）
        if "mapper_type" not in complete_params:
            complete_params["mapper_type"] = "jordan_wigner"
        
        return complete_params
    
    
    def _validate_geometry_format(self, geometry: str) -> bool:
        """验证几何结构格式"""
        try:
            # 基本格式检查
            atoms = geometry.split(';')
            for atom_line in atoms:
                parts = atom_line.strip().split()
                if len(parts) != 4:  # 原子 + 3个坐标
                    return False
                # 检查坐标是否为数字
                for coord in parts[1:4]:
                    float(coord)
            return True
        except:
            return False
    
    
    def _validate_molecular_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数的物理合理性 - 类似TFIM的简洁验证"""
        validated = params.copy()
        
        # 分子名称验证 - 使用安全的类型转换
        molecule = params.get("molecule", "H2")
        if isinstance(molecule, str) and len(molecule.strip()) > 0:
            validated["molecule"] = molecule.strip().upper()
        else:
            validated["molecule"] = "H2"
        
        # 几何结构验证 - 简单格式检查
        geometry = params.get("geometry", "H 0 0 0; H 0 0 0.735")
        if isinstance(geometry, str) and ';' in geometry:
            validated["geometry"] = geometry.strip()
        else:
            validated["geometry"] = "H 0 0 0; H 0 0 0.735"  # 默认H2
        
        # 基组验证
        basis = params.get("basis", "sto3g")
        validated["basis"] = self._validate_basis_set(basis)
        
        # 电荷验证 - 使用安全的类型转换
        charge = self._safe_convert_to_int(params.get("charge", 0))
        if abs(charge) > 3:  # 限制电荷范围（更宽松）
            validated["charge"] = 0
        else:
            validated["charge"] = charge
        
        # 自旋验证 - 使用安全的类型转换
        spin = self._safe_convert_to_int(params.get("spin", 0))
        if abs(spin) > 3:  # 限制自旋范围（更宽松）
            validated["spin"] = 0
        else:
            validated["spin"] = spin
        
        # 单位验证
        unit = params.get("unit", "angstrom")
        if isinstance(unit, str) and unit.lower() in ["angstrom", "bohr"]:
            validated["unit"] = unit.lower()
        else:
            validated["unit"] = "angstrom"
        
        # 映射类型验证
        mapper_type = params.get("mapper_type", "jordan_wigner")
        valid_mappers = ["jordan_wigner", "parity", "bravyi_kitaev"]
        if isinstance(mapper_type, str) and mapper_type.lower() in valid_mappers:
            validated["mapper_type"] = mapper_type.lower()
        else:
            validated["mapper_type"] = "jordan_wigner"
        
        return validated
    
    def _validate_basis_set(self, basis: str) -> str:
        """验证并标准化基组名称 - 简化版本"""
        if not isinstance(basis, str):
            return "sto3g"
        
        basis = basis.strip().lower()
        
        # 有效基组列表
        valid_basis = ["sto3g", "631g", "631gs", "631gss", "ccpvdz"]
        
        # 简单的名称映射
        if "sto" in basis:
            return "sto3g"
        elif "631" in basis or "6-31" in basis:
            return "631g"
        elif basis in valid_basis:
            return basis
        else:
            return "sto3g"  # 默认基组
    
    def _safe_convert_to_int(self, value: Any) -> int:
        """安全地将值转换为整数"""
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, str):
            try:
                return int(float(value))  # 先转float再转int，处理"0.0"这样的字符串
            except ValueError:
                return 0  # 默认值
        else:
            return 0  # 默认值
    
    def _standardize_output_format(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化输出格式"""
        standardized = {
            "molecule": params["molecule"],
            "geometry": params["geometry"],
            "basis": params["basis"],
            "charge": params["charge"],
            "spin": params["spin"],
            "unit": params["unit"],
            "mapper_type": params["mapper_type"]
        }
        
        return standardized
    
    def _generate_parameter_notes(self, params: Dict[str, Any]) -> str:
        """生成参数提取的说明 - 简化版本"""
        molecule = params["molecule"]
        basis = params["basis"]
        charge = params["charge"]
        spin = params["spin"]
        
        # 计算原子数
        geometry = params["geometry"]
        if isinstance(geometry, str):
            atoms = geometry.split(';')
            num_atoms = len(atoms)
        else:
            num_atoms = 2  # 默认值
        
        # 简单的分子类型说明
        if charge == 0 and spin == 0:
            mol_type = "neutral"
        elif charge != 0:
            mol_type = f"charged (q={charge:+d})"
        else:
            mol_type = f"radical (S={spin/2})"
        
        notes = (
            f"Molecular parameters extracted: {molecule} ({num_atoms} atoms), "
            f"{basis} basis, {mol_type}, {params['mapper_type']} mapping"
        )
        
        return notes
