"""
QuantumForge V4 Tool Registry System

工具注册系统，负责自动发现和注册所有可用工具。
"""

import os
import importlib
import inspect
from typing import List, Type
from base_tool import BaseTool


class ToolRegistry:
    """
    工具注册器
    
    功能:
    - 自动发现tools目录下的所有工具类
    - 注册工具到Orchestrator
    - 支持插件化工具加载
    """
    
    def __init__(self):
        self.discovered_tools: List[Type[BaseTool]] = []
        
    def discover_tools(self) -> List[Type[BaseTool]]:
        """
        自动发现所有可用的工具类
        
        Returns:
            发现的工具类列表
        """
        tools = []
        
        # 注册已知工具
        try:
            from tfim.tfim_model_generator import TFIMModelGenerator
            tools.append(TFIMModelGenerator)
            print(f"✅ Discovered tool: {TFIMModelGenerator.__name__}")
        except Exception as e:
            print(f"⚠️ Failed to load TFIMModelGenerator: {e}")
        
        try:
            from tfim.tfim_hamiltonian_builder import TFIMHamiltonianBuilder
            tools.append(TFIMHamiltonianBuilder)
            print(f"✅ Discovered tool: {TFIMHamiltonianBuilder.__name__}")
        except Exception as e:
            print(f"⚠️ Failed to load TFIMHamiltonianBuilder: {e}")
        
        try:
            from tfim.tfim_vqe_circuit_builder import TFIMVQECircuitBuilder
            tools.append(TFIMVQECircuitBuilder)
            print(f"✅ Discovered tool: {TFIMVQECircuitBuilder.__name__}")
        except Exception as e:
            print(f"⚠️ Failed to load TFIMVQECircuitBuilder: {e}")
        
        try:
            from tfim.tfim_vqe_optimizer import TFIMVQEOptimizer
            tools.append(TFIMVQEOptimizer)
            print(f"✅ Discovered tool: {TFIMVQEOptimizer.__name__}")
        except Exception as e:
            print(f"⚠️ Failed to load TFIMVQEOptimizer: {e}")
        
        try:
            from tfim.qiskit_tfim_executor import QiskitTFIMExecutor
            tools.append(QiskitTFIMExecutor)
            print(f"✅ Discovered tool: {QiskitTFIMExecutor.__name__}")
        except Exception as e:
            print(f"⚠️ Failed to load QiskitTFIMExecutor: {e}")
        
        try:
            from tfim.qiskit_code_assembler import QiskitCodeAssembler
            tools.append(QiskitCodeAssembler)
            print(f"✅ Discovered tool: {QiskitCodeAssembler.__name__}")
        except Exception as e:
            print(f"⚠️ Failed to load QiskitCodeAssembler: {e}")
        
        if not tools:
            print("⚠️ No tools discovered. Please implement actual tools.")
        
        self.discovered_tools = tools
        return tools
    
    
    def register_all_tools(self, orchestrator):
        """
        将所有发现的工具注册到Orchestrator
        
        Args:
            orchestrator: IntelligentToolOrchestrator实例
        """
        if not self.discovered_tools:
            self.discover_tools()
        
        registered_count = 0
        for tool_class in self.discovered_tools:
            try:
                orchestrator.register_tool(tool_class)
                registered_count += 1
                print(f"✅ Registered tool: {tool_class.__name__}")
            except Exception as e:
                print(f"❌ Failed to register {tool_class.__name__}: {e}")
        
        print(f"🎯 Total tools registered: {registered_count}")
    
    def get_tool_info(self) -> dict:
        """
        获取所有工具的信息
        
        Returns:
            工具信息字典
        """
        if not self.discovered_tools:
            self.discover_tools()
        
        tool_info = {}
        for tool_class in self.discovered_tools:
            tool_info[tool_class.__name__] = {
                "module": tool_class.__module__,
                "docstring": tool_class.__doc__ or "No description available",
                "file": inspect.getfile(tool_class)
            }
        
        return tool_info


# 全局注册器实例
_tool_registry = None

def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册器实例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def register_all_tools(orchestrator):
    """
    便捷函数：注册所有工具到Orchestrator
    
    Args:
        orchestrator: IntelligentToolOrchestrator实例
    """
    registry = get_tool_registry()
    registry.register_all_tools(orchestrator)


def discover_tools() -> List[Type[BaseTool]]:
    """
    便捷函数：发现所有可用工具
    
    Returns:
        工具类列表
    """
    registry = get_tool_registry()
    return registry.discover_tools()


# 示例使用
if __name__ == "__main__":
    print("Testing Tool Registry...")
    
    registry = ToolRegistry()
    tools = registry.discover_tools()
    
    print(f"\nDiscovered {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.__name__}: {tool.__doc__ or 'No description'}")
    
    print("\nTool Info:")
    tool_info = registry.get_tool_info()
    for name, info in tool_info.items():
        print(f"  {name}: {info['module']}")