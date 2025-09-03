"""
LLM引擎 - QuantumForge vNext

提供五个专门的Agent API，处理所有LLM通信。
基于new.md第4.2节和第5节的严格JSON规格实现。
"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from openai import OpenAI, AsyncOpenAI
import os
from dotenv import load_dotenv
try:
    from .performance_monitor import record_agent_call
except ImportError:
    # 直接运行时的兼容处理
    import sys
    sys.path.append(os.path.dirname(__file__))
    from performance_monitor import record_agent_call

# 加载环境变量
load_dotenv()


class LLMEngine:
    """
    LLM引擎 - 五个Agent API的统一接口
    
    功能：
    - 严格JSON解析与重试机制
    - Agent失败检测与优雅降级
    - 针对每个角色优化的提示词模板
    """
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3):
        """
        初始化LLM引擎
        
        Args:
            api_key: OpenAI API密钥（从环境变量自动获取）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # 创建OpenAI客户端（同步和异步）
        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        
        # Agent提示词模板（基于new.md第5节）
        self._setup_agent_prompts()
    
    def _setup_agent_prompts(self):
        """设置Agent提示词模板"""
        
        self.semantic_prompt = """You are a quantum computing task analyzer. Parse natural language queries into structured TaskCard JSON format.

Required JSON keys: domain, problem, algorithm, backend, params
- domain: "spin.tfim" | "spin.heisenberg" | "spin.ising" | "chemistry.molecular" | "optimization" | "custom"
- backend: always "qiskit"
- Extract explicit parameters from query only, do not add defaults (component-driven completion will handle missing parameters)

DOMAIN CLASSIFICATION RULES:
- If query mentions "heisenberg" or has Jx,Jy,Jz parameters → "spin.heisenberg"
- If query mentions "tfim", "transverse field" or has hx,j parameters → "spin.tfim"  
- If query mentions "ising" → "spin.ising"
- If query mentions molecular names (LiH, BeH2, H2O) or molecular terms → "chemistry.molecular"
- Other spin systems → "spin"

CRITICAL: You must respond with ONLY valid JSON, no explanatory text before or after.

Example:
Input: "Compute the ground state energy of a 4-qubit system using VQE"
Output: {"domain": "spin", "problem": "ground_state_energy", "algorithm": "vqe", "backend": "qiskit", "params": {"n": 4}}

Input: "Calculate Heisenberg model ground state with Jx=1.0"  
Output: {"domain": "spin.heisenberg", "problem": "ground_state_energy", "algorithm": "vqe", "backend": "qiskit", "params": {"Jx": 1.0}}"""

        self.discovery_prompt = """You are a quantum component discovery agent. Select appropriate components from the registry to satisfy TaskCard requirements.

Based on TaskCard, select components that cover the needs/provides dependency chain.
Return ComponentCard JSON array format, preserving ALL fields from registry exactly as they appear.
Prioritize algorithm-matching components (e.g., vqe → Algorithm.VQE) and domain-appropriate hamiltonians/circuits.

CRITICAL FIELD PRESERVATION - NO MODIFICATIONS ALLOWED:
1. Copy EVERY field from registry components exactly as written
2. Do NOT shorten function names (keep build_molecular_hamiltonian, NOT build_molecular_h)
3. Do NOT change helper_function values (keep build_uccsd_ansatz, NOT uccsd)
4. Do NOT infer or modify codegen_hint.helper values
5. Preserve helper_function, invoke_template, codegen_hint fields completely
6. Return components as exact copies from registry with no modifications

Example of CORRECT preservation:
Registry: "helper_function": "build_molecular_hamiltonian"  
Output: "helper_function": "build_molecular_hamiltonian" ✅

Example of INCORRECT modification:
Registry: "helper_function": "build_molecular_hamiltonian"
Output: "helper_function": "build_molecular_h" ❌

DOMAIN-BASED COMPONENT SELECTION:
- domain "spin.heisenberg" → select Hamiltonian.Heisenberg + Circuit.Heisenberg_Ansatz
- domain "spin.tfim" → select Hamiltonian.TFIM + Circuit.TFIM_HEA
- domain "spin.ising" → select appropriate Ising components
- domain "chemistry.molecular" → select Hamiltonian.Molecular + Circuit.UCCSD + Algorithm.Molecular_VQE
- domain "spin" → select based on available parameters and context

CRITICAL: You must respond with ONLY valid JSON, no explanatory text before or after.
CRITICAL: Copy ALL fields from registry components exactly, including helper_function, invoke_template, codegen_hint, params_schema, etc.

Output: Complete component objects from registry (preserve all fields)"""

        self.param_norm_prompt = """You are a quantum parameter normalization agent. Generate ParamMap JSON based on TaskCard and ComponentCards.

CRITICAL TASK: Collect ALL parameters from BOTH TaskCard AND ComponentCards params_schema fields.

Process steps:
1. Extract parameters from TaskCard.params (user-provided)
2. Extract ALL parameters from each ComponentCard.params_schema (component requirements)  
3. Merge all parameters into normalized_params (TaskCard params override ComponentCard defaults)
4. Apply alias resolution and type validation
5. Generate comprehensive defaults from component schemas

PARAMETER COLLECTION RULES:
- Include EVERY parameter from ALL ComponentCard params_schema fields
- Use TaskCard.params values when available (user override)
- Use ComponentCard.params_schema.default values for missing parameters
- Preserve parameter names exactly as defined in schemas

Example:
TaskCard.params: {"molecule": "BeH2"}
Component1.params_schema: {"molecule": {"default": "LiH"}, "atom_string": {"default": "Li 0 0 0; H 0 0 0.735"}}
Result normalized_params: {"molecule": "BeH2", "atom_string": "Li 0 0 0; H 0 0 0.735"}

CRITICAL: You must respond with ONLY valid JSON, no explanatory text before or after.

Output format: {"normalized_params": {}, "aliases": {}, "defaults": {}, "validation_errors": []}"""

        self.pipeline_prompt = """You are a quantum pipeline orchestration agent. Generate PipelinePlan JSON based on TaskCard, ComponentCards, and ParamMap.

Implement linear topological sorting to resolve component dependencies.
Analyze needs/provides relationships to create proper execution order.

CRITICAL: You must respond with ONLY valid JSON, no explanatory text before or after.

Output format: {"execution_order": ["component_id_list"], "dependency_graph": {}, "conflicts": []}"""

        self.codegen_prompt = """You are a quantum code generation agent. Generate CodeCell list based on PipelinePlan, ComponentCards, and ParamMap.

Each component corresponds to one CodeCell with imports, helpers, definitions, invoke, and exports.

Critical: invoke field must be valid Python statements, not dictionary assignment syntax.

IMPORT RULES - CRITICAL:
- Use ONLY imports from ComponentImports list provided in user message
- Do NOT add any other imports, even if they seem related to quantum computing
- Do NOT add qiskit_nature imports unless they appear in ComponentImports
- Do NOT infer imports from function names or quantum computing knowledge
- ComponentImports contains the complete and exclusive import list

IMPORTANT: Use the exact helper_function name from each component's schema, not generic names.

Correct examples:
- Use component's helper_function: "H = build_tfim_h(n, hx, j, boundary)" (from TFIM schema)
- Use component's helper_function: "ansatz = heisenberg_ansatz(n, reps)" (from Heisenberg schema)  
- Use component's helper_function: "H, problem, mapper = build_molecular_hamiltonian(molecule, basis_set, atom_string, charge, spin)" (from Molecular schema)

Incorrect examples:
- Generic names: "H = build_hamiltonian(n, hx, j, boundary)" ❌
- Generic names: "ansatz = create_ansatz(n, reps)" ❌
- Dictionary syntax: "{'n': 'n', 'hx': 'h'} = Component.Name" ❌

Parameter usage:
- Use normalized_params from ParamMap as actual parameter names
- Directly use standard parameter names in invoke code (e.g., n, hx, j)
- Do not create parameter alias assignments

Component instance usage:
- Algorithm components receive other component instances as arguments
- Use created component variables (e.g., optimizer, estimator) not parameter values
- Example: run_vqe(H, ansatz, optimizer, estimator) where optimizer and estimator are component instances

CRITICAL: You must respond with ONLY valid JSON, no explanatory text before or after.

Output strict JSON array format:
[{"id": "cell_id", "imports": ["import_statements"], "helpers": ["helper_functions"], "definitions": ["definitions"], "invoke": "invoke_code", "exports": {"variable_mapping"}}]"""

        self.param_completion_prompt = """You are a quantum computing parameter completion expert. Intelligently complete missing parameters based on query analysis and domain expertise.

Input context:
- User query: Natural language description of the quantum computing task
- Domain: Type of quantum system (spin/chemistry/optimization/custom)
- Algorithm: Selected quantum algorithm (vqe/qaoa/qpe/etc)
- Selected components: Available components with their parameter schemas
- Provided parameters: Parameters explicitly mentioned in query
- Missing parameters: Parameters required by components but not provided

Analyze the user's intent and requirements to determine optimal parameter values:
- For optimization algorithms: Judge iteration needs based on problem complexity and precision requirements
- For quantum systems: Select appropriate parameter values based on physical understanding
- For computational methods: Choose parameters that balance accuracy with computational feasibility
- Prioritize accuracy and convergence quality when in doubt

Use your quantum computing expertise to select the most appropriate values for the given context.

CRITICAL: You must respond with ONLY valid JSON, no explanatory text before or after.

Output format: {"completed_params": {"param_name": value, ...}, "completion_rationale": "brief explanation"}"""
    
    def _call_openai(self, system_prompt: str, user_message: str, agent_name: str = None) -> str:
        """
        调用OpenAI API (同步版本)
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            agent_name: Agent名称（用于性能监控）
            
        Returns:
            API响应内容
        """
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            call_time = time.time() - start_time
            content = response.choices[0].message.content.strip()
            
            # 记录性能数据
            if agent_name:
                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = response.usage.completion_tokens if response.usage else 0
                record_agent_call(agent_name, system_prompt + user_message, content, call_time, "gpt-4o-mini")
                
                # 更新精确的token数据
                from .performance_monitor import get_monitor
                metrics = get_monitor().get_agent_metrics(agent_name)
                metrics.set_tokens(input_tokens, output_tokens)
            
            return content
        
        except Exception as e:
            raise RuntimeError(f"OpenAI API调用失败: {str(e)}")
    
    async def _call_openai_async(self, system_prompt: str, user_message: str) -> str:
        """
        调用OpenAI API (异步版本)
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            
        Returns:
            API响应内容
        """
        try:
            response = await self.async_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise RuntimeError(f"OpenAI API异步调用失败: {str(e)}")
    
    def _parse_json_with_retry(self, response_text: str, agent_name: str) -> Any:
        """
        严格JSON解析，支持重试
        
        Args:
            response_text: LLM响应文本
            agent_name: Agent名称（用于错误报告）
            
        Returns:
            解析后的JSON对象
            
        Raises:
            ValueError: JSON解析失败且重试超过限制
        """
        try:
            # 清理响应文本（移除可能的markdown标记）
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            return json.loads(cleaned_text)
        
        except json.JSONDecodeError as e:
            raise ValueError(f"{agent_name} Agent返回了无效的JSON: {str(e)}\n原始响应: {response_text[:200]}...")
    
    def _validate_task_card(self, data: Dict[str, Any]) -> bool:
        """验证TaskCard格式"""
        required_fields = ["domain", "problem", "algorithm", "backend", "params"]
        valid_domains = {"spin", "spin.tfim", "spin.heisenberg", "spin.ising", "chemistry.molecular", "optimization", "custom"}
        
        # 检查必需字段
        for field in required_fields:
            if field not in data:
                return False
        
        # 检查domain枚举值
        if data["domain"] not in valid_domains:
            return False
        
        # 检查backend固定值
        if data["backend"] != "qiskit":
            return False
        
        return True
    
    def _validate_component_cards(self, data: List[Dict[str, Any]]) -> bool:
        """验证ComponentCards格式"""
        if not isinstance(data, list):
            return False
        
        required_fields = ["name", "kind", "tags", "needs", "provides", "params_schema", "yields", "codegen_hint"]
        
        for card in data:
            if not isinstance(card, dict):
                return False
            for field in required_fields:
                if field not in card:
                    return False
        
        return True
    
    def _validate_param_map(self, data: Dict[str, Any]) -> bool:
        """验证ParamMap格式"""
        required_fields = ["normalized_params", "aliases", "defaults", "validation_errors"]
        
        for field in required_fields:
            if field not in data:
                return False
        
        return True
    
    def _validate_pipeline_plan(self, data: Dict[str, Any]) -> bool:
        """验证PipelinePlan格式"""
        required_fields = ["execution_order", "dependency_graph", "conflicts"]
        
        for field in required_fields:
            if field not in data:
                return False
        
        # execution_order应该是列表
        if not isinstance(data["execution_order"], list):
            return False
        
        return True
    
    def _validate_code_cells(self, data: List[Dict[str, Any]]) -> bool:
        """验证CodeCells格式和invoke语法"""
        if not isinstance(data, list):
            return False
        
        required_fields = ["id", "imports", "helpers", "definitions", "invoke", "exports"]
        
        for cell in data:
            if not isinstance(cell, dict):
                return False
            for field in required_fields:
                if field not in cell:
                    return False
            
            # 验证invoke代码语法
            invoke_code = cell.get("invoke", "")
            if invoke_code and not self._validate_invoke_syntax(invoke_code):
                print(f"⚠️ Invalid invoke syntax in {cell.get('id', 'unknown')}: {invoke_code}")
                return False
        
        return True
    
    def _validate_invoke_syntax(self, invoke_code: str) -> bool:
        """验证invoke代码的语法正确性"""
        import re
        
        # 检查常见的错误模式
        invalid_patterns = [
            r'\{.*\}\s*=',  # 字典赋值语法 {'n': 'n'} =
            r'=\s*\{.*\}$',  # 以字典结尾的赋值 = {'n': 'n'}
            r'\[\s*\]\s*=',  # 空列表赋值 [] =
            r'=\s*\[\s*\]$'  # 以空列表结尾 = []
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, invoke_code):
                return False
        
        # 基本语法检查
        try:
            compile(invoke_code, '<invoke>', 'exec')
            return True
        except SyntaxError:
            return False

    # =============================================================================
    # 五个Agent API
    # =============================================================================
    
    def task_understanding(self, query: str) -> Dict[str, Any]:
        """
        Agent 1: 任务理解 - Query → TaskCard
        
        Args:
            query: 用户自然语言查询
            
        Returns:
            TaskCard字典
        """
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.semantic_prompt, query, "SemanticAgent")
                parsed_data = self._parse_json_with_retry(response, "SemanticAgent")
                
                if self._validate_task_card(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("TaskCard格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"SemanticAgent失败，已重试{self.max_retries}次: {str(e)}")
                
                print(f"⚠️ SemanticAgent重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(0.5)
    
    def discover_components(self, task_card: Dict[str, Any], registry_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agent 2: 组件发现 - TaskCard → ComponentCards
        
        Args:
            task_card: 任务卡
            registry_data: 组件注册表数据
            
        Returns:
            ComponentCard列表
        """
        user_message = f"""TaskCard: {json.dumps(task_card, ensure_ascii=False)}

Component Registry:
{json.dumps(registry_data, ensure_ascii=False, indent=2)}

Please select appropriate components from the registry to satisfy this task requirement."""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.discovery_prompt, user_message, "DiscoveryAgent")
                parsed_data = self._parse_json_with_retry(response, "DiscoveryAgent")
                
                if self._validate_component_cards(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("ComponentCards格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"DiscoveryAgent失败，已重试{self.max_retries}次: {str(e)}")
                
                print(f"⚠️ DiscoveryAgent重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(0.5)
    
    def normalize_params(self, task_card: Dict[str, Any], components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Agent 3: 参数归一化 - 处理别名、默认值、验证
        
        Args:
            task_card: 任务卡
            components: 组件列表
            
        Returns:
            ParamMap字典
        """
        user_message = f"""TaskCard: {json.dumps(task_card, ensure_ascii=False)}

ComponentCards: {json.dumps(components, ensure_ascii=False, indent=2)}

Please process parameter normalization, including alias resolution, default value injection, and basic validation."""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.param_norm_prompt, user_message, "ParamNormAgent")
                parsed_data = self._parse_json_with_retry(response, "ParamNormAgent")
                
                if self._validate_param_map(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("ParamMap格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"ParamNormAgent失败，已重试{self.max_retries}次: {str(e)}")
                
                print(f"⚠️ ParamNormAgent重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(0.5)
    
    def plan_pipeline(self, task_card: Dict[str, Any], components: List[Dict[str, Any]], param_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent 4: 管道编排 - 生成PipelinePlan
        
        Args:
            task_card: 任务卡
            components: 组件列表
            param_map: 参数映射
            
        Returns:
            PipelinePlan字典
        """
        user_message = f"""TaskCard: {json.dumps(task_card, ensure_ascii=False)}

ComponentCards: {json.dumps(components, ensure_ascii=False, indent=2)}

ParamMap: {json.dumps(param_map, ensure_ascii=False)}

Please generate a linear execution pipeline plan based on component needs/provides dependencies."""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.pipeline_prompt, user_message, "PipelineAgent")
                parsed_data = self._parse_json_with_retry(response, "PipelineAgent")
                
                if self._validate_pipeline_plan(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("PipelinePlan格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"PipelineAgent失败，已重试{self.max_retries}次: {str(e)}")
                
                print(f"⚠️ PipelineAgent重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(0.5)
    
    def complete_parameters(self, query: str, task_card: Dict[str, Any], required_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent 6: 参数补全 - 基于组件需求智能补全缺失参数
        
        Args:
            query: 原始用户查询
            task_card: 基础任务卡
            required_schema: 组件参数需求schema
            
        Returns:
            补全后的参数字典
        """
        user_params = task_card.get("params", {})
        missing_params = set(required_schema.keys()) - set(user_params.keys())
        
        # 如果没有缺失参数，直接返回
        if not missing_params:
            return user_params
        
        # 构建补全上下文
        user_message = f"""Query: {query}

Domain: {task_card.get('domain')}
Algorithm: {task_card.get('algorithm')}
Provided Parameters: {json.dumps(user_params, ensure_ascii=False)}
Required Parameters Schema: {json.dumps(required_schema, ensure_ascii=False)}
Missing Parameters: {list(missing_params)}

Please complete the missing parameters with appropriate quantum computing defaults."""

        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.param_completion_prompt, user_message, "ParamCompletionAgent")
                parsed_data = self._parse_json_with_retry(response, "ParamCompletionAgent")
                
                validation_result = self._validate_parameter_completion(
                    parsed_data.get("completed_params", {}), 
                    required_schema
                )
                
                if validation_result["valid"]:
                    # 合并用户参数和补全参数
                    completed_params = user_params.copy()
                    completed_params.update(validation_result["validated_params"])
                    
                    # 创建新的task_card
                    completed_task_card = task_card.copy()
                    completed_task_card["params"] = completed_params
                    return completed_task_card
                else:
                    raise ValueError("Parameter completion format validation failed")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"ParamCompletionAgent failed after {self.max_retries} retries: {str(e)}")
                
                print(f"⚠️ ParamCompletionAgent retry {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(0.5)

    def _get_helper_signature(self, helper_name: str) -> str:
        """
        动态获取helper函数的签名
        
        Args:
            helper_name: helper函数名
            
        Returns:
            函数签名字符串，如 "run_vqe(hamiltonian, ansatz, optimizer, estimator)"
        """
        try:
            # 尝试从helper文件中加载函数并获取签名
            from .helper_loader import load_single_helper
            import inspect
            
            helper_func = load_single_helper(helper_name)
            if helper_func:
                sig = inspect.signature(helper_func)
                return f"{helper_name}{sig}"
        except Exception:
            # 如果动态获取失败，返回None让CodegenAgent自己处理
            pass
        
        return None

    def _get_helper_source(self, helper_name: str, component_names: list = None) -> str:
        """
        根据组件类型隔离查找helper函数源代码
        
        Args:
            helper_name: helper函数名
            component_names: 当前使用的组件名列表，用于确定查找范围
            
        Returns:
            纯函数定义源代码字符串，不包含文件导入
        """
        try:
            from .helper_loader import _find_helper_files
            import ast
            import os
            
            # 根据组件类型确定查找范围
            allowed_files = self._get_allowed_helper_files(component_names)
            
            helper_files = _find_helper_files()
            for helper_file in helper_files:
                # 只查找允许的helper文件，避免跨组件污染  
                helper_filename = os.path.basename(str(helper_file))
                if allowed_files and helper_filename not in allowed_files:
                    continue
                    
                with open(helper_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == helper_name:
                        # 只返回函数定义，避免导入污染
                        return ast.unparse(node)
        except Exception:
            pass
        
        return None
    
    def _detect_typing_imports(self, params_schema: Dict[str, Any]) -> set:
        """
        自动检测参数schema中需要的typing imports
        
        Args:
            params_schema: 组件参数schema
            
        Returns:
            set: 需要的typing import语句
        """
        PYTHON_TYPE_IMPORTS = {
            "Dict": "from typing import Dict",
            "List": "from typing import List", 
            "Optional": "from typing import Optional",
            "Union": "from typing import Union",
            "Tuple": "from typing import Tuple",
            "Any": "from typing import Any",
            "Callable": "from typing import Callable"
        }
        
        needed_imports = set()
        for param_info in params_schema.values():
            param_type = param_info.get("type", "")
            if param_type in PYTHON_TYPE_IMPORTS:
                needed_imports.add(PYTHON_TYPE_IMPORTS[param_type])
        
        return needed_imports
    
    def _detect_typing_from_code(self, code_content: str) -> set:
        """
        从生成的代码内容中检测需要的typing imports
        
        Args:
            code_content: 生成的Python代码内容
            
        Returns:
            set: 需要的typing import语句
        """
        PYTHON_TYPE_IMPORTS = {
            "Dict": "from typing import Dict",
            "List": "from typing import List", 
            "Optional": "from typing import Optional",
            "Union": "from typing import Union",
            "Tuple": "from typing import Tuple",
            "Any": "from typing import Any",
            "Callable": "from typing import Callable"
        }
        
        needed_imports = set()
        
        # 检测类型注解中的typing类型
        for type_name, import_stmt in PYTHON_TYPE_IMPORTS.items():
            if f": {type_name}" in code_content or f"-> {type_name}" in code_content:
                needed_imports.add(import_stmt)
                
        return needed_imports
    
    def _get_allowed_helper_files(self, component_names: list) -> list:
        """
        根据组件名确定允许的helper文件
        
        Args:
            component_names: 组件名列表
            
        Returns:
            允许查找的helper文件名列表
        """
        if not component_names:
            return []
            
        allowed_files = []
        for component_name in component_names:
            if 'tfim' in component_name.lower():
                allowed_files.extend(['tfim_hamiltonian.py', 'tfim_hea_circuit.py'])
            elif 'heisenberg' in component_name.lower():
                allowed_files.extend(['heisenberg_hamiltonian.py', 'heisenberg_ansatz.py'])
            elif 'molecular' in component_name.lower() or 'uccsd' in component_name.lower():
                allowed_files.extend(['molecular_hamiltonian.py', 'uccsd_ansatz.py', 'molecular_vqe.py'])
        
        # 算法组件允许通用文件
        for component_name in component_names:
            if 'vqe' in component_name.lower() or 'cobyla' in component_name.lower() or 'estimator' in component_name.lower():
                allowed_files.extend(['vqe_templates.py'])
        
        # 去重并返回
        return list(set(allowed_files))

    def _validate_parameter_completion(self, completed_params: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证AI生成的参数补全结果
        
        Args:
            completed_params: AI补全的参数
            requirements: 组件参数需求
            
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "validated_params": {}
        }
        
        required_params = requirements.get("required_params", {})
        param_metadata = requirements.get("metadata", {})
        
        # 验证每个补全的参数
        for param_name, param_value in completed_params.items():
            # 检查参数是否在需求中
            if param_name not in required_params:
                validation_result["warnings"].append(f"参数 {param_name} 不在组件需求中")
                continue
            
            # 获取参数元数据
            metadata = param_metadata.get(param_name, {})
            expected_type = metadata.get("type")
            param_enum = metadata.get("enum", [])
            
            # 类型验证
            if expected_type:
                if expected_type == "int" and not isinstance(param_value, int):
                    try:
                        param_value = int(param_value)
                    except (ValueError, TypeError):
                        validation_result["errors"].append(f"参数 {param_name} 应为int类型")
                        validation_result["valid"] = False
                        continue
                        
                elif expected_type == "float" and not isinstance(param_value, (int, float)):
                    try:
                        param_value = float(param_value)
                    except (ValueError, TypeError):
                        validation_result["errors"].append(f"参数 {param_name} 应为float类型")
                        validation_result["valid"] = False
                        continue
                        
                elif expected_type == "str" and not isinstance(param_value, str):
                    param_value = str(param_value)
            
            # 枚举值验证
            if param_enum and param_value not in param_enum:
                validation_result["errors"].append(f"参数 {param_name} 值 {param_value} 不在允许列表 {param_enum} 中")
                validation_result["valid"] = False
                continue
            
            # 验证通过，添加到结果
            validation_result["validated_params"][param_name] = param_value
        
        # 检查是否还有缺失的必需参数
        missing_required = []
        for param_name, metadata in param_metadata.items():
            if metadata.get("required", True) and param_name not in validation_result["validated_params"]:
                missing_required.append(param_name)
        
        if missing_required:
            validation_result["warnings"].append(f"仍缺少必需参数: {missing_required}")
        
        return validation_result

    def generate_codecells(self, pipeline_plan: Dict[str, Any], components: List[Dict[str, Any]], param_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Agent 5: 代码生成 - 生成CodeCell列表
        
        Args:
            pipeline_plan: 管道计划
            components: 组件列表
            param_map: 参数映射
            
        Returns:
            CodeCell列表
        """
        # 提取当前任务需要的helper函数签名和源代码信息
        helper_signatures = {}
        helper_sources = {}
        # 提取组件驱动的导入列表 (用户建议的解决方案)
        component_imports = set()
        
        # 获取组件名列表用于隔离查找
        component_names = [c.get("name", "") for c in components]
        
        # 按照Pipeline执行顺序处理组件
        execution_order = pipeline_plan.get("execution_order", [])
        ordered_components = []
        for component_name in execution_order:
            for comp in components:
                if comp.get("name") == component_name:
                    ordered_components.append(comp)
                    break
        
        # 如果execution_order为空或不完整，fallback到原始顺序
        if len(ordered_components) != len(components):
            ordered_components = components
            
        for component in ordered_components:
            # 优先使用helper_function字段，fallback到codegen_hint.helper
            helper_name = component.get("helper_function") or component.get("codegen_hint", {}).get("helper")
            if helper_name:
                print(f"🔍 Looking for helper: {helper_name} (from component: {component.get('name')})")
                # 从helper文件中动态获取函数签名
                signature = self._get_helper_signature(helper_name)
                if signature:
                    helper_signatures[helper_name] = signature
                # 获取helper函数源代码 (只从相关组件的文件中查找)
                source_code = self._get_helper_source(helper_name, component_names)
                if source_code:
                    helper_sources[helper_name] = source_code
                    print(f"✅ Found helper: {helper_name}")
                else:
                    print(f"❌ Missing helper: {helper_name}")
            
            # 收集每个组件的导入 (只用组件中定义的导入)
            import_hint = component.get("codegen_hint", {}).get("import")
            if import_hint:
                # 处理分号分隔的多个导入
                if ';' in import_hint:
                    for single_import in import_hint.split(';'):
                        component_imports.add(single_import.strip())
                else:
                    component_imports.add(import_hint)
                print(f"📦 Added imports from {component.get('name')}: {import_hint}")
            
            # 自动检测typing imports需求  
            params_schema = component.get("params_schema", {})
            typing_imports = self._detect_typing_imports(params_schema)
            for typing_import in typing_imports:
                component_imports.add(typing_import)
                if typing_imports:
                    print(f"📝 Auto-added typing imports from {component.get('name')}: {', '.join(typing_imports)}")

        # 添加基础必需导入
        component_imports.add("import numpy")
        component_imports.add("from qiskit.circuit import ParameterVector")
        component_imports.add("from qiskit.primitives import Estimator")
        component_imports.add("from qiskit_algorithms import VQE")
        component_imports.add("from qiskit_algorithms.optimizers import COBYLA")
        
        
        user_message = f"""PipelinePlan: {json.dumps(pipeline_plan, ensure_ascii=False)}

ComponentCards: {json.dumps(components, ensure_ascii=False, indent=2)}

ParamMap: {json.dumps(param_map, ensure_ascii=False)}

HelperSignatures: {json.dumps(helper_signatures, ensure_ascii=False)}

HelperSources: {json.dumps(helper_sources, ensure_ascii=False)}

ComponentImports: {list(component_imports)}

Please generate corresponding CodeCell for each component, including imports, helpers, definitions, invoke, and exports.

CRITICAL: helpers field must contain complete function definitions (def statements) for all helper functions used in invoke code.
Use the provided HelperSources for complete function implementations.

CRITICAL IMPORT RULE - COMPONENT-DRIVEN:
Use ONLY imports from ComponentImports list provided in the user message.
ComponentImports contains the exact imports needed for the selected components.

- For spin systems (TFIM/Heisenberg): ComponentImports will NOT include qiskit_nature
- For molecular systems: ComponentImports will include necessary qiskit_nature imports  
- For algorithms: ComponentImports includes the specific optimizers/primitives needed

Do NOT add any imports beyond ComponentImports list.
Do NOT use quantum computing knowledge to add "standard" imports.
ComponentImports is dynamically generated based on selected components - trust it completely.

For example, if invoke uses "H = build_tfim_h(n, hx, j)", copy the complete function from HelperSources.

Use the HelperSignatures to ensure correct function calls with proper parameter order."""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.codegen_prompt, user_message, "CodegenAgent")
                parsed_data = self._parse_json_with_retry(response, "CodegenAgent")
                
                if self._validate_code_cells(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("CodeCells格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"CodegenAgent失败，已重试{self.max_retries}次: {str(e)}")
                
                print(f"⚠️ CodegenAgent重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(0.5)
    
    async def discover_and_normalize_parallel(self, task_card: Dict[str, Any], registry_data: List[Dict[str, Any]]) -> tuple:
        """
        并行执行组件发现和初步参数归一化
        
        Args:
            task_card: 任务卡
            registry_data: 组件注册表数据
            
        Returns:
            (components, initial_param_map) 元组
        """
        # 准备并行任务
        discovery_task = self._discover_components_async(task_card, registry_data)
        param_norm_task = self._normalize_params_initial_async(task_card)
        
        # 并行执行
        components, initial_param_map = await asyncio.gather(
            discovery_task, 
            param_norm_task,
            return_exceptions=True
        )
        
        # 错误处理
        if isinstance(components, Exception):
            raise RuntimeError(f"组件发现并行执行失败: {components}")
        if isinstance(initial_param_map, Exception):
            raise RuntimeError(f"参数归一化并行执行失败: {initial_param_map}")
            
        return components, initial_param_map
    
    async def _discover_components_async(self, task_card: Dict[str, Any], registry_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """异步组件发现"""
        user_message = f"""
TaskCard: {json.dumps(task_card, ensure_ascii=False)}

Component Registry: {json.dumps(registry_data, ensure_ascii=False)}

Please select appropriate components from the registry based on the TaskCard."""

        for attempt in range(self.max_retries):
            try:
                response = await self._call_openai_async(self.discovery_prompt, user_message)
                parsed_data = self._parse_json_with_retry(response, "DiscoveryAgent")
                
                if self._validate_component_cards(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("ComponentCards格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"DiscoveryAgent异步调用失败，已重试{self.max_retries}次: {str(e)}")
                
                await asyncio.sleep(0.5)
    
    async def _normalize_params_initial_async(self, task_card: Dict[str, Any]) -> Dict[str, Any]:
        """异步初步参数归一化（仅基于TaskCard）"""
        user_message = f"""
TaskCard: {json.dumps(task_card, ensure_ascii=False)}

Please perform initial parameter normalization for the TaskCard parameters, including alias mapping and default value injection."""

        for attempt in range(self.max_retries):
            try:
                response = await self._call_openai_async(self.param_norm_prompt, user_message)
                parsed_data = self._parse_json_with_retry(response, "ParamNormAgent")
                
                if self._validate_param_map(parsed_data):
                    return parsed_data
                else:
                    raise ValueError("ParamMap格式验证失败")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"ParamNormAgent异步调用失败，已重试{self.max_retries}次: {str(e)}")
                
                await asyncio.sleep(0.5)

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent使用统计信息"""
        return {
            "api_key_configured": bool(self.api_key),
            "max_retries": self.max_retries,
            "parallel_support": True,
            "supported_agents": [
                "SemanticAgent", "DiscoveryAgent", "ParamNormAgent", 
                "PipelineAgent", "CodegenAgent"
            ]
        }


# =============================================================================
# 便利函数
# =============================================================================

def create_engine(api_key: Optional[str] = None, max_retries: int = 3) -> LLMEngine:
    """
    创建LLM引擎实例
    
    Args:
        api_key: OpenAI API密钥
        max_retries: 最大重试次数
        
    Returns:
        LLMEngine实例
    """
    return LLMEngine(api_key=api_key, max_retries=max_retries)


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing LLMEngine...")
    
    try:
        # 创建引擎
        engine = create_engine()
        
        # 测试基础配置
        stats = engine.get_agent_stats()
        print("📊 引擎配置:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 测试SemanticAgent
        test_query = "帮我计算8比特TFIM的基态能量，使用VQE算法"
        print(f"\n🔍 测试查询: {test_query}")
        
        print("🤖 调用SemanticAgent...")
        task_card = engine.task_understanding(test_query)
        print(f"📋 TaskCard: {json.dumps(task_card, ensure_ascii=False, indent=2)}")
        
        # 验证TaskCard格式
        if engine._validate_task_card(task_card):
            print("✅ TaskCard格式验证通过！")
        else:
            print("❌ TaskCard格式验证失败！")
        
        print("\n🎉 LLMEngine基础测试通过！")
        print("📝 注意：完整的Agent测试需要组件注册表数据。")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        print("💡 请检查OPENAI_API_KEY环境变量配置。")