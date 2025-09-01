"""
Helper函数动态加载器 - QuantumForge vNext

从实际helper文件中动态加载函数实现，替代硬编码方案。
"""

import ast
from pathlib import Path
from typing import List, Tuple, Set


def load_helper_functions(helper_stubs: List[str]) -> Tuple[List[str], List[str]]:
    """
    从实际helper文件中加载函数实现
    
    Args:
        helper_stubs: CodegenAgent生成的helper函数stub列表
        
    Returns:
        (包含真实实现的helper函数列表, 需要的导入语句列表)
    """
    # helper文件映射
    helper_file_map = {
        'build_tfim_h': 'components/helpers/tfim_hamiltonian.py',
        'tfim_hea': 'components/helpers/tfim_hea_circuit.py', 
        'run_vqe': 'components/helpers/vqe_templates.py',
        'create_cobyla_optimizer': 'components/helpers/vqe_templates.py',
        'create_estimator': 'components/helpers/vqe_templates.py'
    }
    
    # 从stub中提取函数名
    stub_functions = set()
    for stub in helper_stubs:
        if stub.strip().startswith('def '):
            func_name = stub.strip().split('(')[0].replace('def ', '')
            stub_functions.add(func_name)
    
    real_helpers = []
    all_imports: Set[str] = set()
    project_root = Path(__file__).parent.parent
    
    # 从实际文件加载函数
    for func_name in stub_functions:
        if func_name in helper_file_map:
            helper_file = project_root / helper_file_map[func_name]
            if helper_file.exists():
                try:
                    with open(helper_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 解析AST
                    tree = ast.parse(content)
                    
                    # 提取函数定义和导入
                    for node in tree.body:
                        if isinstance(node, ast.FunctionDef) and node.name == func_name:
                            # 重新生成函数代码
                            func_code = ast.unparse(node)
                            real_helpers.append(func_code)
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                all_imports.add(f"import {alias.name}")
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module or ""
                            for alias in node.names:
                                all_imports.add(f"from {module} import {alias.name}")
                                
                except Exception as e:
                    print(f"⚠️ 无法加载{func_name}从{helper_file}: {e}")
                    # 如果加载失败，继续处理其他函数
                    continue
    
    helper_imports = list(all_imports)
    return real_helpers, helper_imports


if __name__ == "__main__":
    # 测试helper加载器
    test_stubs = [
        "def build_tfim_h(n, hx, j, boundary):",
        "def tfim_hea(n, reps):",
        "def run_vqe(hamiltonian, ansatz, optimizer, maxiter):"
    ]
    
    helpers, imports = load_helper_functions(test_stubs)
    print(f"✅ 加载了{len(helpers)}个helper函数")
    print(f"🔗 需要{len(imports)}个导入语句")
    
    for i, helper in enumerate(helpers):
        print(f"\n📦 Helper {i+1}:")
        print(helper[:100] + "...")