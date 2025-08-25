"""
Heisenberg Model Components

量子海森堡模型组件集合
包含Heisenberg模型参数生成器、哈密顿量构建器等组件

支持的Heisenberg模型变种:
- 各向同性 (Jx=Jy=Jz): 经典Heisenberg模型
- XXZ模型 (Jx=Jy≠Jz): 易轴各向异性
- XYZ模型 (Jx≠Jy≠Jz): 完全各向异性
- 外磁场 (hx, hy, hz): 三个方向的外加磁场

使用示例:
    from components.heisenberg import HeisenbergModelGenerator
    
    generator = HeisenbergModelGenerator()
    result = generator.execute(
        query="4-qubit isotropic Heisenberg chain", 
        params={"num_qubits": 4, "J": 1.0}
    )
"""

from .heisenberg_model_generator import HeisenbergModelGenerator
from .heisenberg_hamiltonian_builder import HeisenbergHamiltonianBuilder
from .heisenberg_vqe_circuit_builder import HeisenbergVQECircuitBuilder

__all__ = ['HeisenbergModelGenerator', 'HeisenbergHamiltonianBuilder', 'HeisenbergVQECircuitBuilder']