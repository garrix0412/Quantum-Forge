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
        """分析组件的参数需求 - 混合策略"""
        component_info = {
            "name": component_name,
            "description": component.get_description(),
            "common_parameters": self._get_component_parameters_hybrid(component_name, component.get_description())
        }
        
        return component_info
    
    def _get_component_parameters_hybrid(self, component_name: str, description: str) -> List[str]:
        """混合参数推断策略: LLM智能推断 + 硬编码回退"""
        
        # 1. 先尝试LLM智能推断
        try:
            llm_params = self._get_smart_parameters_by_llm(component_name, description)
            if llm_params and len(llm_params) > 0:
                print(f"  🧠 LLM inferred parameters for {component_name}: {llm_params}")
                return llm_params
        except Exception as e:
            print(f"  ⚠️ LLM parameter inference failed for {component_name}: {e}")
        
        # 2. 回退到现有硬编码规则
        fallback_params = self._get_common_parameters_by_type(component_name)
        print(f"  🔄 Using fallback parameters for {component_name}: {fallback_params}")
        return fallback_params
    
    def _get_smart_parameters_by_llm(self, component_name: str, description: str) -> List[str]:
        """使用LLM智能推断组件参数需求"""
        
        prompt = f"""
Analyze the quantum computing component and infer what parameters it likely needs:

Component Name: {component_name}
Component Description: {description}

Based on the component name and description, determine what input parameters this component would need from previous components in the quantum computing pipeline.

Common Parameter Categories:
1. **System Parameters**: num_qubits, system_size, qubit_count
2. **Problem Parameters**: parameters, config, problem_config, user_parameters  
3. **Quantum Objects**: hamiltonian, circuit, ansatz, operator
4. **Specific Info**: ansatz_info, circuit_info, graph_info, molecule_info
5. **Algorithm Config**: optimizer_type, backend_type, method_config
6. **Physical Properties**: coupling_strength, field_strength, J, h, edges

Guidelines:
- Focus on what THIS specific component needs as input
- Consider the quantum computing workflow: Model → Hamiltonian → Circuit → Optimization
- Look for key words in the description that indicate parameter needs
- Molecular components often need: ansatz_info, circuit_info, molecule_info  
- QAOA components often need: graph_info, problem_config
- VQE components often need: hamiltonian, ansatz_info, circuit_info
- Model generators typically need: num_qubits, parameters, config
- QML components often need: dataset_info, circuit_info, network_info, training_info

Return ONLY a JSON list of parameter names (max 6 parameters):
["param1", "param2", "param3"]

Important: Return realistic parameter names that would be passed between quantum computing components.

JSON:"""

        try:
            response = call_llm(prompt, model=self.model)
            
            # 清理响应
            response = response.strip()
            if '```' in response:
                start = response.find('[')
                end = response.rfind(']') + 1
                if start != -1 and end > start:
                    response = response[start:end]
            
            # 解析JSON
            params = json.loads(response)
            
            # 验证结果
            if isinstance(params, list) and len(params) > 0:
                # 确保所有参数都是字符串且合理
                valid_params = []
                for param in params[:6]:  # 最多6个参数
                    if isinstance(param, str) and len(param) > 0 and (('_' in param) or len(param) < 20):
                        valid_params.append(param)
                
                if valid_params:
                    return valid_params
            
            raise ValueError("Invalid parameter format from LLM")
            
        except Exception as e:
            # 记录但不显示详细错误，避免干扰用户
            print(f"    LLM parameter inference error: {str(e)[:50]}...")
            raise e
    
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
            if "GRAPH" in component_name_upper:
                return ["num_nodes", "graph_type", "edge_prob", "custom_edges", "compute_exact"]
            elif "HAMILTONIAN" in component_name_upper:
                return ["graph_info", "edge_list", "coupling_strength"]
            elif "CIRCUIT" in component_name_upper:
                return ["hamiltonian_info", "ansatz_type", "reps", "mixer_type"]
            elif "OPTIMIZER" in component_name_upper:
                return ["circuit_info", "hamiltonian_info", "optimizer_type", "n_restarts", "init_strategies", "maxiter"]
        
        # Grover相关组件
        elif "GROVER" in component_name_upper:
            if "ORACLE" in component_name_upper:
                return ["num_qubits", "target_states", "search_space"]
            elif "DIFFUSER" in component_name_upper:
                return ["num_qubits", "oracle_circuit"]
            elif "CIRCUIT" in component_name_upper:
                return ["oracle_circuit", "diffuser_circuit", "iterations"]
        
        # 分子组件 - 特殊处理
        elif "MOLECULAR" in component_name_upper:
            if "OPTIMIZER" in component_name_upper:
                return ["num_qubits", "parameters", "config", "ansatz_info", "circuit_info"]
            elif "CIRCUIT" in component_name_upper:
                return ["num_qubits", "hamiltonian", "ansatz_type", "parameters"]
            elif "HAMILTONIAN" in component_name_upper:
                return ["num_qubits", "parameters", "config", "molecule_info"]
            elif "MODEL" in component_name_upper:
                return ["num_qubits", "parameters", "config"]
        
        # VQE相关组件
        elif "VQE" in component_name_upper:
            if "CIRCUIT" in component_name_upper:
                return ["num_qubits", "hamiltonian", "ansatz_type", "parameters"]
            elif "OPTIMIZER" in component_name_upper:
                return ["circuit", "hamiltonian", "initial_params", "optimizer_type"]
        
        # HHL相关组件 - 6个组件的参数映射
        elif "HHL" in component_name_upper:
            if "PREPROCESSOR" in component_name_upper:
                return ["matrix_A", "vector_b", "precision_mode", "A", "b", "qpe_qubits", "C_factor"]
            elif "STATE" in component_name_upper and ("PREP" in component_name_upper or "PREPARATION" in component_name_upper):
                return ["hermitian_system", "processed_b", "n_qubits", "hermitian_A"]
            elif "QPE" in component_name_upper and "INVERSE" not in component_name_upper:
                return ["hermitian_system", "qpe_qubits", "eigenvalues", "time_evolution_t0", "hermitian_A"]
            elif "ROTATION" in component_name_upper or "CONTROLLED" in component_name_upper:
                return ["qpe_qubits", "C_factor", "eigenvalues", "hermitian_system"]
            elif "INVERSE" in component_name_upper and "QPE" in component_name_upper:
                return ["qpe_qubits", "auxiliary_qubits", "hermitian_system", "rotation_info", "eigenvalues"]
            elif "MEASUREMENT" in component_name_upper or "EXECUTOR" in component_name_upper:
                return ["hermitian_system", "auxiliary_qubits", "measurement_preparation", "C_factor", "hermitian_A"]
        
        # QML相关组件
        elif "QML" in component_name_upper:
            if "DATASET" in component_name_upper:
                return ["dataset", "target_classes", "train_samples_per_class", "test_samples_per_class"]
            elif "CIRCUIT" in component_name_upper:
                return ["num_qubits", "feature_map_type", "ansatz_type", "dataset_info"]
            elif "NETWORK" in component_name_upper or "HYBRID" in component_name_upper:
                return ["dataset_info", "circuit_info", "input_channels", "classical_layers"]
            elif "TRAINING" in component_name_upper:
                return ["dataset_info", "network_info", "optimizer", "learning_rate", "epochs"]
            elif "EVALUATOR" in component_name_upper:
                return ["dataset_info", "training_info", "metrics", "include_confusion_matrix"]
        
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
7. **QAOA Layers**: reps, repetitions, layers, num_layers, p → QAOA depth parameter
8. **Optimizers**: optimizer, optimizer_type, optim → classical optimizer names (COBYLA, SPSA, L_BFGS_B, SLSQP)
9. **Ansatz Types**: ansatz, ansatz_type, mixer → quantum circuit structure (standard, xy_mixer, multi_angle)
10. **HHL Matrix Parameters**: matrix_A, A, coefficient_matrix → coefficient matrix for linear system
11. **HHL Vector Parameters**: vector_b, b, right_hand_side → right-hand side vector for linear system
12. **HHL Precision Parameters**: qpe_qubits, precision_mode → quantum phase estimation precision settings
13. **HHL Scaling Parameters**: C_factor → eigenvalue inversion scaling factor for HHL algorithm
14. **HHL System Parameters**: hermitian_system, hermitian_A, processed_b → processed Hermitian system data
15. **HHL Eigenvalue Parameters**: eigenvalues, time_evolution_t0 → quantum phase estimation eigenvalue data
16. **HHL Execution Parameters**: shots, backend_type, optimization_level → quantum simulation execution settings

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

    def match_parameters_for_component(self, component_name: str, intent) -> Dict[str, Any]:
        """
        为指定组件匹配参数
        
        Args:
            component_name: 组件名称
            intent: 量子意图对象
            
        Returns:
            匹配的参数字典
        """
        # 从intent中获取参数
        base_params = intent.parameters.copy()
        
        # 根据组件名称添加默认参数
        component_params = self._get_common_parameters_by_type(component_name)
        
        # 为特定组件添加默认值 - 支持6个HHL组件
        if "HHL" in component_name.upper():
            if "Preprocessor" in component_name:
                base_params.setdefault("precision_mode", "high")
                base_params.setdefault("matrix_A", [[4, -1], [-1, 3]])
                base_params.setdefault("vector_b", [1, 0])
            elif "State" in component_name and ("Prep" in component_name or "Preparation" in component_name):
                base_params.setdefault("n_qubits", 2)
            elif "QPE" in component_name and "Inverse" not in component_name:
                base_params.setdefault("qpe_qubits", 4)
                base_params.setdefault("time_evolution_t0", 1.0)
            elif "Rotation" in component_name or "Controlled" in component_name:
                base_params.setdefault("C_factor", 1.0)
            elif "Inverse" in component_name and "QPE" in component_name:
                base_params.setdefault("qpe_qubits", 4)
                base_params.setdefault("time_evolution_t0", 1.0)
            elif "Measurement" in component_name or "Executor" in component_name:
                base_params.setdefault("shots", 1024)
                base_params.setdefault("backend_type", "AerSimulator")
                base_params.setdefault("optimization_level", 2)
        
        return base_params


