"""
代码优化器 - QuantumForge vNext

提供代码生成后的智能优化功能：
- 重复逻辑检测和合并
- main()函数签名优化
- Import语句智能优化
- 函数重命名和冲突解决
"""

import re
import ast
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict


class CodeOptimizer:
    """
    代码优化器
    
    对生成的CodeCells进行智能优化，提高代码质量和可读性
    """
    
    def __init__(self, debug: bool = False):
        """
        初始化代码优化器
        
        Args:
            debug: 是否启用调试输出
        """
        self.debug = debug
        self.optimization_stats = {
            "functions_merged": 0,
            "imports_optimized": 0,
            "params_removed": 0,
            "conflicts_resolved": 0
        }
    
    def optimize_code_cells(self, code_cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        优化CodeCells列表
        
        Args:
            code_cells: 原始CodeCell列表
            
        Returns:
            优化后的CodeCell列表
        """
        self._debug_print("🔧 开始代码优化...")
        
        # 1. 检测和合并重复函数
        optimized_cells = self._deduplicate_functions(code_cells)
        
        # 2. 优化import语句
        optimized_cells = self._optimize_imports(optimized_cells)
        
        # 3. 清理未使用的定义
        optimized_cells = self._remove_unused_definitions(optimized_cells)
        
        self._debug_print(f"✅ 代码优化完成: {self.optimization_stats}")
        
        return optimized_cells
    
    def optimize_main_signature(
        self, 
        used_params: Set[str], 
        all_params: Dict[str, Any], 
        defaults: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        优化main()函数签名
        
        Args:
            used_params: 实际使用的参数集合
            all_params: 所有可用参数
            defaults: 默认值映射
            
        Returns:
            (parameter_list, optimized_defaults) 元组
        """
        self._debug_print("🎯 优化main()函数签名...")
        
        # 按重要性和使用频率排序参数
        param_priority = {
            'n': 1, 'hx': 2, 'j': 3, 'reps': 4, 'optimizer': 5,
            'maxiter': 6, 'shots': 7, 'boundary': 8, 'seed': 9
        }
        
        # 只包含实际使用的参数
        used_param_list = []
        optimized_defaults = {}
        
        # 按优先级排序
        sorted_params = sorted(
            used_params,
            key=lambda p: param_priority.get(p, 999)
        )
        
        for param in sorted_params:
            if param in all_params:
                param_type = self._infer_param_type(all_params[param])
                default_value = defaults.get(param)
                
                if default_value is not None:
                    used_param_list.append(f"{param}: {param_type} = {repr(default_value)}")
                    optimized_defaults[param] = default_value
                else:
                    used_param_list.append(f"{param}: {param_type}")
        
        removed_count = len(all_params) - len(used_param_list)
        if removed_count > 0:
            self.optimization_stats["params_removed"] += removed_count
            self._debug_print(f"🗑️ 移除未使用参数: {removed_count}个")
        
        return used_param_list, optimized_defaults
    
    def _deduplicate_functions(self, code_cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测和合并重复函数"""
        self._debug_print("🔍 检测重复函数...")
        
        function_signatures = defaultdict(list)
        optimized_cells = []
        
        # 分析所有函数签名
        for cell in code_cells:
            cell_copy = cell.copy()
            helpers = cell.get('helpers', [])
            
            if helpers:
                # 提取函数签名
                for helper in helpers:
                    signature = self._extract_function_signature(helper)
                    if signature:
                        function_signatures[signature].append((cell['id'], helper))
            
            optimized_cells.append(cell_copy)
        
        # 处理重复函数
        for signature, instances in function_signatures.items():
            if len(instances) > 1:
                self._debug_print(f"🔄 发现重复函数: {signature} (出现{len(instances)}次)")
                self.optimization_stats["functions_merged"] += len(instances) - 1
                
                # 保留第一个实例，移除其他重复
                keep_cell_id = instances[0][0]
                for i, (cell_id, _) in enumerate(instances[1:], 1):
                    # 在对应的cell中移除重复函数
                    for cell in optimized_cells:
                        if cell['id'] == cell_id:
                            cell['helpers'] = [h for h in cell.get('helpers', []) if not self._same_function(h, instances[0][1])]
        
        return optimized_cells
    
    def _optimize_imports(self, code_cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化import语句"""
        self._debug_print("📦 优化import语句...")
        
        # 收集所有import
        all_imports = set()
        for cell in code_cells:
            for imp in cell.get('imports', []):
                all_imports.add(imp)
        
        # 检测可以合并的import
        optimized_imports = self._merge_imports(list(all_imports))
        
        if len(optimized_imports) < len(all_imports):
            saved_count = len(all_imports) - len(optimized_imports)
            self.optimization_stats["imports_optimized"] += saved_count
            self._debug_print(f"📉 合并import语句: 减少{saved_count}个")
        
        # 更新所有cells使用优化后的imports
        optimized_cells = []
        for cell in code_cells:
            cell_copy = cell.copy()
            # 只在第一个cell中包含所有imports
            if cell == code_cells[0]:
                cell_copy['imports'] = optimized_imports
            else:
                cell_copy['imports'] = []  # 其他cells清空imports避免重复
            optimized_cells.append(cell_copy)
        
        return optimized_cells
    
    def _remove_unused_definitions(self, code_cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """移除未使用的定义"""
        self._debug_print("🧹 清理未使用的定义...")
        
        # 收集所有函数定义和调用
        defined_functions = set()
        called_functions = set()
        
        for cell in code_cells:
            # 收集定义的函数
            for helper in cell.get('helpers', []):
                func_name = self._extract_function_name(helper)
                if func_name:
                    defined_functions.add(func_name)
            
            # 收集调用的函数
            invoke_code = cell.get('invoke', '')
            called_functions.update(self._extract_function_calls(invoke_code))
        
        # 移除未使用的函数
        unused_functions = defined_functions - called_functions
        
        if unused_functions:
            self._debug_print(f"🗑️ 发现未使用函数: {unused_functions}")
            
            optimized_cells = []
            for cell in code_cells:
                cell_copy = cell.copy()
                cell_copy['helpers'] = [
                    helper for helper in cell.get('helpers', [])
                    if self._extract_function_name(helper) not in unused_functions
                ]
                optimized_cells.append(cell_copy)
            
            return optimized_cells
        
        return code_cells
    
    # =============================================================================
    # 辅助方法
    # =============================================================================
    
    def _extract_function_signature(self, function_code: str) -> Optional[str]:
        """提取函数签名"""
        try:
            # 使用正则表达式提取函数定义
            match = re.search(r'def\s+(\w+)\s*\([^)]*\)', function_code)
            if match:
                return match.group(0)
        except:
            pass
        return None
    
    def _extract_function_name(self, function_code: str) -> Optional[str]:
        """提取函数名"""
        try:
            match = re.search(r'def\s+(\w+)\s*\(', function_code)
            if match:
                return match.group(1)
        except:
            pass
        return None
    
    def _extract_function_calls(self, code: str) -> Set[str]:
        """提取代码中的函数调用"""
        function_calls = set()
        try:
            # 使用正则表达式查找函数调用
            matches = re.findall(r'(\w+)\s*\(', code)
            function_calls.update(matches)
        except:
            pass
        return function_calls
    
    def _same_function(self, func1: str, func2: str) -> bool:
        """检查两个函数是否相同"""
        # 简单的字符串比较（可以改进为AST比较）
        normalized1 = re.sub(r'\s+', ' ', func1.strip())
        normalized2 = re.sub(r'\s+', ' ', func2.strip())
        return normalized1 == normalized2
    
    def _merge_imports(self, imports: List[str]) -> List[str]:
        """合并可以合并的import语句"""
        # 按模块分组import
        grouped_imports = defaultdict(list)
        standalone_imports = []
        
        for imp in imports:
            if imp.startswith('from '):
                # from module import item1, item2
                match = re.match(r'from\s+([\w.]+)\s+import\s+(.+)', imp)
                if match:
                    module, items = match.groups()
                    grouped_imports[module].extend([item.strip() for item in items.split(',')])
                else:
                    standalone_imports.append(imp)
            else:
                standalone_imports.append(imp)
        
        # 生成合并后的imports
        merged_imports = []
        
        # 先添加standalone imports
        merged_imports.extend(sorted(set(standalone_imports)))
        
        # 添加合并的from imports
        for module, items in sorted(grouped_imports.items()):
            unique_items = sorted(set(items))
            if len(unique_items) == 1:
                merged_imports.append(f"from {module} import {unique_items[0]}")
            else:
                merged_imports.append(f"from {module} import {', '.join(unique_items)}")
        
        return merged_imports
    
    def _infer_param_type(self, value: Any) -> str:
        """推断参数类型"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "str"
        elif value is None:
            return "Optional[Any]"
        else:
            return "Any"
    
    def _debug_print(self, message: str) -> None:
        """调试输出"""
        if self.debug:
            print(message)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return self.optimization_stats.copy()


# =============================================================================
# 便利函数
# =============================================================================

def create_optimizer(debug: bool = False) -> CodeOptimizer:
    """
    创建代码优化器实例
    
    Args:
        debug: 是否启用调试输出
        
    Returns:
        CodeOptimizer实例
    """
    return CodeOptimizer(debug=debug)


# =============================================================================
# 测试代码  
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing CodeOptimizer...")
    
    optimizer = create_optimizer(debug=True)
    
    # 测试重复函数检测
    test_cells = [
        {
            "id": "cell1",
            "imports": ["from qiskit import QuantumCircuit", "import numpy as np"],
            "helpers": ["def test_func():\n    return 42"],
            "invoke": "result1 = test_func()",
            "exports": {"result": "result1"}
        },
        {
            "id": "cell2", 
            "imports": ["from qiskit import QuantumCircuit", "from qiskit.quantum_info import SparsePauliOp"],
            "helpers": ["def test_func():\n    return 42"],  # 重复函数
            "invoke": "result2 = test_func()",
            "exports": {"result": "result2"}
        }
    ]
    
    print("\n🔍 测试重复函数检测:")
    optimized_cells = optimizer.optimize_code_cells(test_cells)
    
    # 验证优化结果
    all_helpers = []
    for cell in optimized_cells:
        all_helpers.extend(cell.get('helpers', []))
    
    test_func_count = sum(1 for helper in all_helpers if 'def test_func' in helper)
    print(f"优化前test_func出现次数: 2")
    print(f"优化后test_func出现次数: {test_func_count}")
    
    if test_func_count == 1:
        print("✅ 重复函数合并成功")
    else:
        print("❌ 重复函数合并失败")
    
    # 测试main函数签名优化
    print("\n🎯 测试main函数签名优化:")
    used_params = {"n", "hx", "optimizer"}
    all_params = {"n": 4, "hx": 1.0, "j": 1.0, "optimizer": "COBYLA", "unused_param": "value"}
    defaults = {"optimizer": "COBYLA", "j": 1.0}
    
    param_list, opt_defaults = optimizer.optimize_main_signature(used_params, all_params, defaults)
    
    print(f"优化后参数列表: {param_list}")
    print(f"优化后默认值: {opt_defaults}")
    
    # 验证未使用参数被移除
    if "unused_param" not in " ".join(param_list):
        print("✅ 未使用参数移除成功")
    else:
        print("❌ 未使用参数移除失败")
    
    print(f"\n📊 优化统计: {optimizer.get_optimization_stats()}")
    print("\n🎉 CodeOptimizer测试完成！")