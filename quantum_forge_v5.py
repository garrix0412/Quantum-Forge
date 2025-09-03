"""
QuantumForge vNext - 主入口

量子算法代码生成框架的统一入口点。
基于5-Agent架构，将自然语言查询转换为完整的Python量子计算代码。
"""

import time
from typing import Dict, Any, Optional
from core.semantic_engine import parse as parse_query
from core.component_discovery import discover as discover_components
from core.parameter_schema_collector import collect_component_parameter_requirements
from core.parameter_matcher import normalize as normalize_params
from core.pipeline_composer import compose as compose_pipeline
from core.execution_memory import create as create_memory
from core.code_assembler import assemble as assemble_code
from core.llm_engine import create_engine
from core.schemas import CodeCell
from core.performance_monitor import get_monitor


def run(query: str, debug=False, max_retries: int = 3, experiment_config: Dict[str, Any] = None) -> str:
    """
    QuantumForge vNext主入口 - 自然语言查询到Python代码的完整转换
    
    Args:
        query: 用户自然语言查询（中文/英文）
        debug: 调试配置 - bool(开关) 或 dict{"steps": bool, "agents": bool, "performance": bool}
        max_retries: Agent重试次数（默认3次）
        experiment_config: 实验配置（用于消融实验）
        
    Returns:
        完整的Python量子计算源码字符串
        
    Raises:
        ValueError: 查询格式无效
        RuntimeError: Agent处理失败
    """
    start_time = time.time()
    
    # 处理调试配置
    if isinstance(debug, bool):
        debug_config = {"steps": debug, "agents": False, "performance": debug}
    else:
        debug_config = {
            "steps": debug.get("steps", False),
            "agents": debug.get("agents", False), 
            "performance": debug.get("performance", False)
        }
    
    # 初始化性能监控
    monitor = get_monitor()
    monitor.start_query(query)
    
    # 加载实验配置
    if experiment_config is None:
        from config import ExperimentSettings
        experiment_config = ExperimentSettings.get_experiment_config()
    
    if debug_config["steps"]:
        print(f"🚀 QuantumForge vNext 启动")
        print(f"📝 查询: {query}")
        if experiment_config.get("ai_completion", {}).get("enabled") == False:
            print(f"🧪 实验模式: AI参数补全已禁用")
        if experiment_config.get("robustness", {}).get("simulate_failure"):
            print(f"🧪 实验模式: 模拟{experiment_config['robustness']['failed_agent']}Agent失效")
    
    try:
        # Step 1: 语义理解 - Query → TaskCard
        if debug_config["steps"]:
            print(f"\n🧠 Step 1: 语义理解...")
        
        task_card = parse_query(query)
        
        if debug_config["steps"]:
            print(f"📋 TaskCard: {task_card['domain']}.{task_card['problem']}.{task_card['algorithm']}")
        
        # Step 2: 组件发现 - TaskCard → ComponentCards
        if debug_config["steps"]:
            print(f"\n🔍 Step 2: 组件发现...")
        
        # 检查是否模拟DiscoveryAgent失效
        if (experiment_config.get("robustness", {}).get("simulate_failure") and 
            experiment_config.get("robustness", {}).get("failed_agent") == "discovery"):
            # 模拟组件发现失效，使用基线组件
            from core.component_discovery import get_registry_components_by_names
            baseline_names = experiment_config.get("robustness", {}).get("baseline_components", [])
            components = get_registry_components_by_names(baseline_names)
            if debug_config["agents"]:
                print(f"🧪 模拟DiscoveryAgent失效，使用基线组件: {[comp['name'] for comp in components]}")
        else:
            components = discover_components(task_card)
            if debug_config["steps"]:
                print(f"🧱 发现组件: {[comp['name'] for comp in components]}")
        
        # Step 3: 参数需求收集 - 收集组件参数要求
        if debug_config["steps"]:
            print(f"\n📊 Step 3: 参数需求收集...")
        
        param_requirements = collect_component_parameter_requirements(components)
        
        if debug_config["steps"]:
            print(f"📋 参数需求: {param_requirements['total_required_params']}个参数来自{param_requirements['total_components']}个组件")
        
        # Step 4: AI参数补全 - 智能补全缺失参数 (支持消融实验)
        if debug_config["steps"]:
            print(f"\n🤖 Step 4: AI参数补全...")
        
        # 创建引擎（无论是否启用AI补全都需要，因为后续还要用于代码生成）
        engine = create_engine(max_retries=max_retries)
        
        # 检查是否启用AI参数补全 (消融实验控制)
        if experiment_config.get("ai_completion", {}).get("enabled", True):
            completed_task_card = engine.complete_parameters(query, task_card, param_requirements)
            
            if debug_config["agents"]:
                original_count = len(task_card.get('params', {}))
                completed_count = len(completed_task_card.get('params', {}))
                print(f"✨ 参数补全: {original_count} → {completed_count}个参数")
        else:
            # 消融实验：禁用AI参数补全
            completed_task_card = task_card
            if debug_config["agents"]:
                print(f"🧪 消融模式: 跳过AI参数补全，使用原始参数")
        
        # Step 5: 参数归一化 - 处理别名和默认值
        if debug_config["steps"]:
            print(f"\n🔧 Step 5: 参数归一化...")
        
        # 检查是否模拟ParamNormAgent失效
        if (experiment_config.get("robustness", {}).get("simulate_failure") and 
            experiment_config.get("robustness", {}).get("failed_agent") == "param_norm"):
            # 模拟参数归一化失效，使用简单fallback
            param_map = {
                "normalized_params": completed_task_card.get("params", {}),
                "validation_errors": [],
                "fallback_used": True
            }
            if debug_config["steps"]:
                print(f"🧪 模拟ParamNormAgent失效，使用简单参数映射: {len(param_map['normalized_params'])}个")
        else:
            param_map = normalize_params(completed_task_card, components)
            if debug_config["steps"]:
                if param_map['validation_errors']:
                    print(f"⚠️ 参数警告: {param_map['validation_errors']}")
                print(f"✅ 归一化参数: {len(param_map['normalized_params'])}个")
        
        # Step 6: 管道编排 - 生成执行计划
        if debug_config["steps"]:
            print(f"\n📊 Step 6: 管道编排...")
        
        # 检查是否模拟PipelineAgent失效
        if (experiment_config.get("robustness", {}).get("simulate_failure") and 
            experiment_config.get("robustness", {}).get("failed_agent") == "pipeline"):
            # 模拟管道编排失效，使用简单fallback
            pipeline_plan = {
                "execution_order": [comp["name"] for comp in components],
                "conflicts": [],
                "dependencies": {},
                "fallback_used": True
            }
            if debug_config["steps"]:
                print(f"🧪 模拟PipelineAgent失效，使用简单执行顺序: {pipeline_plan['execution_order']}")
        else:
            pipeline_plan = compose_pipeline(completed_task_card, components, param_map)
            if debug_config["steps"]:
                print(f"🔗 执行顺序: {pipeline_plan['execution_order']}")
                if pipeline_plan['conflicts']:
                    print(f"⚠️ 冲突: {pipeline_plan['conflicts']}")
        
        # Step 7: 代码生成 - 生成CodeCells
        if debug_config["steps"]:
            print(f"\n🤖 Step 7: 代码生成...")
        
        memory = create_memory()
        
        # 调用CodegenAgent生成CodeCells
        code_cells_data = engine.generate_codecells(pipeline_plan, components, param_map)
        
        # 转换为CodeCell对象并添加到Memory
        for cell_data in code_cells_data:
            cell = CodeCell(
                id=cell_data["id"],
                imports=cell_data["imports"],
                helpers=cell_data["helpers"],
                definitions=cell_data["definitions"],
                invoke=cell_data["invoke"],
                exports=cell_data["exports"]
            )
            memory.add(cell)
        
        if debug_config["steps"]:
            print(f"📦 生成CodeCells: {memory.size()}个")
        
        # Step 8: 代码装配 - 生成最终源码
        if debug_config["steps"]:
            print(f"\n🔨 Step 8: 代码装配...")
        
        final_code = assemble_code(memory, pipeline_plan, task_card, param_map)
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 结束性能监控
        monitor.end_query()
        
        if debug_config["steps"]:
            print(f"\n✅ 代码生成完成!")
            print(f"⏱️ 执行时间: {execution_time:.2f}秒")
            print(f"📏 代码长度: {len(final_code)}字符")
            
        if debug_config["performance"]:
            # 显示Agent性能统计
            metrics = monitor.export_metrics()
            print(f"\n📊 Agent性能统计:")
            for agent_name, agent_metrics in metrics["agents"].items():
                print(f"  {agent_name}: {agent_metrics['input_tokens']}+{agent_metrics['output_tokens']}={agent_metrics['total_tokens']}tokens, {agent_metrics['call_time']}s")
            totals = metrics["totals"]
            print(f"  总计: {totals['total_tokens']}tokens, {totals['total_agent_time']}s")
        
        return final_code
    
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"QuantumForge处理失败 (耗时{execution_time:.2f}s): {str(e)}"
        
        if debug_config["steps"]:
            print(f"❌ {error_msg}")
        
        raise RuntimeError(error_msg)


def run_and_save(query: str, output_file: str = None, debug=True, max_retries: int = 3) -> str:
    """
    运行查询并保存结果到文件
    
    Args:
        query: 用户查询
        output_file: 输出文件名（可选，默认自动生成）
        debug: 调试配置 - bool(开关) 或 dict{"steps": bool, "agents": bool, "performance": bool}
        max_retries: Agent重试次数（默认3次）
        
    Returns:
        生成的代码内容
    """
    # 处理调试配置
    if isinstance(debug, bool):
        debug_config = {"steps": debug, "agents": False, "performance": debug}
    else:
        debug_config = debug
    
    # 生成代码
    code = run(query, debug=debug, max_retries=max_retries)
    
    # 确定输出文件名
    if not output_file:
        import re
        from datetime import datetime
        
        # 从查询中提取关键词作为文件名
        clean_query = re.sub(r'[^\w\s]', '', query)
        words = clean_query.split()[:3]  # 取前3个词
        filename_base = "_".join(words).lower()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"generated_{filename_base}_{timestamp}.py"
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    if debug_config["steps"]:
        print(f"💾 代码已保存到: {output_file}")
    
    return code


def run_with_metrics(query: str, debug=False, max_retries: int = 3, save_metrics: str = None) -> tuple[str, Dict[str, Any]]:
    """
    运行查询并返回代码和性能指标
    
    Args:
        query: 用户查询
        debug: 调试配置 - bool(开关) 或 dict{"steps": bool, "agents": bool, "performance": bool}
        max_retries: Agent重试次数
        save_metrics: 保存指标的文件路径（可选）
        
    Returns:
        (生成的代码, 性能指标字典)
    """
    # 处理调试配置
    if isinstance(debug, bool):
        debug_config = {"steps": debug, "agents": False, "performance": debug}
    else:
        debug_config = debug
    
    # 运行主函数
    code = run(query, debug=debug, max_retries=max_retries)
    
    # 获取性能指标
    monitor = get_monitor()
    metrics = monitor.export_metrics()
    
    # 保存指标到文件（可选）
    if save_metrics:
        import json
        with open(save_metrics, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        if debug_config["steps"]:
            print(f"📊 性能指标已保存到: {save_metrics}")
    
    return code, metrics


def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息和组件统计
    
    Returns:
        系统信息字典
    """
    from core.component_discovery import get_registry_stats
    from core.llm_engine import create_engine
    
    try:
        registry_stats = get_registry_stats()
        engine_stats = create_engine().get_agent_stats()
        
        return {
            "version": "vNext",
            "architecture": "5-Agent Pipeline",
            "components": registry_stats,
            "agents": engine_stats,
            "pipeline_stages": [
                "SemanticEngine → TaskCard",
                "ComponentDiscovery → ComponentCards", 
                "ParameterMatcher → ParamMap",
                "PipelineComposer → PipelinePlan",
                "CodeAssembler → Python Code"
            ]
        }
    
    except Exception as e:
        return {"error": str(e)}


def run_ablation_experiment(query: str, experiment_type: str = "ai_completion", debug: bool = True) -> Dict[str, Any]:
    """
    运行消融实验，比较不同配置下的系统表现
    
    Args:
        query: 测试查询
        experiment_type: 实验类型 "ai_completion" | "agent_robustness"
        debug: 是否显示调试信息
        
    Returns:
        实验结果字典
    """
    from config import ExperimentSettings
    
    results = {"experiment_type": experiment_type, "query": query, "results": {}}
    
    if experiment_type == "ai_completion":
        print(f"🧪 AI参数补全消融实验")
        print(f"📝 查询: {query}\n")
        
        # 对照组: 禁用AI参数补全
        control_config = {"ai_completion": {"enabled": False}}
        print("📊 对照组 (无AI补全):")
        try:
            start_time = time.time()
            control_code = run(query, debug=debug, experiment_config=control_config)
            control_time = time.time() - start_time
            
            results["results"]["control"] = {
                "success": True,
                "execution_time": control_time,
                "code_length": len(control_code),
                "param_count": control_code.count("=") # 简单参数计数
            }
            print(f"✅ 对照组完成: {control_time:.2f}s, {len(control_code)}字符\n")
            
        except Exception as e:
            results["results"]["control"] = {"success": False, "error": str(e)}
            print(f"❌ 对照组失败: {e}\n")
        
        # 实验组: 启用AI参数补全  
        experiment_config = {"ai_completion": {"enabled": True}}
        print("📊 实验组 (有AI补全):")
        try:
            start_time = time.time()
            experiment_code = run(query, debug=debug, experiment_config=experiment_config)
            experiment_time = time.time() - start_time
            
            results["results"]["experiment"] = {
                "success": True,
                "execution_time": experiment_time,
                "code_length": len(experiment_code),
                "param_count": experiment_code.count("=")
            }
            print(f"✅ 实验组完成: {experiment_time:.2f}s, {len(experiment_code)}字符")
            
        except Exception as e:
            results["results"]["experiment"] = {"success": False, "error": str(e)}
            print(f"❌ 实验组失败: {e}")
    
    elif experiment_type == "agent_robustness":
        print(f"🧪 Agent鲁棒性实验")
        print(f"📝 查询: {query}\n")
        
        # 对照组: 正常运行所有Agent
        control_config = {"robustness": {"simulate_failure": False, "failed_agent": None}}
        print("📊 对照组 (所有Agent正常):")
        try:
            start_time = time.time()
            control_code = run(query, debug=debug, experiment_config=control_config)
            control_time = time.time() - start_time
            
            results["results"]["control"] = {
                "success": True,
                "execution_time": control_time,
                "code_length": len(control_code),
                "failed_agent": None
            }
            print(f"✅ 对照组完成: {control_time:.2f}s, {len(control_code)}字符\n")
            
        except Exception as e:
            results["results"]["control"] = {"success": False, "error": str(e), "failed_agent": None}
            print(f"❌ 对照组失败: {e}\n")
        
        # 实验组: 模拟不同Agent失效
        failed_agents = ["discovery", "param_norm", "pipeline"]
        
        for failed_agent in failed_agents:
            experiment_config = {
                "robustness": {
                    "simulate_failure": True,
                    "failed_agent": failed_agent,
                    "baseline_components": ExperimentSettings.BASELINE_COMPONENTS
                }
            }
            
            print(f"📊 实验组 ({failed_agent}Agent失效):")
            try:
                start_time = time.time()
                experiment_code = run(query, debug=debug, experiment_config=experiment_config)
                experiment_time = time.time() - start_time
                
                results["results"][f"failed_{failed_agent}"] = {
                    "success": True,
                    "execution_time": experiment_time,
                    "code_length": len(experiment_code),
                    "failed_agent": failed_agent
                }
                print(f"✅ 实验组完成: {experiment_time:.2f}s, {len(experiment_code)}字符")
                
            except Exception as e:
                results["results"][f"failed_{failed_agent}"] = {
                    "success": False, 
                    "error": str(e),
                    "failed_agent": failed_agent
                }
                print(f"❌ 实验组失败: {e}")
            
            print()  # 空行分隔
    
    return results


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🚀 QuantumForge vNext 端到端测试")
    
    # 测试查询
    test_queries = [
        "帮我计算8比特TFIM的基态能量",
        "使用VQE算法计算10比特TFIM基态，横向场强度1.5"
    ]
    
    for query in test_queries:
        print(f"\n" + "="*60)
        print(f"🔍 测试查询: {query}")
        print("="*60)
        
        try:
            # 运行完整管道
            generated_code = run(query, debug=True)
            
            # 显示生成的代码片段
            lines = generated_code.split('\n')
            print(f"\n📄 生成的代码预览 (前20行):")
            print("-" * 50)
            for i, line in enumerate(lines[:20]):
                print(f"{i+1:2d}: {line}")
            if len(lines) > 20:
                print(f"... (还有{len(lines)-20}行)")
            print("-" * 50)
            
            print(f"🎉 查询处理成功！")
            
        except Exception as e:
            print(f"❌ 查询处理失败: {str(e)}")
    
    # 显示系统信息
    print(f"\n📊 系统信息:")
    system_info = get_system_info()
    for key, value in system_info.items():
        if isinstance(value, dict):
            print(f"  {key}: {len(value) if 'components' in key else value}")
        elif isinstance(value, list):
            print(f"  {key}: {len(value)}项")
        else:
            print(f"  {key}: {value}")