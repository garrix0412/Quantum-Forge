"""
Code Assembler - QuantumForge V5 智能代码组装引擎

LLM驱动的完整量子程序组装系统。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 3.1 设计。
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入相关类型
try:
    from .execution_memory import ExecutionMemory
    from .llm_engine import call_llm
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.execution_memory import ExecutionMemory
    from core.llm_engine import call_llm


class IntelligentCodeAssembler:
    """
    LLM驱动的智能代码组装引擎
    
    核心功能:
    - 智能组装完整可执行Python程序
    - 自动解决变量名冲突
    - 优化import组织和代码结构
    - 生成专业的量子计算代码
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.output_directory = "generated_quantum_code"
        
        # 确保输出目录存在
        os.makedirs(self.output_directory, exist_ok=True)
    
    def assemble_complete_program(self, user_query: str, memory: ExecutionMemory) -> str:
        """
        组装完整的量子计算Python程序
        
        Args:
            user_query: 用户原始查询
            memory: 执行记忆，包含所有组件输出
            
        Returns:
            生成的完整Python代码文件路径
        """
        # 1. 获取所有组件输出数据
        all_outputs = memory.get_all_outputs()
        
        # 2. 构建代码组装prompt
        prompt = self._build_assembly_prompt(user_query, all_outputs)
        
        # 3. LLM生成完整代码
        try:
            response = call_llm(prompt, model=self.model)
            complete_code = self._parse_code_response(response)
            
            # 4. 生成文件并保存
            file_path = self._save_generated_code(complete_code, user_query)
            
            return file_path
            
        except Exception as e:
            # LLM失败时的fallback策略
            return self._fallback_code_assembly(user_query, memory)
    
    def _build_assembly_prompt(self, user_query: str, all_outputs: Dict[str, Any]) -> str:
        """构建代码组装的LLM prompt"""
        
        # 分析数据结构
        formatted_outputs = self._format_component_outputs(all_outputs)
        quantum_intent = all_outputs.get("quantum_intent", {})
        
        return f"""
Assemble a complete, executable quantum computing Python program using the provided code fragments.

Original User Query: "{user_query}"

Quantum Problem Context:
- Problem Type: {quantum_intent.get('problem_type', 'Unknown')}
- Algorithm: {quantum_intent.get('algorithm', 'Unknown')}
- Parameters: {quantum_intent.get('parameters', {})}
- Requirements: {quantum_intent.get('requirements', [])}

{formatted_outputs}

CRITICAL ASSEMBLY INSTRUCTIONS:

1. **USE PROVIDED CODE FRAGMENTS**: You MUST use the exact code fragments provided by each component. Do not rewrite or recreate the logic.

2. **API CONSISTENCY**: Never hallucinate libraries or functions - only use known, verified Python packages like:
   - qiskit (quantum computing framework)
   - numpy (numerical computing)
   - matplotlib (plotting)
   - Standard Python libraries

3. **INTELLIGENT INTEGRATION TASKS**:
   - Connect code fragments logically in correct execution order
   - Unify variable names across components (e.g., if one component uses 'hamiltonian' and another uses 'H', standardize to one)
   - Resolve import statements and remove duplicates
   - Add necessary glue code for data flow between components
   - Create main execution function that calls components in sequence

4. **PRESERVE COMPONENT LOGIC**: The core quantum algorithms must use the exact implementations provided by components.

5. **COMPLETE PROGRAM STRUCTURE**:
   - Consolidated import statements at the top
   - Component functions preserved exactly as provided
   - Main execution function that orchestrates the workflow
   - Proper error handling and result display

6. **VARIABLE CONSISTENCY**: Ensure variables flow correctly between code fragments:
   - Parameters from TFIMModelGenerator → TFIMHamiltonianBuilder
   - Hamiltonian from builder → VQE components
   - Circuit parameters between components

Return ONLY the complete Python code, no explanations:

```python
# Your assembled quantum program here using provided code fragments
```

IMPORTANT: This is intelligent code assembly, not code generation. Use the provided fragments and focus on connecting them properly.
"""
    
    def _format_component_outputs(self, all_outputs: Dict[str, Any]) -> str:
        """格式化组件输出供LLM分析"""
        formatted_parts = []
        
        # 组件输出部分
        if "component_outputs" in all_outputs and all_outputs["component_outputs"]:
            formatted_parts.append("Component Generated Code Fragments:")
            
            for comp_name, output in all_outputs["component_outputs"].items():
                formatted_parts.append(f"\n{comp_name}:")
                for key, value in output.items():
                    if key != "notes":  # 跳过notes字段
                        if key == "code":
                            # 代码片段完整显示，不截断
                            formatted_parts.append(f"  {key}: {value}")
                        elif isinstance(value, dict):
                            formatted_parts.append(f"  {key}: {json.dumps(value, indent=2)}")
                        elif isinstance(value, list):
                            formatted_parts.append(f"  {key}: {value}")
                        elif isinstance(value, str) and len(value) > 200:
                            # 非代码字段可以截断显示
                            formatted_parts.append(f"  {key}: {value[:200]}...")
                        else:
                            formatted_parts.append(f"  {key}: {value}")
        
        # 当前状态
        if "current_state" in all_outputs and all_outputs["current_state"]:
            state = all_outputs["current_state"]
            formatted_parts.append(f"\nCurrent State Summary:")
            for key, value in state.items():
                if key not in ["timestamp", "execution_id"]:
                    formatted_parts.append(f"  {key}: {value}")
        
        return "\n".join(formatted_parts)
    
    def _parse_code_response(self, response: str) -> str:
        """解析LLM返回的代码"""
        # 清理响应，提取代码部分
        response = response.strip()
        
        # 如果包含代码块标记，提取其中的代码
        if '```python' in response:
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end != -1:
                code = response[start:end].strip()
            else:
                code = response[start:].strip()
        elif '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            if end != -1:
                code = response[start:end].strip()
            else:
                code = response[start:].strip()
        else:
            code = response
        
        # 验证代码基本结构
        if not code or len(code.strip()) < 50:
            raise ValueError("Generated code is too short or empty")
        
        # 检查是否包含基本的Python结构
        if 'import' not in code:
            raise ValueError("Generated code lacks import statements")
        
        return code
    
    def _save_generated_code(self, code: str, user_query: str) -> str:
        """保存生成的代码到文件"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = str(hash(user_query))[-6:]  # 取查询hash的最后6位
        filename = f"quantum_program_{timestamp}_{query_hash}.py"
        file_path = os.path.join(self.output_directory, filename)
        
        # 添加文件头注释
        header_comment = f'''"""
Quantum Computing Program
Generated by QuantumForge V5

Original Query: {user_query}
Generated Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

'''
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header_comment + code)
        
        return file_path
    
    def _fallback_code_assembly(self, user_query: str, memory: ExecutionMemory) -> str:
        """
        LLM失败时的后备策略
        尝试简化的LLM调用或返回错误
        """
        # 尝试更简单的prompt进行二次调用
        try:
            simplified_prompt = f"""
Generate a basic Python quantum computing program for: {user_query}

Based on available data from memory:
{self._format_component_outputs(memory.get_all_outputs())}

Requirements:
- Complete executable Python file
- Use Qiskit framework
- Include imports, main function, and basic structure
- Focus on functionality over optimization

Return only the Python code:
"""
            response = call_llm(simplified_prompt, model=self.model)
            simple_code = self._parse_code_response(response)
            return self._save_generated_code(simple_code, user_query)
            
        except Exception as e:
            # 完全失败时，抛出错误而不是使用模板
            raise Exception(f"Code assembly failed: {str(e)}. Please check component outputs and try again.")
    
    
    def get_assembly_info(self, memory: ExecutionMemory) -> Dict[str, Any]:
        """
        获取代码组装信息，用于调试和验证
        
        Returns:
            代码组装的详细信息
        """
        all_outputs = memory.get_all_outputs()
        
        info = {
            "total_components": 0,
            "available_data": {},
            "code_complexity": "unknown",
            "estimated_lines": 0
        }
        
        # 分析可用数据
        if "component_outputs" in all_outputs:
            info["total_components"] = len(all_outputs["component_outputs"])
            
            # 统计数据类型
            data_types = {}
            total_data_points = 0
            
            for comp_name, output in all_outputs["component_outputs"].items():
                for key, value in output.items():
                    if key != "notes":
                        data_type = type(value).__name__
                        data_types[data_type] = data_types.get(data_type, 0) + 1
                        total_data_points += 1
            
            info["available_data"] = data_types
            info["total_data_points"] = total_data_points
            
            # 估算代码复杂度
            if total_data_points > 20:
                info["code_complexity"] = "high"
                info["estimated_lines"] = 150 + total_data_points * 2
            elif total_data_points > 10:
                info["code_complexity"] = "medium"
                info["estimated_lines"] = 80 + total_data_points * 3
            else:
                info["code_complexity"] = "low"
                info["estimated_lines"] = 50 + total_data_points * 4
        
        return info
