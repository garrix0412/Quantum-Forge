"""
管道编排器 - QuantumForge vNext

基于组件依赖关系生成线性执行计划。
基于new.md第4.6节规格和PipelinePlan架构实现。
"""

from typing import Dict, List, Any, Set
try:
    from .llm_engine import create_engine
    from .schemas import PipelinePlan, PipelineStep
except ImportError:
    # 直接运行时的兼容处理
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from llm_engine import create_engine
    from schemas import PipelinePlan, PipelineStep


def compose(task_card: Dict[str, Any], components: List[Dict[str, Any]], param_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    编排组件执行管道
    
    Args:
        task_card: 任务卡
        components: 组件列表
        param_map: 参数映射
        
    Returns:
        PipelinePlan字典
    """
    # 创建LLM引擎
    engine = create_engine()
    
    # 调用PipelineAgent
    pipeline_plan = engine.plan_pipeline(task_card, components, param_map)
    
    # 应用本地拓扑排序验证和优化
    enhanced_plan = _apply_local_topological_sort(pipeline_plan, components)
    
    return enhanced_plan


def _apply_local_topological_sort(pipeline_plan: Dict[str, Any], components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    应用本地拓扑排序验证
    
    Args:
        pipeline_plan: Agent返回的管道计划
        components: 组件列表
        
    Returns:
        优化后的管道计划
    """
    # 构建组件依赖图
    component_map = {comp["name"]: comp for comp in components}
    dependency_graph = {}
    provides_map = {}
    
    for comp in components:
        name = comp["name"]
        needs = comp.get("needs", [])
        provides = comp.get("provides", [])
        
        dependency_graph[name] = needs
        for resource in provides:
            if resource not in provides_map:
                provides_map[resource] = []
            provides_map[resource].append(name)
    
    # 执行拓扑排序
    sorted_order = topological_sort(dependency_graph, provides_map)
    
    # 检测冲突
    conflicts = detect_conflicts(components, provides_map)
    
    # 构建增强的管道计划
    enhanced_plan = {
        "execution_order": sorted_order,
        "dependency_graph": dependency_graph,
        "conflicts": conflicts,
        "provides_map": provides_map,
        "original_order": pipeline_plan.get("execution_order", [])
    }
    
    return enhanced_plan


def topological_sort(dependency_graph: Dict[str, List[str]], provides_map: Dict[str, List[str]]) -> List[str]:
    """
    拓扑排序算法
    
    Args:
        dependency_graph: 依赖关系图 {组件名: [需要的资源]}
        provides_map: 提供关系图 {资源名: [提供该资源的组件]}
        
    Returns:
        拓扑排序后的组件执行顺序
    """
    # 构建组件间直接依赖关系
    component_deps = {}
    for comp_name, needed_resources in dependency_graph.items():
        component_deps[comp_name] = set()
        
        for resource in needed_resources:
            if resource in provides_map:
                # 这个组件依赖于提供该资源的所有组件
                component_deps[comp_name].update(provides_map[resource])
    
    # Kahn算法进行拓扑排序
    in_degree = {comp: 0 for comp in dependency_graph.keys()}
    
    # 计算入度
    for comp_name, deps in component_deps.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[comp_name] += 1
    
    # 初始化队列（入度为0的节点）
    queue = [comp for comp, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        # 取出一个入度为0的节点
        current = queue.pop(0)
        result.append(current)
        
        # 更新相邻节点的入度
        for comp_name, deps in component_deps.items():
            if current in deps:
                in_degree[comp_name] -= 1
                if in_degree[comp_name] == 0:
                    queue.append(comp_name)
    
    # 检查是否有环
    if len(result) != len(dependency_graph):
        remaining = set(dependency_graph.keys()) - set(result)
        raise ValueError(f"检测到循环依赖: {remaining}")
    
    return result


def detect_conflicts(components: List[Dict[str, Any]], provides_map: Dict[str, List[str]]) -> List[str]:
    """
    检测资源提供冲突
    
    Args:
        components: 组件列表
        provides_map: 资源提供映射
        
    Returns:
        冲突描述列表
    """
    conflicts = []
    
    # 检查是否有多个组件提供同一资源
    for resource, providers in provides_map.items():
        if len(providers) > 1:
            conflicts.append(f"资源 '{resource}' 由多个组件提供: {providers}")
    
    return conflicts


def compose_to_dataclass(task_card: Dict[str, Any], components: List[Dict[str, Any]], param_map: Dict[str, Any]) -> PipelinePlan:
    """
    编排管道并转换为数据类
    
    Args:
        task_card: 任务卡
        components: 组件列表
        param_map: 参数映射
        
    Returns:
        PipelinePlan数据类实例
    """
    pipeline_dict = compose(task_card, components, param_map)
    
    # 构建PipelineStep列表
    steps = []
    execution_order = pipeline_dict["execution_order"]
    normalized_params = param_map.get("normalized_params", {})
    
    for comp_name in execution_order:
        # 为每个组件创建参数绑定（使用$param占位符）
        comp_params = {}
        
        # 找到对应的组件
        component = None
        for comp in components:
            if comp["name"] == comp_name:
                component = comp
                break
        
        if component:
            params_schema = component.get("params_schema", {})
            for param_name in params_schema.keys():
                if param_name in normalized_params:
                    comp_params[param_name] = f"${param_name}"
        
        step = PipelineStep(use=comp_name, with_params=comp_params)
        steps.append(step)
    
    return PipelinePlan(steps=steps)


def validate_pipeline(pipeline_plan: Dict[str, Any], components: List[Dict[str, Any]]) -> List[str]:
    """
    验证管道计划的有效性
    
    Args:
        pipeline_plan: 管道计划
        components: 组件列表
        
    Returns:
        验证错误列表
    """
    errors = []
    
    execution_order = pipeline_plan.get("execution_order", [])
    component_names = {comp["name"] for comp in components}
    
    # 检查执行顺序中的组件是否都存在
    for comp_name in execution_order:
        if comp_name not in component_names:
            errors.append(f"执行计划中的组件 '{comp_name}' 在组件列表中不存在")
    
    # 检查是否所有组件都在执行计划中
    for comp in components:
        if comp["name"] not in execution_order:
            errors.append(f"组件 '{comp['name']}' 不在执行计划中")
    
    return errors


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing PipelineComposer...")
    
    # 测试数据
    test_task_card = {
        "domain": "spin",
        "problem": "tfim_ground_energy",
        "algorithm": "vqe",
        "backend": "qiskit",
        "params": {"n": 8, "hx": 1.0, "j": 1.0}
    }
    
    test_components = [
        {
            "name": "Hamiltonian.TFIM",
            "kind": "hamiltonian",
            "needs": [],
            "provides": ["hamiltonian"]
        },
        {
            "name": "Circuit.TFIM_HEA", 
            "kind": "ansatz",
            "needs": [],
            "provides": ["ansatz"]
        },
        {
            "name": "Algorithm.VQE",
            "kind": "algorithm", 
            "needs": ["hamiltonian", "ansatz", "optimizer", "estimator"],
            "provides": ["energy", "result"]
        },
        {
            "name": "Optimizer.COBYLA",
            "kind": "optimizer",
            "needs": [],
            "provides": ["optimizer"]
        },
        {
            "name": "Backend.Estimator",
            "kind": "backend",
            "needs": [],
            "provides": ["estimator"]
        }
    ]
    
    test_param_map = {
        "normalized_params": {"n": 8, "hx": 1.0, "j": 1.0},
        "aliases": {"num_qubits": "n"},
        "defaults": {"optimizer": "COBYLA"},
        "validation_errors": []
    }
    
    print(f"📋 任务: {test_task_card['domain']}.{test_task_card['problem']}")
    print(f"🔧 组件数量: {len(test_components)}")
    
    try:
        # 测试管道编排
        pipeline_plan = compose(test_task_card, test_components, test_param_map)
        
        print(f"\n📊 执行顺序: {pipeline_plan['execution_order']}")
        print(f"🔗 依赖关系: {pipeline_plan['dependency_graph']}")
        
        if pipeline_plan['conflicts']:
            print(f"⚠️ 检测到冲突: {pipeline_plan['conflicts']}")
        else:
            print("✅ 无冲突检测")
        
        # 验证管道计划
        validation_errors = validate_pipeline(pipeline_plan, test_components)
        if validation_errors:
            print(f"❌ 管道验证失败: {validation_errors}")
        else:
            print("✅ 管道验证通过")
        
        # 测试数据类转换
        pipeline_obj = compose_to_dataclass(test_task_card, test_components, test_param_map)
        print(f"\n📦 PipelinePlan对象: {len(pipeline_obj.steps)}个步骤")
        
        # 显示步骤详情
        for i, step in enumerate(pipeline_obj.steps):
            print(f"   步骤{i+1}: {step.use} -> {step.with_params}")
        
        print("\n✅ PipelineComposer测试通过！")
        
    except Exception as e:
        print(f"❌ 管道编排失败: {str(e)}")
        print("💡 请检查OPENAI_API_KEY环境变量配置。")