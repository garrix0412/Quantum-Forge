"""
组件发现引擎 - QuantumForge vNext

基于TaskCard和组件注册表，发现满足需求的组件集合。
基于new.md第4.4节规格和组件注册表架构实现。
"""

import json
import os
from typing import Dict, List, Any
try:
    from .llm_engine import create_engine
    from .schemas import ComponentCard
except ImportError:
    # 直接运行时的兼容处理
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from llm_engine import create_engine
    from schemas import ComponentCard


def load_registry() -> List[Dict[str, Any]]:
    """
    加载组件注册表（支持模块化和单文件两种格式）
    
    Returns:
        组件注册表数据列表
    """
    current_dir = os.path.dirname(os.path.dirname(__file__))
    
    # 优先尝试模块化结构
    modules_dir = os.path.join(current_dir, "components", "modules")
    if os.path.exists(modules_dir):
        all_components = []
        
        # 递归加载所有模块的JSON文件
        for root, dirs, files in os.walk(modules_dir):
            for file in files:
                if file.endswith('.json'):
                    module_path = os.path.join(root, file)
                    with open(module_path, 'r', encoding='utf-8') as f:
                        module_components = json.load(f)
                        if isinstance(module_components, list):
                            all_components.extend(module_components)
                        else:
                            all_components.append(module_components)
        
        if all_components:
            return all_components
    
    # 回退到单文件registry.json
    registry_path = os.path.join(current_dir, "components", "registry.json")
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"组件注册表不存在: {registry_path}")
    
    with open(registry_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def discover(task_card: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    发现满足TaskCard需求的组件
    
    Args:
        task_card: 任务卡字典
        
    Returns:
        ComponentCard列表
    """
    # 加载组件注册表
    registry_data = load_registry()
    
    # 创建LLM引擎
    engine = create_engine()
    
    # 调用DiscoveryAgent
    component_cards = engine.discover_components(task_card, registry_data)
    
    return component_cards


def discover_to_dataclass(task_card: Dict[str, Any]) -> List[ComponentCard]:
    """
    发现组件并转换为数据类列表
    
    Args:
        task_card: 任务卡字典
        
    Returns:
        ComponentCard数据类列表
    """
    component_dicts = discover(task_card)
    
    # 转换为数据类
    components = []
    for comp_dict in component_dicts:
        component = ComponentCard(
            name=comp_dict["name"],
            kind=comp_dict["kind"],
            tags=comp_dict["tags"],
            needs=comp_dict["needs"],
            provides=comp_dict["provides"],
            params_schema=comp_dict["params_schema"],
            yields=comp_dict["yields"],
            codegen_hint=comp_dict["codegen_hint"]
        )
        components.append(component)
    
    return components


def filter_by_algorithm(components: List[Dict[str, Any]], algorithm: str) -> List[Dict[str, Any]]:
    """
    按算法类型过滤组件
    
    Args:
        components: 组件列表
        algorithm: 算法类型（如"vqe", "qaoa"）
        
    Returns:
        过滤后的组件列表
    """
    filtered = []
    
    for comp in components:
        # 检查tags中是否包含算法标签
        if algorithm.lower() in [tag.lower() for tag in comp.get("tags", [])]:
            filtered.append(comp)
        # 检查name中是否包含算法信息
        elif algorithm.upper() in comp.get("name", "").upper():
            filtered.append(comp)
    
    return filtered


def analyze_dependencies(components: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    分析组件依赖关系
    
    Args:
        components: 组件列表
        
    Returns:
        依赖关系图 {组件名: [依赖的资源列表]}
    """
    dependency_graph = {}
    
    for comp in components:
        comp_name = comp["name"]
        needs = comp.get("needs", [])
        dependency_graph[comp_name] = needs
    
    return dependency_graph


def get_registry_components_by_names(component_names: List[str]) -> List[Dict[str, Any]]:
    """
    根据组件名称从注册表获取组件
    
    Args:
        component_names: 组件名称列表
        
    Returns:
        匹配的组件列表
    """
    registry_data = load_registry()
    
    matched_components = []
    for comp in registry_data:
        if comp["name"] in component_names:
            matched_components.append(comp)
    
    return matched_components


def get_registry_stats() -> Dict[str, Any]:
    """
    获取组件注册表统计信息
    
    Returns:
        统计信息字典
    """
    try:
        registry_data = load_registry()
        
        # 统计各种类型的组件
        kind_counts = {}
        tag_counts = {}
        
        for comp in registry_data:
            kind = comp.get("kind", "unknown")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            
            for tag in comp.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "total_components": len(registry_data),
            "kinds": kind_counts,
            "tags": tag_counts,
            "component_names": [comp["name"] for comp in registry_data]
        }
    
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing ComponentDiscovery...")
    
    # 测试注册表加载
    try:
        registry_data = load_registry()
        print(f"📋 加载了{len(registry_data)}个组件")
        
        # 显示统计信息
        stats = get_registry_stats()
        print(f"📊 注册表统计: {stats}")
        
    except Exception as e:
        print(f"❌ 注册表加载失败: {str(e)}")
        exit(1)
    
    # 测试组件发现
    test_task_card = {
        "domain": "spin",
        "problem": "tfim_ground_energy",
        "algorithm": "vqe",
        "backend": "qiskit",
        "params": {"n": 8, "hx": 1.0, "j": 1.0}
    }
    
    print(f"\n🔍 测试任务: {test_task_card['domain']}.{test_task_card['problem']}.{test_task_card['algorithm']}")
    
    try:
        # 调用组件发现
        discovered_components = discover(test_task_card)
        
        print(f"🎯 发现了{len(discovered_components)}个相关组件:")
        for comp in discovered_components:
            name = comp["name"]
            kind = comp["kind"]
            provides = comp.get("provides", [])
            needs = comp.get("needs", [])
            print(f"   - {name} ({kind})")
            print(f"     提供: {provides}")
            print(f"     依赖: {needs}")
        
        # 测试依赖分析
        deps = analyze_dependencies(discovered_components)
        print(f"\n🔗 依赖关系:")
        for comp_name, needs in deps.items():
            print(f"   {comp_name} → {needs}")
        
        # 测试数据类转换
        component_objects = discover_to_dataclass(test_task_card)
        print(f"\n📦 数据类转换: {len(component_objects)}个ComponentCard对象")
        
        print("\n✅ ComponentDiscovery测试通过！")
        
    except Exception as e:
        print(f"❌ 组件发现失败: {str(e)}")
        print("💡 请检查OPENAI_API_KEY环境变量和注册表格式。")