"""
QuantumForge V4 Memory System

完整历史存储系统，用于在工具链执行过程中保存和传递上下文信息。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class Memory:
    """
    存储工具链执行的完整历史和上下文信息
    
    核心功能:
    - 存储每个工具的完整输出
    - 为后续工具提供相关历史上下文  
    - 跟踪执行历史和状态变化
    - 智能上下文提取和压缩
    """
    
    def __init__(self):
        """初始化Memory系统"""
        self.original_query = ""
        self.execution_history: List[Dict[str, Any]] = []
        self.current_state: Dict[str, Any] = {}
        self.generated_code_fragments: List[str] = []
        
    def initialize_query(self, query: str):
        """初始化用户查询"""
        self.original_query = query
        self.current_state = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "status": "initialized"
        }
    
    def add_tool_output(self, tool_name: str, output: Dict[str, Any]):
        """
        添加工具输出到历史记录
        
        Args:
            tool_name: 工具名称
            output: 工具输出结果
        """
        # 保存执行前状态
        memory_before = self.current_state.copy()
        
        # 创建执行记录
        step = {
            "step_number": len(self.execution_history) + 1,
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "output": output,
            "memory_before": memory_before,
            "memory_after": None  # 稍后更新
        }
        
        # 更新当前状态
        self._update_current_state(tool_name, output)
        step["memory_after"] = self.current_state.copy()
        
        # 添加到历史
        self.execution_history.append(step)
        
        # 如果输出包含代码，添加到代码片段
        if "code" in output:
            self.generated_code_fragments.append(output["code"])
    
    def _update_current_state(self, tool_name: str, output: Dict[str, Any]):
        """更新当前状态"""
        self.current_state["last_tool"] = tool_name
        self.current_state["last_output"] = output
        self.current_state["total_steps"] = len(self.execution_history) + 1
        
        # 提取关键信息到状态
        if "parameters" in output:
            self.current_state["parameters"] = output["parameters"]
        
        if "code" in output:
            self.current_state["has_code"] = True
            self.current_state["code_count"] = len(self.generated_code_fragments) + 1
    
    def get_context_for_tool(self, tool_name: str) -> str:
        """
        为特定工具提取相关历史上下文
        
        Args:
            tool_name: 目标工具名称
            
        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        
        # 基本信息
        context_parts.append(f"Original Query: {self.original_query}")
        context_parts.append(f"Current Step: {len(self.execution_history) + 1}")
        
        # 执行历史
        if self.execution_history:
            context_parts.append("\\nExecution History:")
            for step in self.execution_history:
                context_parts.append(f"Step {step['step_number']}: {step['tool_name']}")
                
                # 简化输出信息
                output_summary = self._summarize_output(step['output'])
                context_parts.append(f"  Output: {output_summary}")
        
        # 当前状态
        if self.current_state:
            context_parts.append("\\nCurrent State:")
            context_parts.append(f"  Total Steps: {self.current_state.get('total_steps', 0)}")
            context_parts.append(f"  Code Fragments: {len(self.generated_code_fragments)}")
            
            if "parameters" in self.current_state:
                context_parts.append(f"  Parameters: {self.current_state['parameters']}")
        
        return "\\n".join(context_parts)
    
    def _summarize_output(self, output: Dict[str, Any]) -> str:
        """简化输出信息用于上下文"""
        summary_parts = []
        
        if "code" in output:
            code_preview = output["code"][:100] + "..." if len(output["code"]) > 100 else output["code"]
            summary_parts.append(f"Code: {code_preview}")
        
        if "parameters" in output:
            summary_parts.append(f"Parameters: {output['parameters']}")
        
        if "notes" in output:
            summary_parts.append(f"Notes: {output['notes']}")
        
        return "; ".join(summary_parts) if summary_parts else str(output)
    
    def get_all_code_fragments(self) -> str:
        """获取所有生成的代码片段"""
        if not self.generated_code_fragments:
            return "No code fragments generated yet."
        
        return "\\n\\n# ===== CODE FRAGMENT SEPARATOR =====\\n\\n".join(self.generated_code_fragments)
    
    def get_final_code(self) -> str:
        """获取最终生成的代码"""
        if not self.execution_history:
            return "No code generated - no tools executed."
        
        # 从最后一个工具的输出中获取代码
        last_output = self.execution_history[-1]["output"]
        if "code" in last_output:
            return last_output["code"]
        
        # 如果最后一个工具没有代码，尝试获取所有代码片段
        if self.generated_code_fragments:
            return self.generated_code_fragments[-1]
        
        return "No final code available."
    
    def get_summary(self) -> str:
        """获取Memory状态摘要"""
        return f"""
Memory Summary:
- Original Query: {self.original_query}
- Steps Executed: {len(self.execution_history)}
- Code Fragments: {len(self.generated_code_fragments)}
- Current Status: {self.current_state.get('status', 'unknown')}
        """.strip()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要，用于LLM判断"""
        return {
            "original_query": self.original_query,
            "total_steps": len(self.execution_history),
            "executed_tools": [step["tool_name"] for step in self.execution_history],
            "has_code_fragments": len(self.generated_code_fragments) > 0,
            "current_status": self.current_state.get("status", "unknown"),
            "last_tool": self.current_state.get("last_tool", "none"),
            "code_count": len(self.generated_code_fragments)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """将Memory转换为字典格式"""
        return {
            "original_query": self.original_query,
            "execution_history": self.execution_history,
            "current_state": self.current_state,
            "generated_code_fragments": self.generated_code_fragments
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """从字典恢复Memory状态"""
        self.original_query = data.get("original_query", "")
        self.execution_history = data.get("execution_history", [])
        self.current_state = data.get("current_state", {})
        self.generated_code_fragments = data.get("generated_code_fragments", [])