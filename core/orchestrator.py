"""
QuantumForge V4 Intelligent Tool Orchestrator

LLM驱动的工具编排器，负责动态选择工具和控制执行流程。
"""

from typing import Dict, Any, Optional, List
from memory import Memory
from llm_engine import call_llm
import json
import time
from datetime import datetime


class ResourceManager:
    """
    资源管理器 - 控制LLM调用、token使用和执行时间
    """
    
    def __init__(self):
        # 资源限制配置
        self.max_llm_calls = 20            # 最大LLM调用次数
        self.max_total_tokens = 100000     # 最大总token数
        self.max_execution_time = 300      # 最大执行时间(秒)
        self.max_context_length = 15000    # 最大上下文长度
        
        # 当前使用统计
        self.current_llm_calls = 0
        self.current_tokens = 0
        self.start_time = None
        self.execution_log = []
        
    def start_execution(self):
        """开始执行，重置统计"""
        self.start_time = time.time()
        self.current_llm_calls = 0
        self.current_tokens = 0
        self.execution_log = []
        
    def can_make_llm_call(self) -> bool:
        """检查是否可以进行LLM调用"""
        if self.current_llm_calls >= self.max_llm_calls:
            return False
        
        if self.start_time and (time.time() - self.start_time) > self.max_execution_time:
            return False
            
        return True
    
    def record_llm_call(self, prompt_tokens: int, response_tokens: int):
        """记录LLM调用"""
        self.current_llm_calls += 1
        self.current_tokens += prompt_tokens + response_tokens
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "call_number": self.current_llm_calls,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": self.current_tokens
        })
    
    def get_remaining_resources(self) -> Dict[str, Any]:
        """获取剩余资源"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "remaining_calls": self.max_llm_calls - self.current_llm_calls,
            "remaining_tokens": self.max_total_tokens - self.current_tokens,
            "remaining_time": self.max_execution_time - elapsed_time,
            "current_calls": self.current_llm_calls,
            "current_tokens": self.current_tokens,
            "elapsed_time": elapsed_time
        }
    
    def is_context_too_long(self, context: str) -> bool:
        """检查上下文是否过长"""
        # 简单的token估算：字符数/4
        estimated_tokens = len(context) / 4
        return estimated_tokens > self.max_context_length


class IntelligentToolOrchestrator:
    """
    智能工具编排器
    
    核心功能:
    - LLM驱动的工具选择和执行顺序决策
    - 与Memory系统集成，维护完整历史
    - 动态评估执行进度，决定是否继续
    - 生成完整的量子计算代码
    """
    
    def __init__(self):
        """初始化编排器"""
        self.memory = Memory()
        self.available_tools = []  # 将通过工具注册系统填充
        self.resource_manager = ResourceManager()
        self.execution_status = "ready"  # ready, running, completed, failed, stopped
        
    def register_tool(self, tool_class):
        """注册可用工具"""
        self.available_tools.append(tool_class)
        print(f"🔧 Registered tool: {tool_class.__name__}")
    
    def load_all_tools(self):
        """自动加载所有可用工具"""
        try:
            # 导入工具注册系统
            import sys
            import os
            
            # 添加tools目录到路径
            tools_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools')
            if tools_path not in sys.path:
                sys.path.append(tools_path)
            
            # 导入并使用工具注册系统
            from registry import register_all_tools
            register_all_tools(self)
            
        except Exception as e:
            print(f"⚠️ Failed to auto-load tools: {e}")
            print("Please register tools manually using register_tool()")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "status": self.execution_status,
            "available_tools": [tool.__name__ for tool in self.available_tools],
            "resource_stats": self.resource_manager.get_remaining_resources(),
            "execution_log": self.resource_manager.execution_log
        }
    
    def generate_quantum_code(self, user_query: str) -> Dict[str, Any]:
        """
        主入口点：根据用户查询生成完整的量子代码
        
        Args:
            user_query: 用户的自然语言查询
            
        Returns:
            包含代码和执行信息的字典
        """
        try:
            # 开始执行
            self.execution_status = "running"
            self.resource_manager.start_execution()
            self.memory.initialize_query(user_query)
            
            print(f"🚀 Starting quantum code generation for: {user_query}")
            print(f"📊 Available tools: {len(self.available_tools)}")
            
            # 主执行循环
            max_iterations = 10  # 防止无限循环
            iteration = 0
            stop_reason = "max_iterations"
            
            while iteration < max_iterations:
                iteration += 1
                print(f"\n🔄 Iteration {iteration}")
                
                # 检查资源限制
                if not self.resource_manager.can_make_llm_call():
                    print("⏰ Resource limits reached")
                    stop_reason = "resource_limit"
                    break
                
                # LLM选择下一个工具
                next_tool_name = self._llm_select_next_tool()
                print(f"🎯 LLM selected tool: {next_tool_name}")
                
                # 检查是否完成
                if next_tool_name == "COMPLETE":
                    stop_reason = "completed"
                    break
                
                # 执行选定的工具
                tool_output = self._execute_tool(next_tool_name)
                
                # 检查工具执行是否成功
                if "error" in tool_output:
                    print(f"❌ Tool execution failed: {tool_output['error']}")
                    # 继续执行其他工具，不中断流程
                
                # 将输出添加到Memory
                self.memory.add_tool_output(next_tool_name, tool_output)
                
                # 检查资源限制后再次调用LLM
                if not self.resource_manager.can_make_llm_call():
                    print("⏰ Resource limits reached before progress evaluation")
                    stop_reason = "resource_limit"
                    break
                
                # LLM评估是否继续
                should_continue = self._llm_evaluate_progress()
                print(f"🤔 LLM decision: {'Continue' if should_continue else 'Stop'}")
                
                if not should_continue:
                    stop_reason = "llm_decision"
                    break
            
            self.execution_status = "completed"
            
            # 返回完整结果
            result = {
                "code": self.memory.get_final_code(),
                "stop_reason": stop_reason,
                "iterations": iteration,
                "resources_used": self.resource_manager.get_remaining_resources(),
                "memory_summary": self.memory.get_summary(),
                "execution_log": self.resource_manager.execution_log
            }
            
            print(f"\n✅ Execution completed: {stop_reason}")
            print(f"📊 Used {self.resource_manager.current_llm_calls} LLM calls")
            
            return result
            
        except Exception as e:
            self.execution_status = "failed"
            print(f"💥 Execution failed: {str(e)}")
            
            return {
                "code": self.memory.get_final_code() if self.memory.execution_history else "",
                "stop_reason": "error",
                "error": str(e),
                "iterations": iteration if 'iteration' in locals() else 0,
                "resources_used": self.resource_manager.get_remaining_resources(),
                "memory_summary": self.memory.get_summary() if self.memory.execution_history else "No execution history"
            }
    
    def _llm_select_next_tool(self) -> str:
        """
        使用LLM动态选择下一个要执行的工具
        
        Returns:
            工具名称或"COMPLETE"表示完成
        """
        # 获取上下文并检查长度
        context = self.memory.get_context_for_tool("tool_selector")
        
        # 如果上下文过长，进行压缩
        if self.resource_manager.is_context_too_long(context):
            print("⚠️ Context too long, compressing...")
            # 简单压缩：只保留最后几步和原始查询
            lines = context.split('\n')
            compressed_context = '\n'.join(lines[:5] + lines[-10:])  # 保留前5行和后10行
            context = compressed_context
        
        available_tools_str = ", ".join([tool.__name__ for tool in self.available_tools])
        
        prompt = f"""
Based on the following context, select the next tool to execute for quantum code generation.

{context}

Available tools: {available_tools_str}

Current task: Generate complete quantum code for the user's query.

Please respond with ONLY the tool name (e.g., "TFIMModelGenerator") or "COMPLETE" if all necessary steps are done.

Tool selection:"""

        # 估算token并记录
        estimated_prompt_tokens = len(prompt) // 4
        response = call_llm(prompt, temperature=0.1)
        estimated_response_tokens = len(response) // 4
        
        # 记录到资源管理器
        self.resource_manager.record_llm_call(estimated_prompt_tokens, estimated_response_tokens)
        
        # 清理响应，只保留工具名称
        tool_name = response.strip().replace('"', '').replace("'", '')
        
        return tool_name
    
    def _llm_evaluate_progress(self) -> bool:
        """
        使用LLM评估当前进度，决定是否继续执行
        
        Returns:
            True表示继续，False表示停止
        """
        execution_summary = self.memory.get_execution_summary()
        resources = self.resource_manager.get_remaining_resources()
        
        prompt = f"""
Evaluate the current progress of quantum code generation:

Original Query: {execution_summary['original_query']}
Steps Executed: {execution_summary['total_steps']}
Tools Used: {execution_summary['executed_tools']}
Has Code: {execution_summary['has_code_fragments']}

Remaining Resources:
- LLM Calls: {resources['remaining_calls']}
- Tokens: {resources['remaining_tokens']}
- Time: {resources['remaining_time']:.1f}s

Analysis Guidelines:
- TFIM queries typically need: 1) Model parameters AND 2) Hamiltonian construction
- "Complete TFIM Hamiltonian" requires both model generation and Pauli operator construction
- "Hamiltonian" or "Pauli" in query suggests need for TFIMHamiltonianBuilder
- "VQE", "ground state", "energy", "optimization" in query requires full VQE pipeline:
  Model → Hamiltonian → Circuit → Optimizer → Executor → Assembler
- "Calculate ground state energy" requires ALL 6 tools for complete code generation
- "Execute VQE", "run VQE", "compute energy" requires final QiskitTFIMExecutor and QiskitCodeAssembler
- "Complete code", "final code", "save file" requires QiskitCodeAssembler for integration
- Continue if query asks for complete/full implementation but missing components
- Continue if ground state energy calculation requested but no code assembler used yet
- Continue if VQE execution requested but no final code integration
- Stop only if all requested components including final code assembly are implemented

Based on this analysis and remaining resources, should we continue with more tools or is the task complete?

Respond with only "CONTINUE" or "STOP".

Decision:"""

        # 估算token并记录
        estimated_prompt_tokens = len(prompt) // 4
        response = call_llm(prompt, temperature=0.1)
        estimated_response_tokens = len(response) // 4
        
        # 记录到资源管理器
        self.resource_manager.record_llm_call(estimated_prompt_tokens, estimated_response_tokens)
        
        return response.strip().upper() == "CONTINUE"
    
    def _execute_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        执行指定的工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具执行结果
        """
        # 查找工具类
        tool_class = None
        for tool in self.available_tools:
            if tool.__name__ == tool_name:
                tool_class = tool
                break
        
        if tool_class is None:
            return {
                "error": f"Tool {tool_name} not found",
                "code": "",
                "notes": f"Failed to find tool: {tool_name}"
            }
        
        try:
            # 实例化工具
            tool_instance = tool_class()
            
            # 获取当前上下文
            context = self.memory.get_context_for_tool(tool_name)
            
            # 执行工具
            result = tool_instance.execute(context)
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "code": "",
                "notes": f"Tool execution failed: {str(e)}"
            }
    
    def get_memory_summary(self) -> str:
        """获取Memory系统摘要"""
        return self.memory.get_summary()
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取完整执行历史"""
        return self.memory.execution_history




# 示例使用
if __name__ == "__main__":
    print("IntelligentToolOrchestrator is ready.")
    print("Please use this class by importing it and registering real tools.")
    print("Example:")
    print("  orchestrator = IntelligentToolOrchestrator()")
    print("  orchestrator.load_all_tools()  # Auto-load tools")
    print("  result = orchestrator.generate_quantum_code('Your query')")