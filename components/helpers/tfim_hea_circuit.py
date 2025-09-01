"""
TFIM HEA电路构建器 - QuantumForge vNext

实现TFIM的硬件高效ansatz电路。
"""

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter


def tfim_hea(n, reps):
    """
    构建TFIM硬件高效ansatz
    
    层结构: RY旋转 + CNOT纠缠
    """
    qc = QuantumCircuit(n)
    
    for rep in range(reps):
        # RY旋转层
        for i in range(n):
            theta = Parameter(f'theta_{rep}_{i}')
            qc.ry(theta, i)
        
        # CNOT纠缠层
        for i in range(n):
            qc.cx(i, (i + 1) % n)
    
    return qc


if __name__ == "__main__":
    # 简单测试
    ansatz = tfim_hea(4, 2)
    print(f"TFIM_HEA(4,2): {ansatz.num_parameters} params")