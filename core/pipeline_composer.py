"""
Pipeline Composer - QuantumForge V5 智能流水线组合引擎

LLM驱动的量子组件执行流水线设计系统。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 2.2 设计。
"""

import json
from typing import Dict, Any, List, Tuple, Optional

# 导入相关类型
try:
    from .semantic_engine import QuantumIntent
    from .llm_engine import call_llm
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.semantic_engine import QuantumIntent
    from core.llm_engine import call_llm


class IntelligentPipelineComposer:
    """
    LLM驱动的智能流水线组合引擎
    
    核心功能:
    - 分析组件之间的依赖关系
    - 设计最优的执行顺序
    - 识别并行执行的可能性
    - 优化流水线性能和逻辑
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
    
    def compose_execution_pipeline(self, intent: QuantumIntent, 
                                  component_names: List[str],
                                  component_descriptions: Dict[str, str]) -> List[str]:
        """
        设计最优的组件执行流水线
        
        Args:
            intent: 量子问题意图
            component_names: 发现的相关组件名称列表
            component_descriptions: 组件名称到描述的映射
            
        Returns:
            优化后的组件执行顺序列表
        """
        if not component_names:
            return []
        
        # 如果只有一个组件，直接返回
        if len(component_names) == 1:
            return component_names
        
        # 构建流水线设计prompt
        prompt = self._build_pipeline_prompt(intent, component_names, component_descriptions)
        
        # LLM分析设计流水线
        try:
            response = call_llm(prompt, model=self.model)
            pipeline = self._parse_pipeline_response(response, component_names)
            return pipeline
            
        except Exception as e:
            # LLM失败时的fallback策略
            return self._fallback_pipeline_design(intent, component_names)
    
    def _build_pipeline_prompt(self, intent: QuantumIntent, 
                              component_names: List[str],
                              component_descriptions: Dict[str, str]) -> str:
        """构建流水线设计的LLM prompt"""
        
        # 格式化组件信息
        component_info = []
        for name in component_names:
            desc = component_descriptions.get(name, f"Component: {name}")
            component_info.append(f"- {name}: {desc}")
        
        component_list = "\n".join(component_info)
        
        return f"""
Design the optimal execution pipeline for this quantum computing workflow:

Problem Context:
- Problem Type: {intent.problem_type}
- Algorithm: {intent.algorithm}
- Parameters: {intent.parameters}
- Requirements: {intent.requirements}

Available Components:
{component_list}

Task: Design the logical execution sequence considering:

1. **Quantum Algorithm Workflow**:
   - Model/Problem Setup → Parameters → Hamiltonian/Oracle → Circuit/Ansatz → Optimization/Execution

2. **Data Dependencies**:
   - Which components need outputs from others?
   - What is the natural information flow?

3. **Quantum Physics Logic**:
   - TFIM: Parameters → Hamiltonian → VQE Circuit → Optimization
   - QAOA: Graph Problem → Hamiltonians → QAOA Circuit → Optimization
   - Grover: Oracle → Diffuser → Grover Circuit → Execution

4. **Best Practices**:
   - Setup before execution
   - Parameters before circuits
   - Circuits before optimization

Return ONLY a JSON list of component names in optimal execution order:
["FirstComponent", "SecondComponent", "ThirdComponent"]

Important:
- Use exact component names from the available list
- Order by logical dependencies, not alphabetical
- Consider quantum algorithm best practices
- Ensure data flow makes physical sense

JSON:"""
    
    def _parse_pipeline_response(self, response: str, valid_components: List[str]) -> List[str]:
        """解析LLM的流水线设计响应"""
        # 清理响应，提取JSON部分
        response = response.strip()
        
        # 如果包含代码块标记，提取其中的JSON
        if '```' in response:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                response = response[start:end]
        
        try:
            # 解析JSON列表
            pipeline = json.loads(response)
            
            # 验证返回的是列表
            if not isinstance(pipeline, list):
                raise ValueError("Response is not a list")
            
            # 验证并过滤有效组件
            valid_pipeline = []
            for component in pipeline:
                if isinstance(component, str) and component in valid_components:
                    # 避免重复
                    if component not in valid_pipeline:
                        valid_pipeline.append(component)
            
            # 确保所有组件都包含在流水线中
            missing_components = [comp for comp in valid_components if comp not in valid_pipeline]
            valid_pipeline.extend(missing_components)
            
            return valid_pipeline
            
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse LLM pipeline response: {e}")
    
    def _fallback_pipeline_design(self, intent: QuantumIntent, component_names: List[str]) -> List[str]:
        """
        LLM失败时的后备流水线设计策略
        基于量子算法工作流的简单规则
        """
        problem_type = intent.problem_type.upper()
        
        # 基于问题类型的流水线模式
        if "TFIM" in problem_type:
            return self._tfim_pipeline_pattern(component_names)
        elif "QAOA" in problem_type:
            return self._qaoa_pipeline_pattern(component_names)
        elif "GROVER" in problem_type:
            return self._grover_pipeline_pattern(component_names)
        else:
            return self._generic_pipeline_pattern(component_names)
    
    def _tfim_pipeline_pattern(self, components: List[str]) -> List[str]:
        """TFIM算法的标准流水线模式"""
        pipeline = []
        
        # 优先级顺序
        priority_order = [
            ("ModelGenerator", "Model"),
            ("ParameterExtractor", "Parameter"), 
            ("HamiltonianBuilder", "Hamiltonian"),
            ("VQECircuitBuilder", "VQE", "Circuit"),
            ("VQEOptimizer", "Optimizer"),
            ("VQEExecutor", "Executor")
        ]
        
        # 按优先级匹配组件
        for priority_keywords in priority_order:
            for component in components:
                if any(keyword in component for keyword in priority_keywords):
                    if component not in pipeline:
                        pipeline.append(component)
                        break
        
        # 添加未匹配的组件
        for component in components:
            if component not in pipeline:
                pipeline.append(component)
        
        return pipeline
    
    def _qaoa_pipeline_pattern(self, components: List[str]) -> List[str]:
        """QAOA算法的标准流水线模式"""
        pipeline = []
        
        # QAOA流水线模式
        priority_order = [
            ("GraphProblem", "Graph", "Problem"),
            ("HamiltonianBuilder", "Hamiltonian", "Cost"),
            ("QAOACircuitBuilder", "QAOA", "Circuit"),
            ("QAOAOptimizer", "Optimizer"),
            ("QAOAExecutor", "Executor")
        ]
        
        for priority_keywords in priority_order:
            for component in components:
                if any(keyword in component for keyword in priority_keywords):
                    if component not in pipeline:
                        pipeline.append(component)
                        break
        
        # 添加未匹配的组件
        for component in components:
            if component not in pipeline:
                pipeline.append(component)
        
        return pipeline
    
    def _grover_pipeline_pattern(self, components: List[str]) -> List[str]:
        """Grover算法的标准流水线模式"""
        pipeline = []
        
        # Grover流水线模式
        priority_order = [
            ("OracleBuilder", "Oracle"),
            ("DiffuserBuilder", "Diffuser"), 
            ("GroverCircuitBuilder", "Grover", "Circuit"),
            ("GroverExecutor", "Executor")
        ]
        
        for priority_keywords in priority_order:
            for component in components:
                if any(keyword in component for keyword in priority_keywords):
                    if component not in pipeline:
                        pipeline.append(component)
                        break
        
        # 添加未匹配的组件
        for component in components:
            if component not in pipeline:
                pipeline.append(component)
        
        return pipeline
    
    def _generic_pipeline_pattern(self, components: List[str]) -> List[str]:
        """通用的流水线模式"""
        pipeline = []
        
        # 通用优先级
        priority_order = [
            ("ModelGenerator", "Model", "Parameter"),
            ("HamiltonianBuilder", "Hamiltonian"),
            ("CircuitBuilder", "Circuit", "Ansatz"),
            ("Optimizer", "Optimization"),
            ("Executor", "Execution")
        ]
        
        for priority_keywords in priority_order:
            for component in components:
                if any(keyword in component for keyword in priority_keywords):
                    if component not in pipeline:
                        pipeline.append(component)
                        break
        
        # 添加未匹配的组件
        for component in components:
            if component not in pipeline:
                pipeline.append(component)
        
        return pipeline
    
    def analyze_pipeline_dependencies(self, pipeline: List[str], 
                                    component_descriptions: Dict[str, str]) -> Dict[str, Any]:
        """
        分析流水线中组件的依赖关系
        
        Args:
            pipeline: 组件执行顺序
            component_descriptions: 组件描述
            
        Returns:
            依赖关系分析结果
        """
        analysis = {
            "pipeline_length": len(pipeline),
            "execution_order": pipeline,
            "dependencies": {},
            "parallel_opportunities": [],
            "critical_path": pipeline  # 简化实现，假设所有组件都在关键路径上
        }
        
        # 分析每个组件的依赖
        for i, component in enumerate(pipeline):
            analysis["dependencies"][component] = {
                "position": i,
                "depends_on": pipeline[:i] if i > 0 else [],
                "enables": pipeline[i+1:] if i < len(pipeline)-1 else []
            }
        
        return analysis

