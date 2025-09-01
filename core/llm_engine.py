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
        
        self.semantic_prompt = """你是量子算法需求解析助手。将用户中文/英文自然语言需求解析为 TaskCard(JSON)。
必须严格输出 JSON，键包括 domain, problem, algorithm, backend, params。
domain ∈ {spin, chemistry, optimization, custom}；backend 固定 "qiskit"。
params 中如未给出，基于常识填默认：optimizer=COBYLA, reps=2, boundary=periodic, shots=null, seed=42, maxiter=200。

例子：
输入："帮我计算8比特TFIM的基态能量"
输出：{"domain": "spin", "problem": "tfim_ground_energy", "algorithm": "vqe", "backend": "qiskit", "params": {"n": 8, "optimizer": "COBYLA", "reps": 2, "boundary": "periodic", "shots": null, "seed": 42, "maxiter": 200}}"""

        self.discovery_prompt = """你是组件选择助手。基于 TaskCard，从注册表记录中挑选能覆盖 needs/provides 的组件集合。
每个组件以 ComponentCard(JSON) 形式返回。保留 codegen_hint 提示。
优先选择 algorithm 对应组件（如 vqe→Algorithm.VQE），以及与 domain/problem 相匹配的 hamiltonian/circuit。
必须严格输出 JSON 数组格式。

输出格式：[{"name": "组件名", "kind": "类型", "tags": ["标签"], "needs": ["依赖"], "provides": ["提供"], "params_schema": {}, "yields": {}, "codegen_hint": {}}]"""

        self.param_norm_prompt = """你是参数归一化助手。基于 TaskCard 和 ComponentCards，生成 ParamMap(JSON)。
处理参数别名、注入默认值、做基础校验。
必须严格输出 JSON，键包括 normalized_params, aliases, defaults, validation_errors。

输出格式：{"normalized_params": {}, "aliases": {}, "defaults": {}, "validation_errors": []}"""

        self.pipeline_prompt = """你是管道编排助手。基于 TaskCard、ComponentCards 和 ParamMap，生成 PipelinePlan(JSON)。
实现线性拓扑排序，解决组件依赖关系。
必须严格输出 JSON，键包括 execution_order, dependency_graph, conflicts。

输出格式：{"execution_order": ["组件ID列表"], "dependency_graph": {}, "conflicts": []}"""

        self.codegen_prompt = """你是代码生成助手。基于 PipelinePlan、ComponentCards 和 ParamMap，生成 CodeCell 列表。
每个组件对应一个 CodeCell，包含 imports, helpers, definitions, invoke, exports。

重要：invoke字段必须是有效的Python语句，不能包含字典赋值语法。

正确示例：
- "H = build_tfim_h(n, hx, j, boundary)"  ✅
- "ansatz = tfim_hea(n, reps)"  ✅
- "result, energy = run_vqe(H, ansatz, optimizer, maxiter)"  ✅

错误示例：
- "{'n': 'n', 'hx': 'h'} = Hamiltonian.TFIM"  ❌
- "n, hx, j = params['n'], params['hx'], params['j']"  ❌

参数说明：
- 使用ParamMap中的normalized_params作为实际参数名
- invoke代码中直接使用这些标准参数名（如n, hx, j）
- 不要创建参数别名赋值

必须严格输出 JSON 数组格式：
[{"id": "cell_id", "imports": ["import语句"], "helpers": ["辅助函数"], "definitions": ["定义"], "invoke": "调用代码", "exports": {"变量映射"}}]"""
    
    def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """
        调用OpenAI API (同步版本)
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            
        Returns:
            API响应内容
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            return response.choices[0].message.content.strip()
        
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
                model="gpt-4",
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
        valid_domains = {"spin", "chemistry", "optimization", "custom"}
        
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
                response = self._call_openai(self.semantic_prompt, query)
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

组件注册表:
{json.dumps(registry_data, ensure_ascii=False, indent=2)}

请从注册表中选择合适的组件来满足这个任务需求。"""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.discovery_prompt, user_message)
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

请处理参数归一化，包括别名解析、默认值注入和基础验证。"""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.param_norm_prompt, user_message)
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

请基于组件的needs/provides依赖关系，生成线性执行顺序的管道计划。"""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.pipeline_prompt, user_message)
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
        user_message = f"""PipelinePlan: {json.dumps(pipeline_plan, ensure_ascii=False)}

ComponentCards: {json.dumps(components, ensure_ascii=False, indent=2)}

ParamMap: {json.dumps(param_map, ensure_ascii=False)}

请为每个组件生成对应的CodeCell，包含imports、helpers、definitions、invoke、exports。"""
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_openai(self.codegen_prompt, user_message)
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
任务卡：{json.dumps(task_card, ensure_ascii=False)}

组件注册表：{json.dumps(registry_data, ensure_ascii=False)}

请根据任务卡从注册表中选择合适的组件。"""

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
任务卡：{json.dumps(task_card, ensure_ascii=False)}

请对任务卡中的参数进行初步归一化处理，包括别名映射和默认值注入。"""

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