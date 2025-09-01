"""
VQE模板函数 - QuantumForge vNext

实现VQE算法的基础模板功能。
"""

from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import Estimator


def run_vqe(hamiltonian, ansatz, optimizer='COBYLA', maxiter=200):
    """
    运行VQE算法计算基态能量
    """
    # 创建优化器
    if optimizer == 'COBYLA':
        opt = COBYLA(maxiter=maxiter)
    else:
        opt = COBYLA(maxiter=maxiter)  # 默认使用COBYLA
    
    # 创建Estimator
    estimator = Estimator()
    
    # 运行VQE
    vqe = VQE(estimator, ansatz, opt)
    result = vqe.compute_minimum_eigenvalue(hamiltonian)
    energy = float(result.eigenvalue.real)
    print(energy)
    return result, energy


def create_cobyla_optimizer(maxiter=200):
    """创建COBYLA优化器"""
    return COBYLA(maxiter=maxiter)


def create_estimator():
    """创建Estimator原语"""
    return Estimator()


if __name__ == "__main__":
    # 简单测试
    opt = create_cobyla_optimizer()
    est = create_estimator()
    print(f"VQE components: optimizer={type(opt).__name__}, estimator={type(est).__name__}")