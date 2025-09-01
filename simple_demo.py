#!/usr/bin/env python3
"""
QuantumForge vNext 简单Demo
输入查询 → 自动运行 → 显示结果
"""

from quantum_forge_v5 import run_and_save

def demo():
    # 你的英文查询
    query = "I would like to compute the ground state energy of a 6-qubit transverse-field Ising model (TFIM) with coupling strength J=0.5, transverse field h=1.5, and open boundary conditions"
    
    print("🚀 QuantumForge vNext Demo")
    print(f"📝 查询: {query}")
    print()
    
    # 自动运行
    print("🤖 运行中...")
    code = run_and_save(query, "demo_output.py", debug=False)
    
    print("✅ 完成!")
    print(f"📄 生成代码: demo_output.py ({len(code)}字符)")
    
    # 尝试执行
    try:
        exec(open("demo_output.py").read())
    except Exception as e:
        print(f"ℹ️ 执行需要Qiskit: {e}")

if __name__ == "__main__":
    demo()