"""
QuantumForge vNext - 主入口

量子算法代码生成框架的统一入口点。
基于5-Agent架构，将自然语言查询转换为完整的Python量子计算代码。
"""

import time
from typing import Dict, Any, Optional
from core.semantic_engine import parse as parse_query
from core.component_discovery import discover as discover_components
from core.parameter_matcher import normalize as normalize_params
from core.pipeline_composer import compose as compose_pipeline
from core.execution_memory import create as create_memory
from core.code_assembler import assemble as assemble_code
from core.llm_engine import create_engine
from core.schemas import CodeCell


def run(query: str, debug: bool = False) -> str:
    """
    QuantumForge vNext主入口 - 自然语言查询到Python代码的完整转换
    
    Args:
        query: 用户自然语言查询（中文/英文）
        debug: 是否输出调试信息
        
    Returns:
        完整的Python量子计算源码字符串
        
    Raises:
        ValueError: 查询格式无效
        RuntimeError: Agent处理失败
    """
    start_time = time.time()
    
    if debug:
        print(f"🚀 QuantumForge vNext 启动")
        print(f"📝 查询: {query}")
    
    try:
        # Step 1: 语义理解 - Query → TaskCard
        if debug:
            print(f"\n🧠 Step 1: 语义理解...")
        
        task_card = parse_query(query)
        
        if debug:
            print(f"📋 TaskCard: {task_card['domain']}.{task_card['problem']}.{task_card['algorithm']}")
        
        # Step 2: 组件发现 - TaskCard → ComponentCards
        if debug:
            print(f"\n🔍 Step 2: 组件发现...")
        
        components = discover_components(task_card)
        
        if debug:
            print(f"🧱 发现组件: {[comp['name'] for comp in components]}")
        
        # Step 3: 参数归一化 - 处理别名和默认值
        if debug:
            print(f"\n🔧 Step 3: 参数归一化...")
        
        param_map = normalize_params(task_card, components)
        
        if debug:
            if param_map['validation_errors']:
                print(f"⚠️ 参数警告: {param_map['validation_errors']}")
            print(f"✅ 归一化参数: {len(param_map['normalized_params'])}个")
        
        # Step 4: 管道编排 - 生成执行计划
        if debug:
            print(f"\n📊 Step 4: 管道编排...")
        
        pipeline_plan = compose_pipeline(task_card, components, param_map)
        
        if debug:
            print(f"🔗 执行顺序: {pipeline_plan['execution_order']}")
            if pipeline_plan['conflicts']:
                print(f"⚠️ 冲突: {pipeline_plan['conflicts']}")
        
        # Step 5: 代码生成 - 生成CodeCells
        if debug:
            print(f"\n🤖 Step 5: 代码生成...")
        
        memory = create_memory()
        engine = create_engine()
        
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
        
        if debug:
            print(f"📦 生成CodeCells: {memory.size()}个")
        
        # Step 6: 代码装配 - 生成最终源码
        if debug:
            print(f"\n🔨 Step 6: 代码装配...")
        
        final_code = assemble_code(memory, pipeline_plan, task_card, param_map)
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        if debug:
            print(f"\n✅ 代码生成完成!")
            print(f"⏱️ 执行时间: {execution_time:.2f}秒")
            print(f"📏 代码长度: {len(final_code)}字符")
        
        return final_code
    
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"QuantumForge处理失败 (耗时{execution_time:.2f}s): {str(e)}"
        
        if debug:
            print(f"❌ {error_msg}")
        
        raise RuntimeError(error_msg)


def run_and_save(query: str, output_file: str = None, debug: bool = True) -> str:
    """
    运行查询并保存结果到文件
    
    Args:
        query: 用户查询
        output_file: 输出文件名（可选，默认自动生成）
        debug: 是否显示调试信息
        
    Returns:
        生成的代码内容
    """
    # 生成代码
    code = run(query, debug=debug)
    
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
    
    if debug:
        print(f"💾 代码已保存到: {output_file}")
    
    return code


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