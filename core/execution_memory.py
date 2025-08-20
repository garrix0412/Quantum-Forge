"""
Execution Memory - QuantumForge V5 执行记忆系统

适配V5架构的智能执行记忆系统，支持组件导向和LLM智能参数匹配。
基于V4 Memory系统改进，去除硬编码依赖。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class ExecutionMemory:
    """
    V5架构的智能执行记忆系统
    
    改进点:
    - 组件导向而非工具导向
    - LLM友好的上下文提取
    - 语义化参数匹配支持
    - 去除硬编码依赖关系
    """
    
    def __init__(self):
        """初始化ExecutionMemory系统"""
        self.original_query = ""
        self.quantum_intent: Optional[Dict[str, Any]] = None  # 存储语义理解结果
        self.execution_history: List[Dict[str, Any]] = []  # 组件执行历史
        self.current_state: Dict[str, Any] = {}  # 当前全局状态
        self.generated_code_fragments: List[str] = []  # 代码片段
        
    def initialize(self, query: str, intent: Dict[str, Any]):
        """
        初始化执行记忆
        
        Args:
            query: 用户原始查询
            intent: 语义理解结果
        """
        self.original_query = query
        self.quantum_intent = intent
        self.current_state = {
            "query": query,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "status": "initialized"
        }
    
    def store_component_output(self, component_name: str, output: Dict[str, Any]):
        """
        存储组件执行输出
        
        Args:
            component_name: 组件名称
            output: 组件输出结果
        """
        # 保存执行前状态
        memory_before = self.current_state.copy()
        
        # 创建执行记录
        step = {
            "step_number": len(self.execution_history) + 1,
            "component_name": component_name,
            "timestamp": datetime.now().isoformat(),
            "output": output,
            "memory_before": memory_before,
            "memory_after": None  # 稍后更新
        }
        
        # 更新当前状态
        self._update_current_state(component_name, output)
        step["memory_after"] = self.current_state.copy()
        
        # 添加到历史
        self.execution_history.append(step)
        
        # 如果输出包含代码，添加到代码片段
        if "code" in output:
            self.generated_code_fragments.append(output["code"])
    
    def _update_current_state(self, component_name: str, output: Dict[str, Any]):
        """
        更新当前状态 - 通用化处理，算法无关
        只处理真正通用的字段，让LLM智能理解其他信息
        """
        self.current_state["last_component"] = component_name
        self.current_state["last_output"] = output
        self.current_state["total_steps"] = len(self.execution_history) + 1
        
        # 只处理真正通用的字段 - 代码生成（所有算法最终都生成代码）
        if "code" in output:
            self.current_state["has_code"] = True
            self.current_state["code_count"] = len(self.generated_code_fragments) + 1
        
        # 其他算法特定字段（hamiltonian, parameters, oracle, cost_function等）
        # 都通过 get_all_outputs() 和 get_context_for_llm() 让LLM智能处理
        # 保持系统的算法无关性和扩展性
    
    def get_all_outputs(self) -> Dict[str, Any]:
        """
        获取所有组件输出，供LLM参数匹配使用
        
        Returns:
            包含所有历史输出的结构化字典
        """
        all_outputs = {
            "original_query": self.original_query,
            "quantum_intent": self.quantum_intent,
            "component_outputs": {}
        }
        
        # 按组件整理输出
        for step in self.execution_history:
            component_name = step["component_name"]
            all_outputs["component_outputs"][component_name] = step["output"]
        
        # 添加当前状态
        all_outputs["current_state"] = self.current_state
        
        return all_outputs
    
    def get_component_output(self, component_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定组件的输出
        
        Args:
            component_name: 组件名称
            
        Returns:
            组件输出或None
        """
        for step in self.execution_history:
            if step["component_name"] == component_name:
                return step["output"]
        return None
    
    def get_latest_parameters(self) -> Dict[str, Any]:
        """
        获取最新的参数集合 - 通用化处理
        智能查找各种参数字段，不限于 "parameters"
        
        Returns:
            最新参数字典
        """
        # 从最近的组件开始查找，查找各种可能的参数字段
        parameter_fields = ["parameters", "params", "config", "settings"]
        
        for step in reversed(self.execution_history):
            for field in parameter_fields:
                if field in step["output"]:
                    return step["output"][field]
        
        # 如果没有找到组件参数，返回intent中的参数
        if self.quantum_intent:
            return self.quantum_intent.get("parameters", {})
        
        return {}
    
    def get_context_for_llm(self, target_component: str) -> str:
        """
        为LLM参数匹配提供结构化上下文
        
        Args:
            target_component: 目标组件名称
            
        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        
        # 基本信息
        context_parts.append(f"Original Query: {self.original_query}")
        
        if self.quantum_intent:
            context_parts.append(f"Problem Type: {self.quantum_intent.get('problem_type', 'Unknown')}")
            context_parts.append(f"Algorithm: {self.quantum_intent.get('algorithm', 'Unknown')}")
        
        context_parts.append(f"Target Component: {target_component}")
        context_parts.append(f"Current Step: {len(self.execution_history) + 1}")
        
        # 可用数据
        if self.execution_history:
            context_parts.append("\nAvailable Data from Previous Components:")
            for step in self.execution_history:
                component = step["component_name"]
                output = step["output"]
                context_parts.append(f"  {component}:")
                
                # 提取关键输出信息
                for key, value in output.items():
                    if key != "code":  # 代码太长，不包含在上下文中
                        context_parts.append(f"    {key}: {value}")
        
        # 当前参数状态
        latest_params = self.get_latest_parameters()
        if latest_params:
            context_parts.append(f"\nLatest Parameters: {latest_params}")
        
        return "\n".join(context_parts)
    
    def get_final_code(self) -> str:
        """获取最终生成的代码"""
        if not self.execution_history:
            return "No code generated - no components executed."
        
        # 从最后一个组件的输出中获取代码
        last_output = self.execution_history[-1]["output"]
        if "code" in last_output:
            return last_output["code"]
        
        # 如果最后一个组件没有代码，尝试获取所有代码片段
        if self.generated_code_fragments:
            return self.generated_code_fragments[-1]
        
        return "No final code available."
    
    def get_all_code_fragments(self) -> str:
        """获取所有生成的代码片段"""
        if not self.generated_code_fragments:
            return "No code fragments generated yet."
        
        return "\n\n# ===== CODE FRAGMENT SEPARATOR =====\n\n".join(self.generated_code_fragments)
    
    def get_summary(self) -> str:
        """获取执行摘要"""
        return f"""
ExecutionMemory Summary:
- Original Query: {self.original_query}
- Problem Type: {self.quantum_intent.get('problem_type', 'Unknown') if self.quantum_intent else 'Unknown'}
- Algorithm: {self.quantum_intent.get('algorithm', 'Unknown') if self.quantum_intent else 'Unknown'}
- Components Executed: {len(self.execution_history)}
- Code Fragments: {len(self.generated_code_fragments)}
- Current Status: {self.current_state.get('status', 'unknown')}
        """.strip()
