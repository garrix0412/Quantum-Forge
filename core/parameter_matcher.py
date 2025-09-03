"""
参数匹配器 - QuantumForge vNext

组件驱动的参数处理引擎。
集成AI智能补全，替代硬编码别名和默认值系统。
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


# 组件驱动的参数发现架构
# AI智能参数补全系统


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
        # 直接使用参数名，不做别名转换（将由组件schema驱动）
        final_params[param_name] = param_value
    
    # 合并Agent的归一化结果
    for param_name, param_value in normalized_params.items():
        if param_name not in final_params:
            final_params[param_name] = param_value
    
    # 默认值现在由AI智能补全，不再使用硬编码
    applied_defaults = {}
    
    # 错误处理：检查组件格式
    if not components:
        enhanced_map = {
            "normalized_params": final_params,
            "aliases": param_map.get("aliases", {}),
            "defaults": {},
            "validation_errors": ["No components provided for parameter processing"]
        }
        return enhanced_map
    
    # 为nullable参数设置None默认值
    for comp in components:
        params_schema = comp.get("params_schema", {})
        for param_name, param_info in params_schema.items():
            # 检查param_info是否为字典类型
            if isinstance(param_info, dict) and param_info.get("nullable") and param_name not in final_params:
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

