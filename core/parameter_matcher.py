"""
Parameter Matcher - QuantumForge V5 智能参数匹配引擎

LLM驱动的量子组件参数智能匹配系统。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 2.3 设计。
"""

import json
from typing import Dict, Any, List, Optional, Union

# 导入相关类型
try:
    from .execution_memory import ExecutionMemory
    from .llm_engine import call_llm
    from ..components.base_component import BaseComponent
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.execution_memory import ExecutionMemory
    from core.llm_engine import call_llm
    from components.base_component import BaseComponent


class LLMParameterMatcher:
    """
    LLM驱动的智能参数匹配引擎
    
    核心功能:
    - 理解量子物理参数语义
    - 智能匹配不同组件的参数需求
    - 自动解决参数名称不匹配问题
    - 提供参数类型转换和验证
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
    
    def resolve_parameters(self, memory: ExecutionMemory, target_component: BaseComponent,
                          component_name: str) -> Dict[str, Any]:
        """
        为目标组件智能解决参数匹配问题
        
        Args:
            memory: 执行记忆，包含所有历史数据
            target_component: 目标组件实例  
            component_name: 目标组件名称
            
        Returns:
            为目标组件匹配的参数字典
        """
        # 1. 获取所有可用数据
        available_data = memory.get_all_outputs()
        
        # 2. 分析目标组件的参数需求
        component_info = self._analyze_component_requirements(target_component, component_name)
        
        # 3. 构建LLM参数匹配prompt
        prompt = self._build_matching_prompt(available_data, component_info)
        
        # 4. LLM智能匹配参数
        try:
            response = call_llm(prompt, model=self.model)
            matched_params = self._parse_parameter_response(response)
            
            # 5. 验证和后处理参数
            validated_params = self._validate_and_process_parameters(matched_params, component_info)
            
            return validated_params
            
        except Exception as e:
            # LLM失败时的fallback策略
            return self._fallback_parameter_matching(memory, component_name)
    
    def _analyze_component_requirements(self, component: BaseComponent, component_name: str) -> Dict[str, Any]:
        """分析组件的参数需求"""
        component_info = {
            "name": component_name,
            "description": component.get_description(),
            "common_parameters": self._get_common_parameters_by_type(component_name)
        }
        
        return component_info
    
    def _get_common_parameters_by_type(self, component_name: str) -> List[str]:
        """根据组件类型获取常见参数"""
        component_name_upper = component_name.upper()
        
        # TFIM相关组件
        if "TFIM" in component_name_upper:
            if "MODEL" in component_name_upper or "GENERATOR" in component_name_upper:
                return ["num_qubits", "J", "h", "coupling_strength", "field_strength"]
            elif "HAMILTONIAN" in component_name_upper:
                return ["num_qubits", "J", "h", "coupling_J", "field_h", "parameters"]
            elif "CIRCUIT" in component_name_upper or "VQE" in component_name_upper:
                return ["num_qubits", "hamiltonian", "circuit_depth", "parameters"]
        
        # QAOA相关组件
        elif "QAOA" in component_name_upper:
            if "GRAPH" in component_name_upper or "PROBLEM" in component_name_upper:
                return ["num_qubits", "edges", "graph_config", "problem_type"]
            elif "HAMILTONIAN" in component_name_upper:
                return ["graph_config", "cost_function", "mixer_type"]
            elif "CIRCUIT" in component_name_upper:
                return ["cost_hamiltonian", "mixer_hamiltonian", "layers", "parameters"]
        
        # Grover相关组件
        elif "GROVER" in component_name_upper:
            if "ORACLE" in component_name_upper:
                return ["num_qubits", "target_states", "search_space"]
            elif "DIFFUSER" in component_name_upper:
                return ["num_qubits", "oracle_circuit"]
            elif "CIRCUIT" in component_name_upper:
                return ["oracle_circuit", "diffuser_circuit", "iterations"]
        
        # VQE相关组件
        elif "VQE" in component_name_upper:
            if "CIRCUIT" in component_name_upper:
                return ["num_qubits", "hamiltonian", "ansatz_type", "parameters"]
            elif "OPTIMIZER" in component_name_upper:
                return ["circuit", "hamiltonian", "initial_params", "optimizer_type"]
        
        # 通用参数
        return ["num_qubits", "parameters", "config"]
    
    def _build_matching_prompt(self, available_data: Dict[str, Any], component_info: Dict[str, Any]) -> str:
        """构建参数匹配的LLM prompt"""
        
        # 格式化可用数据
        formatted_data = self._format_available_data(available_data)
        
        return f"""
Quantum Parameter Matching Task:

Target Component: {component_info['name']}
Component Description: {component_info['description']}
Expected Parameters: {component_info['common_parameters']}

Available Data from Previous Components:
{formatted_data}

Task: Match parameters for the target component using quantum physics semantics.

Quantum Parameter Mapping Rules:
1. **Coupling Parameters**: J, coupling_J, coupling_strength → same physical quantity
2. **Field Parameters**: h, field_h, field_strength → same physical quantity  
3. **System Size**: num_qubits, qubits, n_qubits → same physical quantity
4. **Hamiltonians**: hamiltonian, cost_hamiltonian, mixer_hamiltonian → quantum operators
5. **Circuits**: circuit, oracle_circuit, vqe_circuit → quantum circuits
6. **Optimization**: parameters, params, initial_params → variational parameters

Matching Strategy:
- Use EXACT values when available in previous outputs
- Map semantically equivalent parameter names
- Include parameters needed by target component
- Preserve original data types and structures
- Add reasonable defaults ONLY if no data available

Return ONLY a JSON object with matched parameters:
{{
    "parameter_name": "parameter_value",
    "num_qubits": 4,
    "J": 1.5
}}

Important:
- Use actual values from available data, not placeholders
- Map parameter names to what target component expects
- Ensure quantum physics semantic consistency
- Return empty object {{}} if no relevant data available

JSON:"""
    
    def _format_available_data(self, available_data: Dict[str, Any]) -> str:
        """格式化可用数据供LLM分析"""
        formatted_parts = []
        
        # 原始查询和意图
        if "original_query" in available_data:
            formatted_parts.append(f"Original Query: {available_data['original_query']}")
        
        if "quantum_intent" in available_data and available_data["quantum_intent"]:
            intent = available_data["quantum_intent"]
            formatted_parts.append(f"Problem Type: {intent.get('problem_type', 'Unknown')}")
            formatted_parts.append(f"Algorithm: {intent.get('algorithm', 'Unknown')}")
            if intent.get("parameters"):
                formatted_parts.append(f"User Parameters: {intent['parameters']}")
        
        # 组件输出
        if "component_outputs" in available_data and available_data["component_outputs"]:
            formatted_parts.append("\nComponent Outputs:")
            for comp_name, output in available_data["component_outputs"].items():
                formatted_parts.append(f"  {comp_name}:")
                for key, value in output.items():
                    if key != "notes":  # 跳过notes字段
                        formatted_parts.append(f"    {key}: {value}")
        
        # 当前状态
        if "current_state" in available_data and available_data["current_state"]:
            state = available_data["current_state"]
            if "latest_parameters" in state:
                formatted_parts.append(f"\nLatest Parameters: {state['latest_parameters']}")
        
        return "\n".join(formatted_parts)
    
    def _parse_parameter_response(self, response: str) -> Dict[str, Any]:
        """解析LLM的参数匹配响应"""
        # 清理响应，提取JSON部分
        response = response.strip()
        
        # 如果包含代码块标记，提取其中的JSON
        if '```' in response:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                response = response[start:end]
        
        try:
            # 解析JSON
            parameters = json.loads(response)
            
            # 验证返回的是字典
            if not isinstance(parameters, dict):
                raise ValueError("Response is not a dictionary")
            
            return parameters
            
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse LLM parameter response: {e}")
    
    def _validate_and_process_parameters(self, params: Dict[str, Any], 
                                       component_info: Dict[str, Any]) -> Dict[str, Any]:
        """验证和后处理匹配的参数"""
        processed_params = {}
        
        for key, value in params.items():
            # 基本数据类型验证和转换
            processed_value = self._convert_parameter_value(key, value)
            processed_params[key] = processed_value
        
        return processed_params
    
    def _convert_parameter_value(self, param_name: str, value: Any) -> Any:
        """参数值类型转换"""
        # 如果是字符串形式的数字，尝试转换
        if isinstance(value, str):
            # 尝试转换为int
            try:
                if '.' not in value:
                    return int(value)
            except ValueError:
                pass
            
            # 尝试转换为float
            try:
                return float(value)
            except ValueError:
                pass
        
        return value
    
    def _fallback_parameter_matching(self, memory: ExecutionMemory, component_name: str) -> Dict[str, Any]:
        """
        LLM失败时的后备参数匹配策略
        基于简单规则和最新参数
        """
        # 获取最新参数
        latest_params = memory.get_latest_parameters()
        
        # 获取用户原始参数
        user_params = {}
        if memory.quantum_intent:
            user_params = memory.quantum_intent.get("parameters", {})
        
        # 合并参数（最新参数优先）
        fallback_params = {**user_params, **latest_params}
        
        # 根据组件类型过滤相关参数
        relevant_params = self._filter_relevant_parameters(fallback_params, component_name)
        
        return relevant_params
    
    def _filter_relevant_parameters(self, params: Dict[str, Any], component_name: str) -> Dict[str, Any]:
        """根据组件类型过滤相关参数"""
        component_name_upper = component_name.upper()
        filtered_params = {}
        
        # 通用参数
        common_keys = ["num_qubits", "qubits", "n_qubits"]
        for key in common_keys:
            if key in params:
                filtered_params["num_qubits"] = params[key]
                break
        
        # TFIM特定参数
        if "TFIM" in component_name_upper:
            tfim_keys = ["J", "coupling_J", "coupling_strength"]
            for key in tfim_keys:
                if key in params:
                    filtered_params["J"] = params[key]
                    break
            
            field_keys = ["h", "field_h", "field_strength"] 
            for key in field_keys:
                if key in params:
                    filtered_params["h"] = params[key]
                    break
        
        # 保留其他相关参数
        for key, value in params.items():
            if key not in filtered_params and key not in ["notes", "timestamp"]:
                filtered_params[key] = value
        
        return filtered_params
    
    def get_parameter_mapping_info(self, memory: ExecutionMemory) -> Dict[str, Any]:
        """
        获取参数映射信息，用于调试和验证
        
        Returns:
            参数映射的详细信息
        """
        available_data = memory.get_all_outputs()
        
        mapping_info = {
            "available_parameters": {},
            "parameter_sources": {},
            "total_components": 0
        }
        
        # 分析可用参数
        if "component_outputs" in available_data:
            mapping_info["total_components"] = len(available_data["component_outputs"])
            
            for comp_name, output in available_data["component_outputs"].items():
                for key, value in output.items():
                    if key not in ["notes", "timestamp"]:
                        if key not in mapping_info["available_parameters"]:
                            mapping_info["available_parameters"][key] = []
                            mapping_info["parameter_sources"][key] = []
                        
                        mapping_info["available_parameters"][key].append(value)
                        mapping_info["parameter_sources"][key].append(comp_name)
        
        return mapping_info


