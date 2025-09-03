"""
Helper函数动态加载器 - QuantumForge vNext

从实际helper文件中动态加载函数实现，替代硬编码方案。
"""

import ast
import importlib.util
from pathlib import Path
from typing import List, Tuple, Set, Optional


def _find_helper_files() -> List[Path]:
    """
    自动发现项目中的helper文件
    
    Returns:
        所有helper Python文件的路径列表
    """
    project_root = Path(__file__).parent.parent
    helper_files = []
    
    # 搜索components/helpers目录
    helpers_dir = project_root / "components" / "helpers"
    if helpers_dir.exists():
        helper_files.extend(helpers_dir.glob("*.py"))
    
    # 搜索其他可能的helper目录
    for pattern in ["**/helpers/*.py", "**/helper_*.py", "**/*_helper.py"]:
        helper_files.extend(project_root.glob(pattern))
    
    # 去重并过滤掉__init__.py
    unique_files = []
    seen_files = set()
    for file_path in helper_files:
        if file_path.name != "__init__.py" and file_path not in seen_files:
            unique_files.append(file_path)
            seen_files.add(file_path)
    
    return unique_files


def _extract_function_from_file(file_path: Path, function_name: str) -> Optional[object]:
    """
    从指定文件中提取并加载函数
    
    Args:
        file_path: Python文件路径
        function_name: 要提取的函数名
        
    Returns:
        函数对象，失败时返回None
    """
    try:
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(f"helper_{file_path.stem}", file_path)
        if spec is None or spec.loader is None:
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 检查函数是否存在
        if hasattr(module, function_name):
            return getattr(module, function_name)
        
        return None
    except Exception:
        return None


def load_single_helper(helper_name: str):
    """
    动态加载单个helper函数
    
    Args:
        helper_name: helper函数名
        
    Returns:
        函数对象，失败时返回None
    """
    try:
        # 自动搜索helper文件
        helper_files = _find_helper_files()
        
        for file_path in helper_files:
            func = _extract_function_from_file(file_path, helper_name)
            if func:
                return func
        
        return None
    except Exception:
        return None


def load_helper_functions(helper_stubs: List[str]) -> Tuple[List[str], List[str]]:
    """
    从实际helper文件中加载函数实现
    
    Args:
        helper_stubs: CodegenAgent生成的helper函数stub列表
        
    Returns:
        (包含真实实现的helper函数列表, 需要的导入语句列表)
    """
    # 动态发现helper文件，消除硬编码
    helper_files = _find_helper_files()
    
    # 从stub中提取函数名
    stub_functions = set()
    for stub in helper_stubs:
        if stub.strip().startswith('def '):
            func_name = stub.strip().split('(')[0].replace('def ', '')
            stub_functions.add(func_name)
    
    real_helpers = []
    all_imports: Set[str] = set()
    
    # 从实际文件加载函数
    for func_name in stub_functions:
        function_found = False
        for helper_file in helper_files:
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
                        function_found = True
                        break  # 找到函数后跳出内层循环
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(f"import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            all_imports.add(f"from {module} import {alias.name}")
                            
            except Exception as e:
                print(f"⚠️ 无法加载{func_name}从{helper_file}: {e}")
                continue
            
            if function_found:
                break  # 找到函数后跳出外层循环
    
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