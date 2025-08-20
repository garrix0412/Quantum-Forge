"""
QuantumForge V5 - 主控制器

LLM驱动的量子代码生成系统核心控制器。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 3.2 设计。
整合所有智能组件，提供端到端的量子代码生成服务。
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入所有核心组件
try:
    from .semantic_engine import QuantumSemanticEngine
    from .component_discovery import IntelligentComponentDiscovery
    from .pipeline_composer import IntelligentPipelineComposer
    from .parameter_matcher import LLMParameterMatcher
    from .code_assembler import IntelligentCodeAssembler
    from .execution_memory import ExecutionMemory
    from ..components.base_component import BaseComponent
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.semantic_engine import QuantumSemanticEngine
    from core.component_discovery import IntelligentComponentDiscovery
    from core.pipeline_composer import IntelligentPipelineComposer
    from core.parameter_matcher import LLMParameterMatcher
    from core.code_assembler import IntelligentCodeAssembler
    from core.execution_memory import ExecutionMemory
    from components.base_component import BaseComponent


class QuantumForgeV5:
    """
    QuantumForge V5 主控制器
    
    核心功能:
    - 端到端量子代码生成流程
    - 智能组件协调和管理
    - LLM驱动的量子问题理解和解决
    - 零配置的量子算法扩展支持
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        初始化QuantumForge V5系统
        
        Args:
            model: 使用的LLM模型名称
        """
        self.model = model
        self.session_id = self._generate_session_id()
        
        # 初始化所有核心组件
        self.semantic_engine = QuantumSemanticEngine(model=model)
        self.component_discovery = IntelligentComponentDiscovery(model=model)
        self.pipeline_composer = IntelligentPipelineComposer(model=model)
        self.parameter_matcher = LLMParameterMatcher(model=model)
        self.code_assembler = IntelligentCodeAssembler(model=model)
        
        print(f"🚀 QuantumForge V5 initialized (Model: {model}, Session: {self.session_id})")
    
    def generate_quantum_code(self, user_query: str) -> str:
        """
        端到端量子代码生成的主要接口
        
        Args:
            user_query: 用户的量子计算问题描述
            
        Returns:
            生成的完整量子代码文件路径
        """
        print(f"\n🎯 Processing query: \"{user_query}\"")
        print("=" * 60)
        
        try:
            # 阶段1: 语义理解
            print("📡 Phase 1: Quantum Problem Understanding...")
            intent = self.semantic_engine.understand_quantum_query(user_query)
            print(f"  ✅ Problem Type: {intent.problem_type}")
            print(f"  ✅ Algorithm: {intent.algorithm}")
            print(f"  ✅ Parameters: {intent.parameters}")
            
            # 阶段2: 智能组件发现
            print("\n🔍 Phase 2: Intelligent Component Discovery...")
            component_names = self.component_discovery.discover_relevant_components(intent)
            print(f"  ✅ Selected Components: {component_names}")
            
            # 获取组件描述用于流水线设计
            component_descriptions = {}
            for name in component_names:
                try:
                    component_class = self.component_discovery.get_component_class(name)
                    if component_class:
                        instance = component_class()
                        component_descriptions[name] = instance.get_description()
                    else:
                        component_descriptions[name] = f"Component: {name}"
                except Exception as e:
                    component_descriptions[name] = f"Component: {name} (description unavailable)"
            
            # 阶段3: 智能流水线组合
            print("\n🔧 Phase 3: Intelligent Pipeline Composition...")
            pipeline_order = self.pipeline_composer.compose_execution_pipeline(
                intent, component_names, component_descriptions
            )
            print(f"  ✅ Pipeline Order: {pipeline_order}")
            
            # 阶段4: 执行流水线
            print("\n⚡ Phase 4: Pipeline Execution...")
            memory = ExecutionMemory()
            memory.initialize(user_query, intent.to_dict())
            
            for i, component_name in enumerate(pipeline_order):
                print(f"  🔄 Executing {i+1}/{len(pipeline_order)}: {component_name}")
                
                try:
                    # 获取组件实例
                    component_class = self.component_discovery.get_component_class(component_name)
                    component_instance = component_class()
                    
                    # 智能参数匹配
                    matched_params = self.parameter_matcher.resolve_parameters(
                        memory, component_instance, component_name
                    )
                    print(f"    📋 Matched Parameters: {list(matched_params.keys())}")
                    
                    # 执行组件
                    result = component_instance.execute(user_query, matched_params)
                    memory.store_component_output(component_name, result)
                    print(f"    ✅ {component_name} completed")
                    
                except Exception as e:
                    print(f"    ⚠️ {component_name} execution failed: {e}")
                    # 继续执行，但记录错误
                    error_result = {
                        "error": str(e),
                        "component": component_name,
                        "status": "failed",
                        "notes": f"Component execution failed: {e}"
                    }
                    memory.store_component_output(component_name, error_result)
            
            # 阶段5: 智能代码组装
            print("\n🔨 Phase 5: Intelligent Code Assembly...")
            generated_file = self.code_assembler.assemble_complete_program(user_query, memory)
            print(f"  ✅ Code Generated: {os.path.basename(generated_file)}")
            
            print("\n" + "=" * 60)
            print(f"✅ QuantumForge V5 Generation Complete!")
            print(f"📁 Output: {generated_file}")
            
            return generated_file
            
        except Exception as e:
            print(f"\n❌ QuantumForge V5 Generation Failed: {e}")
            raise e
        
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"qf5_{timestamp}"
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            系统状态和组件信息
        """
        available_components = self.component_discovery.get_available_components()
        
        return {
            "version": "5.0.0",
            "model": self.model,
            "session_id": self.session_id,
            "available_components": list(available_components.keys()),
            "total_components": len(available_components),
            "system_ready": True,
            "components": {
                "semantic_engine": "✅ Ready",
                "component_discovery": "✅ Ready", 
                "pipeline_composer": "✅ Ready",
                "parameter_matcher": "✅ Ready",
                "code_assembler": "✅ Ready"
            }
        }
    
    def batch_generate(self, queries: List[str]) -> List[str]:
        """
        批量生成量子代码
        
        Args:
            queries: 用户查询列表
            
        Returns:
            生成的代码文件路径列表
        """
        results = []
        
        print(f"🚀 Batch Generation: {len(queries)} queries")
        print("=" * 60)
        
        for i, query in enumerate(queries):
            print(f"\n📋 Processing batch {i+1}/{len(queries)}")
            try:
                result = self.generate_quantum_code(query)
                results.append(result)
                print(f"✅ Batch {i+1} completed: {os.path.basename(result)}")
            except Exception as e:
                print(f"❌ Batch {i+1} failed: {e}")
                results.append(None)
        
        successful_results = [r for r in results if r is not None]
        print(f"\n📊 Batch Summary: {len(successful_results)}/{len(queries)} successful")
        
        return results
