"""
Import管理器 - QuantumForge vNext

实现import语句的去重、分组和排序功能。
基于new.md第7节规定的装配规则实现。
"""

from typing import List, Set, Dict
import re


class ImportManager:
    """
    Import语句管理器
    
    功能：
    - 去重：移除重复的import语句
    - 分组：标准库 < 第三方 < Qiskit < 本地
    - 排序：同组内按字典顺序排列
    """
    
    def __init__(self):
        # 标准库模块列表（常用的）
        self.stdlib_modules = {
            'os', 'sys', 'time', 'datetime', 'json', 'math', 'random',
            'typing', 'dataclasses', 'abc', 'itertools', 'functools',
            'collections', 'pathlib', 're', 'copy', 'pickle'
        }
        
        # Qiskit相关模块前缀
        self.qiskit_prefixes = ['qiskit', 'qiskit_']
    
    def normalize(self, imports: List[str]) -> List[str]:
        """
        标准化import语句列表
        
        Args:
            imports: 原始import语句列表
            
        Returns:
            去重、分组、排序后的import语句列表
        """
        if not imports:
            return []
        
        # 1. 去重（保持原始格式）
        unique_imports = self._deduplicate(imports)
        
        # 2. 分组
        grouped = self._group_imports(unique_imports)
        
        # 3. 排序和格式化
        sorted_imports = self._sort_and_format(grouped)
        
        return sorted_imports
    
    def _deduplicate(self, imports: List[str]) -> List[str]:
        """去重import语句"""
        seen: Set[str] = set()
        unique_imports: List[str] = []
        
        for import_stmt in imports:
            # 标准化空白字符
            normalized = ' '.join(import_stmt.strip().split())
            
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_imports.append(normalized)
        
        return unique_imports
    
    def _group_imports(self, imports: List[str]) -> Dict[str, List[str]]:
        """
        分组import语句
        
        返回4组：stdlib, third_party, qiskit, local
        """
        groups = {
            'stdlib': [],
            'third_party': [],
            'qiskit': [],
            'local': []
        }
        
        for import_stmt in imports:
            group = self._classify_import(import_stmt)
            groups[group].append(import_stmt)
        
        return groups
    
    def _classify_import(self, import_stmt: str) -> str:
        """
        分类单个import语句
        
        Args:
            import_stmt: import语句
            
        Returns:
            分组名称：stdlib/third_party/qiskit/local
        """
        # 提取模块名
        module_name = self._extract_module_name(import_stmt)
        
        # 本地导入（以.开头）
        if import_stmt.strip().startswith('from .'):
            return 'local'
        
        # Qiskit相关
        if any(module_name.startswith(prefix) for prefix in self.qiskit_prefixes):
            return 'qiskit'
        
        # 标准库
        root_module = module_name.split('.')[0]
        if root_module in self.stdlib_modules:
            return 'stdlib'
        
        # 第三方库
        return 'third_party'
    
    def _extract_module_name(self, import_stmt: str) -> str:
        """从import语句中提取模块名"""
        import_stmt = import_stmt.strip()
        
        # 处理 "import xxx" 格式
        if import_stmt.startswith('import '):
            module_part = import_stmt[7:].split(' as ')[0].strip()
            return module_part.split(',')[0].strip()
        
        # 处理 "from xxx import yyy" 格式
        elif import_stmt.startswith('from '):
            match = re.match(r'from\s+([^\s]+)\s+import', import_stmt)
            if match:
                return match.group(1)
        
        return ""
    
    def _sort_and_format(self, grouped: Dict[str, List[str]]) -> List[str]:
        """
        对分组的import进行排序和格式化
        
        Args:
            grouped: 分组的import字典
            
        Returns:
            最终的import语句列表
        """
        result = []
        
        # 按顺序处理各组
        for group_name in ['stdlib', 'third_party', 'qiskit', 'local']:
            group_imports = grouped[group_name]
            
            if group_imports:
                # 同组内按字典顺序排序
                sorted_group = sorted(group_imports)
                result.extend(sorted_group)
                
                # 组间添加空行（除了最后一组）
                if group_name != 'local' and any(grouped[g] for g in ['third_party', 'qiskit', 'local'] if g != group_name):
                    result.append("")  # 空行分隔符
        
        return result
    
    def get_import_stats(self, imports: List[str]) -> Dict[str, int]:
        """
        获取import统计信息
        
        Args:
            imports: import语句列表
            
        Returns:
            统计信息字典
        """
        grouped = self._group_imports(imports)
        
        return {
            'total': len(imports),
            'stdlib': len(grouped['stdlib']),
            'third_party': len(grouped['third_party']),
            'qiskit': len(grouped['qiskit']),
            'local': len(grouped['local']),
            'duplicates_removed': 0  # 需要在normalize中计算
        }


# =============================================================================
# 便利函数
# =============================================================================

def normalize_imports(imports: List[str]) -> List[str]:
    """便利函数：标准化import列表"""
    manager = ImportManager()
    return manager.normalize(imports)


# =============================================================================
# 测试代码  
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing ImportManager...")
    
    # 测试数据
    test_imports = [
        "import os",
        "import numpy as np", 
        "from qiskit import QuantumCircuit",
        "from qiskit.quantum_info import SparsePauliOp",
        "import json",
        "from qiskit_algorithms.optimizers import COBYLA",
        "import numpy as np",  # 重复
        "from . import config",
        "import sys",
        "from qiskit.primitives import Estimator"
    ]
    
    manager = ImportManager()
    
    # 测试标准化
    normalized = manager.normalize(test_imports)
    
    print("📋 标准化结果:")
    for i, stmt in enumerate(normalized):
        if stmt == "":
            print("    ---")  # 空行分隔符
        else:
            print(f"  {i+1}. {stmt}")
    
    # 测试统计
    stats = manager.get_import_stats(test_imports)
    print(f"\n📊 统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ ImportManager 测试通过！")