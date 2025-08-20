"""
端到端系统测试 - QuantumForge V5
测试从用户自然语言查询到完整可执行代码的完整流程
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from core.quantum_forge_v5 import QuantumForgeV5


def test_end_to_end_user_experience():
    """测试真实用户体验 - 从查询到完整代码"""
    print("🎯 End-to-End System Test: Real User Experience")
    print("=" * 80)
    print("Testing: User Query → QuantumForge V5 → Complete Executable Code")
    print("=" * 80)
    
    try:
        # 初始化QuantumForge V5
        print("🚀 Initializing QuantumForge V5...")
        qf5 = QuantumForgeV5()
        
        # 显示系统状态
        system_info = qf5.get_system_info()
        print(f"✅ System Ready: {system_info['system_ready']}")
        print(f"📦 Available Components: {system_info['total_components']}")
        print(f"🧠 Model: {system_info['model']}")
        
        # 真实用户查询测试用例
        user_test_cases = [
            {
                "query": "Create a VQE simulation for 4-qubit Heisenberg model with coupling J=2.0 and field h=0.5",               
            }
            # {
            #     "query": "Create a VQE simulation for 6-qubit Heisenberg model with real amplitudes ansatz and L_BFGS_B optimization",
            # },
            # {
            #     "query": "Generate quantum code for TFIM ground state calculation using VQE algorithm, 6 qubits, open boundary",
            # }
        ]
        
        successful_tests = 0
        total_tests = len(user_test_cases)
        generated_files = []
        
        for i, test_case in enumerate(user_test_cases, 1):
            # name = test_case["name"]
            query = test_case["query"]
            # expected = test_case["expected_keywords"]
            
            # print(f"\n🧪 Test {i}/{total_tests}: {name}")
            print(f"📝 User Query: \"{query}\"")
            print("-" * 60)
            
            try:
                # 执行端到端生成
                generated_file = qf5.generate_quantum_code(query)                                
                generated_files.append(generated_file)
                    
            except Exception as e:
                print(f"❌ Test Execution Error: {e}")
                print(f"🎯 Test Result: FAILED ❌")
        
        return successful_tests, total_tests, generated_files
        
    except Exception as e:
        print(f"❌ System Initialization Failed: {e}")
        print("💡 Please check:")
        print("  • OPENAI_API_KEY environment variable") 
        print("  • Component imports and dependencies")
        print("  • File permissions for code generation")
        return 0, 0, []

if __name__ == "__main__":
    print("🚀 QuantumForge V5 End-to-End System Testing")
    print("Testing real user experience from query to executable code")
    print("=" * 80)
    
    # 执行端到端测试
    successful_tests, total_tests, generated_files = test_end_to_end_user_experience()

