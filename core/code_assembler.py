"""
代码装配器 - QuantumForge vNext

将Memory中的CodeCells装配成单文件Python源码。
基于new.md第7节的确定性合并规则实现。
"""

from typing import Dict, List, Any, Set
try:
    from .execution_memory import Memory
    from .import_manager import normalize_imports
    from .code_templates import generate_file_banner, main_wrapper, emit_entry, generate_param_aliases
    from .llm_engine import create_engine
except ImportError:
    # 直接运行时的兼容处理
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from execution_memory import Memory
    from import_manager import normalize_imports
    from code_templates import generate_file_banner, main_wrapper, emit_entry, generate_param_aliases
    from llm_engine import create_engine


def assemble(memory: Memory, pipeline_plan: Dict[str, Any], task_card: Dict[str, Any], param_map: Dict[str, Any]) -> str:
    """
    装配完整的Python源码
    
    Args:
        memory: 包含CodeCells的Memory容器
        pipeline_plan: 管道执行计划
        task_card: 原始任务卡
        param_map: 参数映射
        
    Returns:
        完整的Python源码字符串
    """
    # 1. 导出所有CodeCells
    code_cells = memory.export()
    
    if not code_cells:
        raise ValueError("Memory中没有CodeCells，无法装配代码")
    
    # 2. 收集和处理imports
    all_imports = []
    for cell in code_cells:
        all_imports.extend(cell.imports)
    
    # 去重和分组排序
    normalized_imports = normalize_imports(all_imports)
    
    # 3. 收集和处理helpers/definitions（处理命名冲突）
    all_helpers, all_definitions = _merge_code_sections(code_cells)
    
    # 3.5 加载真实的helper函数实现和相关导入
    from .helper_loader import load_helper_functions
    all_helpers, helper_imports = load_helper_functions(all_helpers)
    
    # 合并helper函数的导入
    all_imports.extend(helper_imports)
    normalized_imports = normalize_imports(all_imports)
    
    # 3.6 清理definitions中的无效变量名
    all_definitions = _clean_definitions(all_definitions)
    
    # 4. 生成main函数体
    main_body = _generate_main_body(code_cells, pipeline_plan, param_map)
    
    # 4.5 修正函数调用参数不匹配问题
    main_body = _fix_function_calls(main_body)
    
    # 5. 生成参数规格（从TaskCard和ParamMap）
    args_spec = _build_args_spec(task_card, param_map)
    
    # 6. 使用代码模板装配
    try:
        from .code_templates import create_complete_program
    except ImportError:
        from code_templates import create_complete_program
    
    complete_code = create_complete_program(
        query=task_card.get("problem", "Unknown query"),
        algorithm=task_card.get("algorithm", "VQE").upper(),
        imports=normalized_imports,
        helpers=all_helpers,
        definitions=all_definitions,
        main_body=main_body,
        args_spec=args_spec,
        param_aliases=param_map.get("aliases", {})
    )
    
    return complete_code


def _merge_code_sections(code_cells: List[Any]) -> tuple[List[str], List[str]]:
    """
    合并代码段落，处理命名冲突
    
    Args:
        code_cells: CodeCell列表
        
    Returns:
        (合并后的helpers, 合并后的definitions)
    """
    all_helpers = []
    all_definitions = []
    used_names = set()
    
    for cell in code_cells:
        cell_id = cell.id
        
        # 处理helpers
        for helper in cell.helpers:
            processed_helper = _resolve_naming_conflict(helper, used_names, cell_id)
            all_helpers.append(processed_helper)
            
            # 提取函数名并记录
            func_name = _extract_function_name(processed_helper)
            if func_name:
                used_names.add(func_name)
        
        # 处理definitions
        for definition in cell.definitions:
            processed_def = _resolve_naming_conflict(definition, used_names, cell_id)
            all_definitions.append(processed_def)
            
            # 提取定义名并记录
            def_name = _extract_definition_name(processed_def)
            if def_name:
                used_names.add(def_name)
    
    return all_helpers, all_definitions


def _resolve_naming_conflict(code_line: str, used_names: Set[str], cell_id: str) -> str:
    """
    解决命名冲突
    
    Args:
        code_line: 代码行
        used_names: 已使用的名称集合
        cell_id: Cell ID
        
    Returns:
        处理冲突后的代码行
    """
    # 提取函数名或定义名
    name = _extract_function_name(code_line) or _extract_definition_name(code_line)
    
    if name and name in used_names:
        # 添加cell_id后缀
        new_name = f"{name}__{cell_id}"
        code_line = code_line.replace(f" {name}(", f" {new_name}(")
        code_line = code_line.replace(f"def {name}(", f"def {new_name}(")
        code_line = code_line.replace(f" {name} =", f" {new_name} =")
        code_line = code_line.replace(f"{name} =", f"{new_name} =")
    
    return code_line


def _extract_function_name(code_line: str) -> str:
    """提取函数名"""
    code_line = code_line.strip()
    if code_line.startswith("def "):
        # 提取 "def function_name(" 中的函数名
        parts = code_line[4:].split("(")
        if parts:
            return parts[0].strip()
    return ""


def _extract_definition_name(code_line: str) -> str:
    """提取变量/常量定义名"""
    code_line = code_line.strip()
    if " = " in code_line and not code_line.startswith("def "):
        # 提取 "VARIABLE = value" 中的变量名
        parts = code_line.split(" = ")
        if parts:
            return parts[0].strip()
    return ""


def _generate_main_body(code_cells: List[Any], pipeline_plan: Dict[str, Any], param_map: Dict[str, Any]) -> str:
    """
    生成main函数体
    
    Args:
        code_cells: CodeCell列表
        pipeline_plan: 管道计划
        param_map: 参数映射
        
    Returns:
        main函数体代码
    """
    body_lines = []
    
    # 添加参数别名归一化代码
    aliases = param_map.get("aliases", {})
    if aliases:
        alias_code = generate_param_aliases(aliases)
        if alias_code.strip():
            body_lines.append(alias_code.rstrip())
    
    # 按管道计划的执行顺序生成调用代码
    execution_order = pipeline_plan.get("execution_order", [])
    cell_map = {cell.id: cell for cell in code_cells}
    
    for comp_name in execution_order:
        # 查找对应的CodeCell
        cell = None
        for c in code_cells:
            if comp_name in c.id or comp_name in c.invoke:
                cell = c
                break
        
        if cell and cell.invoke.strip():
            # 添加注释
            body_lines.append(f"    # {comp_name}")
            
            # 添加调用代码
            invoke_lines = cell.invoke.strip().split('\n')
            for line in invoke_lines:
                if line.strip():
                    # 确保正确的缩进
                    if not line.startswith('    '):
                        line = '    ' + line.strip()
                    body_lines.append(line)
            
            body_lines.append("")  # 空行分隔
    
    return '\n'.join(body_lines)


def _build_args_spec(task_card: Dict[str, Any], param_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建main函数的参数规格
    
    Args:
        task_card: 任务卡
        param_map: 参数映射
        
    Returns:
        参数规格字典
    """
    args_spec = {}
    
    # 从ParamMap获取归一化参数（统一字段名）
    normalized_params = param_map.get("validated", param_map.get("normalized_params", {}))
    defaults = param_map.get("defaults", {})
    
    for param_name, param_value in normalized_params.items():
        # 清理参数名（移除特殊字符，确保是有效的Python标识符）
        clean_param_name = _clean_param_name(param_name)
        
        # 推断参数类型
        param_type = _infer_param_type(param_value)
        
        # 构建参数规格
        param_spec = {
            "type": param_type,
            "description": f"Parameter {clean_param_name}"
        }
        
        # 如果有默认值，添加到规格中
        if param_name in defaults:
            param_spec["default"] = defaults[param_name]
        elif param_value is not None:
            param_spec["default"] = param_value
        
        args_spec[clean_param_name] = param_spec
    
    return args_spec


def _infer_param_type(value: Any) -> str:
    """推断参数类型"""
    if value is None:
        return "Any"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "str"
    elif isinstance(value, list):
        return "List"
    elif isinstance(value, dict):
        return "Dict"
    else:
        return "Any"


def generate_code_with_cells(task_card: Dict[str, Any], components: List[Dict[str, Any]], param_map: Dict[str, Any]) -> str:
    """
    生成CodeCells并装配完整代码（端到端测试用）
    
    Args:
        task_card: 任务卡
        components: 组件列表
        param_map: 参数映射
        
    Returns:
        完整的Python源码
    """
    # 创建Memory
    try:
        from .execution_memory import create
        from .pipeline_composer import compose
        from .schemas import CodeCell
    except ImportError:
        from execution_memory import create
        from pipeline_composer import compose
        from schemas import CodeCell
    
    memory = create()
    
    # 生成管道计划
    pipeline_plan = compose(task_card, components, param_map)
    
    # 调用CodegenAgent生成CodeCells
    engine = create_engine()
    code_cells_data = engine.generate_codecells(pipeline_plan, components, param_map)
    
    # 转换为CodeCell对象并添加到Memory
    for cell_data in code_cells_data:
        cell = CodeCell(
            id=cell_data["id"],
            imports=cell_data["imports"],
            helpers=cell_data["helpers"],
            definitions=cell_data["definitions"],
            invoke=cell_data["invoke"],
            exports=cell_data["exports"]
        )
        memory.add(cell)
    
    # 装配代码
    return assemble(memory, pipeline_plan, task_card, param_map)


def _clean_param_name(param_name: str) -> str:
    """
    清理参数名，确保是有效的Python标识符
    
    Args:
        param_name: 原始参数名
        
    Returns:
        清理后的参数名
    """
    import re
    
    # 移除特殊字符，只保留字母、数字和下划线
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', param_name)
    
    # 确保以字母或下划线开头
    if clean_name and clean_name[0].isdigit():
        clean_name = f"param_{clean_name}"
    
    # 如果为空或者是Python关键字，使用默认名
    if not clean_name or clean_name in ['def', 'class', 'import', 'from', 'if', 'else', 'return']:
        clean_name = f"param_{hash(param_name) % 1000}"
    
    return clean_name


def _clean_definitions(definitions: List[str]) -> List[str]:
    """
    清理definitions中的无效变量名
    
    Args:
        definitions: 原始定义列表
        
    Returns:
        清理后的定义列表
    """
    cleaned_definitions = []
    seen_vars = set()
    
    for definition in definitions:
        # 跳过空行
        if not definition.strip():
            continue
            
        # 检查是否是有效的赋值语句
        if '=' in definition:
            var_part, value_part = definition.split('=', 1)
            var_name = var_part.strip()
            
            # 处理复合参数名（如n__Circuit_TFIM_HEA）
            if '__' in var_name:
                # 提取基础参数名（取第一部分）
                base_name = var_name.split('__')[0]
                clean_var_name = _clean_param_name(base_name)
            else:
                # 清理普通变量名
                clean_var_name = _clean_param_name(var_name)
            
            # 避免重复定义
            if clean_var_name not in seen_vars:
                cleaned_definition = f"{clean_var_name} = {value_part.strip()}"
                cleaned_definitions.append(cleaned_definition)
                seen_vars.add(clean_var_name)
        else:
            # 非赋值语句，直接保留
            cleaned_definitions.append(definition)
    
    return cleaned_definitions



def _fix_function_calls(main_body: str) -> str:
    """
    修正函数调用参数不匹配问题
    
    Args:
        main_body: 原始main函数体
        
    Returns:
        修正后的main函数体
    """
    # 已知的函数签名映射
    function_signatures = {
        'run_vqe': 'run_vqe(hamiltonian, ansatz, optimizer, maxiter)',
        'tfim_hea': 'tfim_hea(n, reps)',
        'build_tfim_h': 'build_tfim_h(n, hx, j, boundary)',
        'create_cobyla_optimizer': 'create_cobyla_optimizer(maxiter)',
        'create_estimator': 'create_estimator()'
    }
    
    # 正确的函数调用模式
    correct_calls = {
        'run_vqe': 'run_vqe(H, ansatz, optimizer, maxiter)',
        'tfim_hea': 'tfim_hea(n, reps)', 
        'build_tfim_h': 'build_tfim_h(n, hx, j, boundary)',
        'create_cobyla_optimizer': 'create_cobyla_optimizer(maxiter)',
        'create_estimator': 'create_estimator()'
    }
    
    # 修正函数调用
    fixed_body = main_body
    import re
    
    # 修正每个函数的调用
    for func_name, correct_call in correct_calls.items():
        # 查找该函数的所有调用
        pattern = f'{func_name}\\([^)]*\\)'
        matches = re.findall(pattern, fixed_body)
        
        for match in matches:
            # 如果调用模式不正确，替换为正确的调用
            if match != correct_call:
                # 对于结果赋值，保持变量名
                if func_name == 'run_vqe':
                    # 查找result, energy = run_vqe(...)模式
                    result_pattern = r'(\w+(?:,\s*\w+)*)\s*=\s*' + re.escape(match)
                    result_matches = re.findall(result_pattern, fixed_body)
                    if result_matches:
                        var_names = result_matches[0]
                        fixed_body = re.sub(result_pattern, f'{var_names} = {correct_call}', fixed_body)
                    else:
                        fixed_body = fixed_body.replace(match, correct_call)
                else:
                    fixed_body = fixed_body.replace(match, correct_call)
    
    return fixed_body


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing CodeAssembler...")
    
    # 创建测试数据
    from execution_memory import create
    from schemas import CodeCell
    
    memory = create()
    
    # 添加测试CodeCells
    cell1 = CodeCell(
        id="hamiltonian_cell",
        imports=["import numpy as np", "from qiskit.quantum_info import SparsePauliOp"],
        helpers=["def build_tfim_h(n, hx, j, boundary='periodic'):", "    # 构建TFIM哈密顿量", "    return SparsePauliOp.from_list([...])"],
        definitions=["PAULI_X = 'X'", "PAULI_Z = 'Z'"],
        invoke="H = build_tfim_h(n=n, hx=hx, j=j, boundary=boundary)",
        exports={"H": "hamiltonian"}
    )
    
    cell2 = CodeCell(
        id="vqe_cell",
        imports=["from qiskit_algorithms import VQE", "from qiskit.primitives import Estimator"],
        helpers=["def run_vqe(hamiltonian, ansatz, optimizer, estimator):", "    # 运行VQE算法", "    return vqe.compute_minimum_eigenvalue(hamiltonian)"],
        definitions=[],
        invoke="result = run_vqe(H, ansatz, optimizer, estimator)\nenergy = float(result.eigenvalue.real)",
        exports={"energy": "ground_state_energy"}
    )
    
    memory.add(cell1)
    memory.add(cell2)
    
    # 测试数据
    test_pipeline_plan = {
        "execution_order": ["Hamiltonian.TFIM", "Algorithm.VQE"],
        "dependency_graph": {
            "Hamiltonian.TFIM": [],
            "Algorithm.VQE": ["hamiltonian", "ansatz"]
        },
        "conflicts": []
    }
    
    test_task_card = {
        "domain": "spin",
        "problem": "tfim_ground_energy",
        "algorithm": "vqe",
        "backend": "qiskit",
        "params": {"n": 8, "hx": 1.0, "j": 1.0}
    }
    
    test_param_map = {
        "normalized_params": {"n": 8, "hx": 1.0, "j": 1.0, "reps": 2, "optimizer": "COBYLA"},
        "aliases": {"num_qubits": "n", "h_x": "hx"},
        "defaults": {"optimizer": "COBYLA", "reps": 2},
        "validation_errors": []
    }
    
    print(f"📋 任务: {test_task_card['problem']}")
    print(f"🧱 CodeCells: {memory.size()}个")
    print(f"📊 执行顺序: {test_pipeline_plan['execution_order']}")
    
    try:
        # 测试代码装配
        assembled_code = assemble(memory, test_pipeline_plan, test_task_card, test_param_map)
        
        print(f"\n📄 生成的代码（前500字符）:")
        print("-" * 60)
        print(assembled_code[:500] + "..." if len(assembled_code) > 500 else assembled_code)
        print("-" * 60)
        
        # 验证生成的代码基本结构
        code_lines = assembled_code.split('\n')
        has_imports = any('import' in line for line in code_lines[:20])
        has_main = any('def main(' in line for line in code_lines)
        has_entry = any('if __name__ == "__main__"' in line for line in code_lines)
        
        print(f"\n🔍 代码结构验证:")
        print(f"   包含import语句: {'✅' if has_imports else '❌'}")
        print(f"   包含main函数: {'✅' if has_main else '❌'}")
        print(f"   包含程序入口: {'✅' if has_entry else '❌'}")
        
        if has_imports and has_main and has_entry:
            print("\n✅ CodeAssembler测试通过！")
        else:
            print("\n⚠️ 代码结构不完整")
        
    except Exception as e:
        print(f"❌ 代码装配失败: {str(e)}")
        
    # 测试端到端代码生成（需要真实API）
    print(f"\n🚀 测试端到端代码生成...")
    
    test_components = [
        {
            "name": "Hamiltonian.TFIM",
            "kind": "hamiltonian", 
            "needs": [],
            "provides": ["hamiltonian"],
            "params_schema": {"n": "int", "hx": "float", "j": "float"}
        },
        {
            "name": "Algorithm.VQE",
            "kind": "algorithm",
            "needs": ["hamiltonian", "ansatz"],
            "provides": ["energy"],
            "params_schema": {"optimizer": "str", "maxiter": "int"}
        }
    ]
    
    try:
        # 端到端测试（会调用真实OpenAI API）
        complete_code = generate_code_with_cells(test_task_card, test_components, test_param_map)
        
        print(f"🎉 端到端代码生成成功！")
        print(f"📏 代码长度: {len(complete_code)}字符")
        
        # 检查代码质量
        if "def main(" in complete_code and "if __name__" in complete_code:
            print("✅ 端到端测试通过！")
        else:
            print("⚠️ 端到端生成的代码结构可能不完整")
        
    except Exception as e:
        print(f"❌ 端到端测试失败: {str(e)}")
        print("💡 这可能是正常的，因为需要完整的组件实现。")