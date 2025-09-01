"""
参数匹配器 - QuantumForge vNext

处理参数归一化、别名解析和默认值注入。
基于new.md第4.5节规格和ParamMap架构实现。
"""

from typing import Dict, List, Any
try:
    from .llm_engine import create_engine
    from .schemas import ParamMap
except ImportError:
    # 直接运行时的兼容处理
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from llm_engine import create_engine
    from schemas import ParamMap


# 全局参数别名配置
PARAMETER_ALIASES = {
    # 通用别名
    "num_qubits": "n",
    "qubits": "n", 
    "qubit_count": "n",
    "h_x": "hx",
    "transverse_field": "hx",
    "coupling": "j",
    "j_coupling": "j",
    "repetitions": "reps",
    "layers": "reps",
    "iterations": "maxiter",
    "max_iterations": "maxiter",
    "maximum_iterations": "maxiter",
    
    # VQE特定别名
    "vqe_optimizer": "optimizer",
    "classical_optimizer": "optimizer",
    "opt": "optimizer",
    
    # TFIM特定别名
    "tfim_hx": "hx",
    "tfim_j": "j",
    "ising_coupling": "j",
    
    # 通用参数别名
    "random_seed": "seed",
    "num_shots": "shots",
    "shot_count": "shots"
}


# 全局默认值配置
DEFAULT_VALUES = {
    # VQE算法默认值
    "optimizer": "COBYLA",
    "maxiter": 200,
    "reps": 2,
    "seed": 42,
    "shots": None,
    
    # TFIM哈密顿量默认值
    "boundary": "periodic",
    "hx": 1.0,
    "j": 1.0,
    
    # 通用默认值
    "backend": "qiskit",
    "tolerance": 1e-6
}


def normalize(task_card: Dict[str, Any], components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    归一化参数，处理别名和默认值
    
    Args:
        task_card: 任务卡
        components: 组件列表
        
    Returns:
        ParamMap字典
    """
    # 创建LLM引擎
    engine = create_engine()
    
    # 调用ParamNormAgent
    param_map = engine.normalize_params(task_card, components)
    
    # 应用本地别名和默认值增强
    enhanced_map = _apply_local_enhancements(param_map, task_card, components)
    
    return enhanced_map


def _apply_local_enhancements(param_map: Dict[str, Any], task_card: Dict[str, Any], components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    应用本地别名和默认值增强
    
    Args:
        param_map: Agent返回的ParamMap
        task_card: 原始任务卡
        components: 组件列表
        
    Returns:
        增强后的ParamMap
    """
    # 获取原始参数
    original_params = task_card.get("params", {})
    normalized_params = param_map.get("normalized_params", {})
    
    # 应用全局别名
    final_params = {}
    applied_aliases = {}
    
    for param_name, param_value in original_params.items():
        # 检查是否有别名
        canonical_name = PARAMETER_ALIASES.get(param_name, param_name)
        
        if canonical_name != param_name:
            applied_aliases[param_name] = canonical_name
        
        final_params[canonical_name] = param_value
    
    # 合并Agent的归一化结果
    for param_name, param_value in normalized_params.items():
        if param_name not in final_params:
            final_params[param_name] = param_value
    
    # 应用默认值（只对缺失的参数）
    applied_defaults = {}
    for default_name, default_value in DEFAULT_VALUES.items():
        if default_name not in final_params:
            final_params[default_name] = default_value
            applied_defaults[default_name] = default_value
    
    # 为nullable参数设置None默认值
    for comp in components:
        params_schema = comp.get("params_schema", {})
        for param_name, param_info in params_schema.items():
            if param_info.get("nullable") and param_name not in final_params:
                final_params[param_name] = None
                applied_defaults[param_name] = None
    
    # 收集组件所需的参数
    required_params = set()
    for comp in components:
        params_schema = comp.get("params_schema", {})
        required_params.update(params_schema.keys())
    
    # 验证参数完整性
    missing_params = []
    for required_param in required_params:
        if required_param not in final_params:
            missing_params.append(required_param)
    
    # 构建增强的ParamMap
    enhanced_map = {
        "normalized_params": final_params,
        "aliases": {**param_map.get("aliases", {}), **applied_aliases},
        "defaults": {**param_map.get("defaults", {}), **applied_defaults},
        "validation_errors": param_map.get("validation_errors", []) + 
                           ([f"Missing required parameters: {missing_params}"] if missing_params else [])
    }
    
    return enhanced_map


def normalize_to_dataclass(task_card: Dict[str, Any], components: List[Dict[str, Any]]) -> ParamMap:
    """
    归一化参数并转换为数据类
    
    Args:
        task_card: 任务卡
        components: 组件列表
        
    Returns:
        ParamMap数据类实例
    """
    param_map_dict = normalize(task_card, components)
    
    # 构建validated参数列表（所有成功归一化的参数）
    validated_params = list(param_map_dict["normalized_params"].keys())
    
    return ParamMap(
        aliases=param_map_dict["aliases"],
        defaults=param_map_dict["defaults"],
        validated=validated_params
    )


def resolve_param_alias(param_name: str) -> str:
    """
    解析参数别名为标准名称
    
    Args:
        param_name: 参数名（可能是别名）
        
    Returns:
        标准参数名
    """
    return PARAMETER_ALIASES.get(param_name, param_name)


def get_default_value(param_name: str) -> Any:
    """
    获取参数的默认值
    
    Args:
        param_name: 参数名
        
    Returns:
        默认值，如果没有则返回None
    """
    return DEFAULT_VALUES.get(param_name)


def validate_param_types(params: Dict[str, Any], components: List[Dict[str, Any]]) -> List[str]:
    """
    验证参数类型
    
    Args:
        params: 参数字典
        components: 组件列表
        
    Returns:
        验证错误列表
    """
    errors = []
    
    # 收集所有组件的参数类型要求
    type_requirements = {}
    for comp in components:
        params_schema = comp.get("params_schema", {})
        for param_name, param_spec in params_schema.items():
            if isinstance(param_spec, dict) and "type" in param_spec:
                type_requirements[param_name] = param_spec["type"]
    
    # 验证每个参数的类型
    for param_name, param_value in params.items():
        if param_name in type_requirements:
            expected_type = type_requirements[param_name]
            
            # 基础类型检查
            if expected_type == "int" and not isinstance(param_value, int):
                errors.append(f"参数 {param_name} 应为int类型，实际为{type(param_value).__name__}")
            elif expected_type == "float" and not isinstance(param_value, (int, float)):
                errors.append(f"参数 {param_name} 应为float类型，实际为{type(param_value).__name__}")
            elif expected_type == "str" and not isinstance(param_value, str):
                errors.append(f"参数 {param_name} 应为str类型，实际为{type(param_value).__name__}")
    
    return errors


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing ParameterMatcher...")
    
    # 测试数据
    test_task_card = {
        "domain": "spin",
        "problem": "tfim_ground_energy",
        "algorithm": "vqe", 
        "backend": "qiskit",
        "params": {
            "num_qubits": 8,  # 应该被别名化为 n
            "h_x": 1.2,       # 应该被别名化为 hx
            "coupling": 0.8,  # 应该被别名化为 j
            "repetitions": 3, # 应该被别名化为 reps
            "iterations": 300 # 应该被别名化为 maxiter
        }
    }
    
    test_components = [
        {
            "name": "Hamiltonian.TFIM",
            "kind": "hamiltonian",
            "params_schema": {
                "n": {"type": "int"},
                "hx": {"type": "float"}, 
                "j": {"type": "float"},
                "boundary": {"type": "str"}
            }
        },
        {
            "name": "Algorithm.VQE",
            "kind": "algorithm",
            "params_schema": {
                "optimizer": {"type": "str"},
                "maxiter": {"type": "int"},
                "reps": {"type": "int"}
            }
        }
    ]
    
    print(f"📋 原始参数: {test_task_card['params']}")
    
    try:
        # 测试参数归一化
        param_map = normalize(test_task_card, test_components)
        
        print(f"\n🔧 归一化后参数: {param_map['normalized_params']}")
        print(f"🏷️ 应用的别名: {param_map['aliases']}")
        print(f"📌 应用的默认值: {param_map['defaults']}")
        
        if param_map['validation_errors']:
            print(f"⚠️ 验证错误: {param_map['validation_errors']}")
        else:
            print("✅ 参数验证通过！")
        
        # 测试数据类转换
        param_map_obj = normalize_to_dataclass(test_task_card, test_components)
        print(f"\n📦 ParamMap对象: {len(param_map_obj.validated)}个已验证参数")
        print(f"   别名映射: {len(param_map_obj.aliases)}个")
        print(f"   默认值: {len(param_map_obj.defaults)}个")
        
        # 测试单独的别名解析
        print(f"\n🔍 别名解析测试:")
        test_aliases = ["num_qubits", "h_x", "coupling", "unknown_param"]
        for alias in test_aliases:
            canonical = resolve_param_alias(alias)
            print(f"   {alias} → {canonical}")
        
        print("\n✅ ParameterMatcher测试通过！")
        
    except Exception as e:
        print(f"❌ 参数匹配失败: {str(e)}")
        print("💡 请检查OPENAI_API_KEY环境变量配置。")