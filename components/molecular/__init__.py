"""
Molecular Components

分子能量计算组件集合
包含分子模型参数生成器、哈密顿量构建器、VQE线路构建器等组件

支持的分子计算功能:
- 分子几何处理和参数验证
- 电子结构Hamiltonian构建
- 化学启发的VQE ansatz生成
- 初始点管理和优化器配置

使用示例:
    from components.molecular import MolecularModelGenerator
    
    generator = MolecularModelGenerator()
    result = generator.execute(
        query="H2 molecule VQE calculation", 
        params={"atom": "H 0 0 0; H 0 0 0.735", "basis": "sto-3g"}
    )
"""

from .molecular_model_generator import MolecularModelGenerator
from .molecular_hamiltonian_builder import MolecularHamiltonianBuilder

__all__ = ['MolecularModelGenerator', 'MolecularHamiltonianBuilder']