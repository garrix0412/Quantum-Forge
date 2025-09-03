"""
参数Schema收集器 - QuantumForge vNext

组件驱动的参数需求收集和元数据管理。
替代硬编码别名和默认值，实现真正的可扩展架构。
"""

from typing import Dict, List, Any, Set, Optional


def collect_component_parameter_requirements(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    从选中组件动态收集参数需求schema
    
    Args:
        components: 组件列表，每个组件包含params_schema
        
    Returns:
        参数需求字典，包含required_params和metadata
    """
    required_params = {}
    param_metadata = {}
    component_sources = {}
    
    for component in components:
        component_name = component.get("name", "unknown")
        params_schema = component.get("params_schema", {})
        
        for param_name, param_spec in params_schema.items():
            # 收集参数规格
            required_params[param_name] = param_spec
            
            # 构建参数元数据
            param_metadata[param_name] = {
                "source_component": component_name,
                "type": param_spec.get("type") if isinstance(param_spec, dict) else str(param_spec),
                "description": param_spec.get("description", "") if isinstance(param_spec, dict) else "",
                "required": not param_spec.get("nullable", False) if isinstance(param_spec, dict) else True,
                "nullable": param_spec.get("nullable", False) if isinstance(param_spec, dict) else False,
                "enum": param_spec.get("enum", []) if isinstance(param_spec, dict) else []
            }
            
            # 跟踪参数来源组件
            if param_name not in component_sources:
                component_sources[param_name] = []
            component_sources[param_name].append(component_name)
    
    return {
        "required_params": required_params,
        "metadata": param_metadata,
        "component_sources": component_sources,
        "total_components": len(components),
        "total_required_params": len(required_params)
    }


def get_missing_parameters(user_params: Dict[str, Any], required_params: Dict[str, Any]) -> Set[str]:
    """
    识别用户参数中缺失的必需参数
    
    Args:
        user_params: 用户提供的参数
        required_params: 组件要求的参数schema
        
    Returns:
        缺失参数名称集合
    """
    user_param_names = set(user_params.keys())
    required_param_names = set(required_params.keys())
    
    return required_param_names - user_param_names


def categorize_parameters(required_params: Dict[str, Any], param_metadata: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    按类型和特性对参数进行分类
    
    Args:
        required_params: 必需参数schema
        param_metadata: 参数元数据
        
    Returns:
        参数分类字典
    """
    categorized = {
        "required": [],       # 必需参数
        "optional": [],       # 可选参数  
        "algorithmic": [],    # 算法相关参数
        "physical": [],       # 物理量参数
        "computational": []   # 计算控制参数
    }
    
    for param_name, metadata in param_metadata.items():
        # 按必需性分类
        if metadata["required"]:
            categorized["required"].append(param_name)
        else:
            categorized["optional"].append(param_name)
        
        # 按语义分类 (基于参数名模式)
        param_lower = param_name.lower()
        
        if any(keyword in param_lower for keyword in ["optimizer", "maxiter", "reps", "seed"]):
            categorized["computational"].append(param_name)
        elif any(keyword in param_lower for keyword in ["hx", "j", "coupling", "field", "energy"]):
            categorized["physical"].append(param_name)
        elif any(keyword in param_lower for keyword in ["algorithm", "method", "strategy"]):
            categorized["algorithmic"].append(param_name)
    
    return categorized


def validate_parameter_schema(components: List[Dict[str, Any]]) -> List[str]:
    """
    验证组件参数schema的完整性和一致性
    
    Args:
        components: 组件列表
        
    Returns:
        验证错误列表
    """
    errors = []
    
    for component in components:
        component_name = component.get("name", "unknown")
        params_schema = component.get("params_schema", {})
        
        # 检查schema是否为空
        if not params_schema:
            errors.append(f"Component {component_name} has empty params_schema")
            continue
        
        # 检查每个参数的格式
        for param_name, param_spec in params_schema.items():
            if isinstance(param_spec, dict):
                # 检查必需字段
                if "type" not in param_spec:
                    errors.append(f"Parameter {param_name} in {component_name} missing 'type' field")
                
                # 检查类型有效性
                valid_types = {"int", "float", "str", "bool", "list", "dict"}
                param_type = param_spec.get("type")
                if param_type not in valid_types:
                    errors.append(f"Parameter {param_name} in {component_name} has invalid type: {param_type}")
            
            elif isinstance(param_spec, str):
                # 简化格式支持
                valid_simple_types = {"int", "float", "str", "bool"}
                if param_spec not in valid_simple_types:
                    errors.append(f"Parameter {param_name} in {component_name} has invalid simple type: {param_spec}")
            
            else:
                errors.append(f"Parameter {param_name} in {component_name} has invalid schema format")
    
    return errors


def generate_parameter_completion_context(
    query: str, 
    task_card: Dict[str, Any], 
    requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    为AI参数补全生成上下文信息
    
    Args:
        query: 原始用户查询
        task_card: 基础任务卡
        requirements: 参数需求信息
        
    Returns:
        AI补全上下文字典
    """
    missing_params = get_missing_parameters(
        task_card.get("params", {}), 
        requirements["required_params"]
    )
    
    categorized = categorize_parameters(
        requirements["required_params"],
        requirements["metadata"]
    )
    
    return {
        "query": query,
        "domain": task_card.get("domain"),
        "algorithm": task_card.get("algorithm"), 
        "provided_params": task_card.get("params", {}),
        "missing_params": list(missing_params),
        "required_params": requirements["required_params"],
        "param_metadata": requirements["metadata"],
        "categorized_params": categorized,
        "component_sources": requirements["component_sources"]
    }


# =============================================================================
# 便利函数
# =============================================================================

def get_parameter_summary(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """获取参数需求摘要"""
    return {
        "total_params": requirements["total_required_params"],
        "total_components": requirements["total_components"],
        "param_types": {
            param_name: metadata["type"] 
            for param_name, metadata in requirements["metadata"].items()
        },
        "required_params": [
            param_name for param_name, metadata in requirements["metadata"].items()
            if metadata["required"]
        ],
        "optional_params": [
            param_name for param_name, metadata in requirements["metadata"].items()
            if not metadata["required"]
        ]
    }


def check_parameter_conflicts(requirements: Dict[str, Any]) -> List[str]:
    """检查参数冲突（同名参数不同类型）"""
    conflicts = []
    param_types = {}
    
    for param_name, metadata in requirements["metadata"].items():
        param_type = metadata["type"]
        
        if param_name in param_types:
            if param_types[param_name] != param_type:
                conflicts.append(
                    f"Parameter {param_name} has conflicting types: "
                    f"{param_types[param_name]} vs {param_type}"
                )
        else:
            param_types[param_name] = param_type
    
    return conflicts


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing ParameterSchemaCollector...")
    
    # 测试组件数据（模拟registry.json格式）
    test_components = [
        {
            "name": "Hamiltonian.TFIM",
            "kind": "hamiltonian",
            "params_schema": {
                "n": {"type": "int", "description": "Number of qubits"},
                "hx": {"type": "float", "description": "Transverse field strength"},
                "j": {"type": "float", "description": "Coupling strength"},
                "boundary": {"type": "str", "description": "Boundary condition", "enum": ["periodic", "open"]}
            }
        },
        {
            "name": "Algorithm.VQE", 
            "kind": "algorithm",
            "params_schema": {
                "optimizer": {"type": "str", "description": "Optimizer name"},
                "maxiter": {"type": "int", "description": "Maximum iterations"}
            }
        }
    ]
    
    # 测试参数需求收集
    print("\n🔍 测试参数需求收集...")
    requirements = collect_component_parameter_requirements(test_components)
    
    print(f"📊 收集到 {requirements['total_required_params']} 个参数需求")
    print(f"🧱 来自 {requirements['total_components']} 个组件")
    
    # 显示参数元数据
    print(f"\n📋 参数详情:")
    for param_name, metadata in requirements["metadata"].items():
        required_mark = "✅" if metadata["required"] else "⚪"
        print(f"  {required_mark} {param_name}: {metadata['type']} - {metadata['description']}")
        print(f"     来源: {metadata['source_component']}")
    
    # 测试参数分类
    print(f"\n🏷️ 参数分类:")
    categorized = categorize_parameters(requirements["required_params"], requirements["metadata"])
    for category, params in categorized.items():
        if params:
            print(f"  {category}: {params}")
    
    # 测试缺失参数检测
    print(f"\n🔍 测试缺失参数检测:")
    test_user_params = {"n": 4, "hx": 1.0}  # 缺少其他参数
    missing = get_missing_parameters(test_user_params, requirements["required_params"])
    print(f"  用户提供: {list(test_user_params.keys())}")
    print(f"  缺失参数: {list(missing)}")
    
    # 测试冲突检测
    conflicts = check_parameter_conflicts(requirements)
    if conflicts:
        print(f"\n⚠️ 参数冲突: {conflicts}")
    else:
        print(f"\n✅ 无参数冲突")
    
    # 测试AI补全上下文生成
    print(f"\n🤖 生成AI补全上下文...")
    test_task_card = {
        "domain": "spin",
        "algorithm": "vqe",
        "params": test_user_params
    }
    
    context = generate_parameter_completion_context(
        "Compute ground state of 4-qubit system",
        test_task_card,
        requirements
    )
    
    print(f"  查询: {context['query']}")
    print(f"  领域: {context['domain']}")
    print(f"  算法: {context['algorithm']}")
    print(f"  缺失: {context['missing_params']}")
    
    print(f"\n🎉 ParameterSchemaCollector测试完成！")