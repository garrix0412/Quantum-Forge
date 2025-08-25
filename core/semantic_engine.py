"""
Semantic Engine - QuantumForge V5 语义理解引擎

LLM驱动的量子问题语义理解引擎。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 1.2 设计。
"""

import json
from typing import Dict, Any, List, Optional

# 导入LLM调用函数
try:
    from .llm_engine import call_llm
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from llm_engine import call_llm


class QuantumIntent:
    """量子问题意图数据结构"""
    
    def __init__(self, problem_type: str, algorithm: str, parameters: Dict[str, Any], 
                 requirements: List[str]):
        self.problem_type = problem_type    # 量子问题类型
        self.algorithm = algorithm      # 需要的算法
        self.parameters = parameters    # 提取的参数
        self.requirements = requirements    # 用户需求
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "problem_type": self.problem_type,
            "algorithm": self.algorithm,
            "parameters": self.parameters,
            "requirements": self.requirements
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumIntent':
        """从字典创建实例"""
        return cls(
            problem_type=data.get("problem_type", ""),
            algorithm=data.get("algorithm", ""),
            parameters=data.get("parameters", {}),
            requirements=data.get("requirements", [])
        )


class QuantumSemanticEngine:
    """
    LLM驱动的量子问题语义理解引擎
    
    职责:
    - 理解用户的量子计算查询
    - 提取问题类型、算法、参数等关键信息
    - 返回结构化的量子意图对象
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
    
    def understand_quantum_query(self, query: str) -> QuantumIntent:
        """
        LLM理解量子问题的核心方法，支持智能补足
        
        Args:
            query: 用户的量子计算查询
            
        Returns:
            结构化的量子意图对象
            
        Raises:
            Exception: 如果两次LLM调用都完全失败
        """
        prompt = self._build_understanding_prompt(query)
        
        # 第一次尝试
        try:
            response = call_llm(prompt, model=self.model)
            intent_data = self._parse_llm_response(response)
            
            # 检查信息完整性，不完整则智能补足
            if self._is_incomplete(intent_data):
                intent_data = self._apply_defaults(intent_data)
                
            return QuantumIntent.from_dict(intent_data)
            
        except Exception as e:
            # 第二次尝试
            try:
                response = call_llm(prompt, model=self.model)
                intent_data = self._parse_llm_response(response)
                
                # 第二次尝试后仍可能不完整，智能补足
                if self._is_incomplete(intent_data):
                    intent_data = self._apply_defaults(intent_data)
                    
                return QuantumIntent.from_dict(intent_data)
                
            except Exception as retry_error:
                # 两次都失败，返回完全默认配置
                return self._get_default_intent()
    
    def _build_understanding_prompt(self, query: str) -> str:
        """构建语义理解的prompt"""
        return f"""
Analyze this quantum computing query and extract structured information: {query}

Extract the following information:
- Problem type: What quantum problem is this? (TFIM, QAOA, MaxCut, Graph Optimization, Grover, QML, Machine Learning, Binary Classification, HHL, Linear System, etc.)
- Algorithm: What quantum algorithm is needed?
- Parameters: What specific values are mentioned?
- Requirements: What does the user want as output?

Return ONLY a JSON object with these fields:
{{
    "problem_type": "detected_problem_type",
    "algorithm": "needed_algorithm", 
    "parameters": {{"extracted_parameters": "values"}},
    "requirements": ["what_user_wants"]
}}

Important:
- Extract EXACT parameter values from the query
- If no specific algorithm mentioned, infer the most appropriate one
- Always include "complete_python_file" in requirements
- Use standard quantum physics notation when applicable

JSON:"""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM的JSON响应"""
        # 清理响应，提取JSON部分
        response = response.strip()
        
        # 如果包含代码块标记，提取其中的JSON
        if '```' in response:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                response = response[start:end]
        
        # 解析JSON
        try:
            intent_data = json.loads(response)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM JSON response: {e}")
        
        # 验证必需字段存在
        required_fields = ["problem_type", "algorithm", "parameters", "requirements"]
        missing_fields = [field for field in required_fields if field not in intent_data]
        if missing_fields:
            raise Exception(f"Missing required fields in LLM response: {missing_fields}")
        
        return intent_data
    
    def _is_incomplete(self, intent_data: Dict[str, Any]) -> bool:
        """
        检查提取的信息是否不完整或无效
        
        Args:
            intent_data: LLM提取的意图数据
            
        Returns:
            True if 关键信息缺失或无效, False if 信息完整
        """
        # 无效的问题类型（LLM返回的无意义值）
        invalid_problem_types = ["unspecified", "unknown", "unclear", "not_specified", 
                                "general", "generic", "undefined", "not_clear",
                                "quantum_circuit_creation", "quantum_code", "general_quantum"]
        
        # 无效的算法
        invalid_algorithms = ["unspecified", "unknown", "unclear", "not_specified",
                             "general", "generic", "undefined", "not_clear", 
                             "custom_circuit_design", "general_algorithm", "quantum_algorithm"]
        
        problem_type = intent_data.get("problem_type", "").strip().lower()
        algorithm = intent_data.get("algorithm", "").strip().lower()
        
        # 检查关键字段是否为空或无效
        return (
            not intent_data.get("problem_type") or 
            problem_type == "" or
            problem_type in invalid_problem_types or
            not intent_data.get("algorithm") or
            algorithm == "" or  
            algorithm in invalid_algorithms
        )
    
    def _apply_defaults(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        智能补足缺失信息，保留已提取的信息
        只补足问题类型和算法，参数由后续组件处理
        
        Args:
            intent_data: 部分提取的意图数据
            
        Returns:
            补足后的完整意图数据
        """
        # 无效值检测
        invalid_values = ["unspecified", "unknown", "unclear", "not_specified",
                         "general", "generic", "undefined", "not_clear", "",
                         "quantum_circuit_creation", "quantum_code", "general_quantum",
                         "custom_circuit_design", "general_algorithm", "quantum_algorithm"]
        
        # 1. 问题类型缺失或无效 -> 默认TFIM
        problem_type = intent_data.get("problem_type", "").strip().lower()
        if not problem_type or problem_type in invalid_values:
            intent_data["problem_type"] = "TFIM"
            intent_data["problem_type_is_default"] = True
        
        # 2. 算法缺失或无效 -> 根据问题类型智能推断
        algorithm = intent_data.get("algorithm", "").strip().lower()
        if not algorithm or algorithm in invalid_values:
            problem_type = intent_data.get("problem_type", "TFIM")
            if problem_type.upper() == "TFIM":
                intent_data["algorithm"] = "VQE"
            elif problem_type.upper() == "QAOA":
                intent_data["algorithm"] = "QAOA"
            elif problem_type.upper() == "GROVER":
                intent_data["algorithm"] = "Grover"
            elif problem_type.upper() == "HHL" or "LINEAR SYSTEM" in problem_type.upper():
                intent_data["algorithm"] = "HHL"
            else:
                intent_data["algorithm"] = "VQE"  # 通用默认
            intent_data["algorithm_is_default"] = True
        
        # 3. 参数处理 -> 保留用户提取的参数，空值也OK（组件会处理默认参数）
        if not intent_data.get("parameters"):
            intent_data["parameters"] = {}
            # 不标记为默认值，因为空参数是正常的
        
        # 4. 需求缺失 -> 标准需求
        if not intent_data.get("requirements") or not intent_data["requirements"]:
            intent_data["requirements"] = ["complete_python_file"]
            intent_data["requirements_is_default"] = True
        
        return intent_data
    
    def _get_default_intent(self) -> QuantumIntent:
        """
        LLM完全失败时的默认配置
        
        Returns:
            完全默认的量子意图对象
        """
        default_data = {
            "problem_type": "TFIM",
            "problem_type_is_default": True,
            "algorithm": "VQE", 
            "algorithm_is_default": True,
            "parameters": {},
            "parameters_is_default": True,
            "requirements": ["complete_python_file"],
            "requirements_is_default": True
        }
        
        return QuantumIntent.from_dict(default_data)
