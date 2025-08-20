"""
Component Discovery - QuantumForge V5 智能组件发现引擎

LLM驱动的量子组件自动发现系统。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 2.1 设计。
"""

import os
import importlib
import inspect
import json
from typing import Dict, Any, List, Type
from pathlib import Path

# 导入相关类型
try:
    from .semantic_engine import QuantumIntent
    from ..components.base_component import BaseComponent
    from .llm_engine import call_llm
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.semantic_engine import QuantumIntent
    from components.base_component import BaseComponent
    from core.llm_engine import call_llm


class IntelligentComponentDiscovery:
    """
    LLM驱动的量子组件智能发现引擎
    
    核心功能:
    - 自动扫描和发现可用组件
    - LLM理解组件功能描述
    - 根据量子问题意图智能选择相关组件
    - 零配置支持新组件
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self._component_cache: Dict[str, Type[BaseComponent]] = {}
        self._scan_components()
    
    def _scan_components(self):
        """
        扫描并缓存所有可用组件
        自动发现components目录下的所有组件类
        """
        # 获取components目录路径
        current_dir = Path(__file__).parent.parent
        components_dir = current_dir / "components"
        
        if not components_dir.exists():
            return
        
        # 扫描所有Python模块
        for root, dirs, files in os.walk(components_dir):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    self._load_components_from_file(Path(root) / file)
    
    def _load_components_from_file(self, file_path: Path):
        """从单个文件中加载组件"""
        try:
            # 构建模块路径
            relative_path = file_path.relative_to(Path(__file__).parent.parent)
            module_path = str(relative_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_path, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找BaseComponent子类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseComponent) and 
                        obj != BaseComponent and 
                        hasattr(obj, 'description')):
                        self._component_cache[name] = obj
                        
        except Exception as e:
            # 静默处理导入错误，继续处理其他组件
            pass
    
    def discover_relevant_components(self, intent: QuantumIntent) -> List[str]:
        """
        根据量子问题意图发现相关组件
        
        Args:
            intent: 量子问题意图对象
            
        Returns:
            相关组件名称列表（按重要性排序）
        """
        # 获取所有可用组件描述
        available_components = self._get_component_descriptions()
        
        if not available_components:
            # 如果没有可用组件，返回空列表
            return []
        
        # 构建LLM分析prompt
        prompt = self._build_discovery_prompt(intent, available_components)
        
        # LLM分析
        try:
            response = call_llm(prompt, model=self.model)
            component_names = self._parse_llm_response(response)
            return component_names
            
        except Exception as e:
            # LLM失败时的fallback策略
            return self._fallback_component_selection(intent)
    
    def _get_component_descriptions(self) -> Dict[str, str]:
        """获取所有组件的描述信息"""
        descriptions = {}
        
        for name, component_class in self._component_cache.items():
            try:
                # 获取组件描述
                if hasattr(component_class, 'description'):
                    descriptions[name] = component_class.description
                else:
                    descriptions[name] = f"Quantum component: {name}"
            except Exception:
                descriptions[name] = f"Quantum component: {name}"
        
        return descriptions
    
    def _build_discovery_prompt(self, intent: QuantumIntent, components: Dict[str, str]) -> str:
        """构建组件发现的LLM prompt"""
        return f"""
Analyze this quantum computing problem and select the most relevant components:

Problem Analysis:
- Problem Type: {intent.problem_type}
- Algorithm: {intent.algorithm}
- Parameters: {intent.parameters}
- Requirements: {intent.requirements}

Available Components:
{self._format_component_list(components)}

Task: Select the components needed for this quantum problem.

Consider:
1. Quantum algorithm workflow (Model → Hamiltonian → Circuit → Optimization)
2. Problem-specific requirements (TFIM, QAOA, Grover, etc.)
3. Component dependencies and logical flow
4. Essential vs optional components

Return ONLY a JSON list of component names in logical execution order:
["ComponentName1", "ComponentName2", "ComponentName3"]

Important:
- Include only truly necessary components
- Order by logical execution sequence  
- Use exact component names from the available list
- Maximum 8 components to avoid complexity

JSON:"""
    
    def _format_component_list(self, components: Dict[str, str]) -> str:
        """格式化组件列表供LLM分析"""
        formatted = []
        for name, description in components.items():
            formatted.append(f"- {name}: {description}")
        return "\n".join(formatted)
    
    def _parse_llm_response(self, response: str) -> List[str]:
        """解析LLM的组件选择响应"""
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
            component_names = json.loads(response)
            
            # 验证返回的是列表
            if not isinstance(component_names, list):
                raise ValueError("Response is not a list")
            
            # 验证组件名称有效性
            valid_components = []
            for name in component_names:
                if isinstance(name, str) and name in self._component_cache:
                    valid_components.append(name)
            
            return valid_components
            
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse LLM component selection: {e}")
    
    def _fallback_component_selection(self, intent: QuantumIntent) -> List[str]:
        """
        LLM失败时的后备组件选择策略
        基于问题类型的简单规则匹配
        """
        problem_type = intent.problem_type.upper()
        algorithm = intent.algorithm.upper()
        
        # 基本的规则匹配
        if "TFIM" in problem_type:
            return [name for name in self._component_cache.keys() 
                   if "TFIM" in name or "VQE" in name]
        elif "QAOA" in problem_type or "QAOA" in algorithm:
            return [name for name in self._component_cache.keys() 
                   if "QAOA" in name]
        elif "GROVER" in problem_type or "GROVER" in algorithm:
            return [name for name in self._component_cache.keys() 
                   if "GROVER" in name or "Grover" in name]
        else:
            # 返回通用组件
            return list(self._component_cache.keys())[:5]  # 限制数量
    
    def get_component_class(self, component_name: str) -> Type[BaseComponent]:
        """
        根据组件名称获取组件类
        
        Args:
            component_name: 组件名称
            
        Returns:
            组件类
            
        Raises:
            KeyError: 如果组件不存在
        """
        if component_name not in self._component_cache:
            raise KeyError(f"Component '{component_name}' not found")
        
        return self._component_cache[component_name]
    
    def get_available_components(self) -> Dict[str, str]:
        """获取所有可用组件及其描述"""
        return self._get_component_descriptions()
    
    def refresh_components(self):
        """重新扫描和缓存组件"""
        self._component_cache.clear()
        self._scan_components()
