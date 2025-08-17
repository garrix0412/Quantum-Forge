"""
QuantumForge V4 - Complete Demo
简洁的演示脚本，展示完整的6工具TFIM VQE流程
"""

import sys
import os

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

from orchestrator import IntelligentToolOrchestrator


def demo_quantumforge_v4():
    """演示QuantumForge V4完整功能"""
    print("🧪 QuantumForge V4 - Complete TFIM VQE Demo")
    print("=" * 80)
    
    # 创建编排器
    orchestrator = IntelligentToolOrchestrator()
    
    # 自动加载所有工具
    print("📦 Loading tools...")
    orchestrator.load_all_tools()
    
    # 显示可用工具
    stats = orchestrator.get_execution_stats()
    print(f"✅ Available tools: {len(stats['available_tools'])}")
    for i, tool in enumerate(stats['available_tools'], 1):
        print(f"  {i}. {tool}")
    
    print("\\n" + "=" * 80)
    
    # 演示查询
    query = "Generate complete VQE code file to calculate ground state energy of 4-qubit TFIM with coupling J=1.5"
    
    print(f"🎯 Demo Query:")
    print(f"  '{query}'")
    print()
    print("Expected 6-tool chain:")
    print("  TFIMModelGenerator → TFIMHamiltonianBuilder → TFIMVQECircuitBuilder")
    print("  → TFIMVQEOptimizer → QiskitTFIMExecutor → QiskitCodeAssembler")
    
    print("\\n" + "-" * 80)
    
    try:
        # 执行完整VQE流程
        print("🚀 Executing QuantumForge V4...")
        result = orchestrator.generate_quantum_code(query)
        
        # 显示执行摘要
        print(f"\\n📊 Execution Summary:")
        print(f"  Stop Reason: {result['stop_reason']}")
        print(f"  Total Iterations: {result['iterations']}")
        print(f"  LLM Calls Used: {result['resources_used']['current_calls']}")
        print(f"  Tokens Consumed: {result['resources_used']['current_tokens']}")
        
        # 显示工具链
        execution_history = orchestrator.get_execution_history()
        used_tools = [step['tool_name'] for step in execution_history]
        
        print(f"\\n🔧 Tool Chain Executed:")
        for i, tool in enumerate(used_tools, 1):
            print(f"  {i}. {tool}")
        
        # 分析结果
        print(f"\\n🎯 Results Analysis:")
        
        # 检查是否生成了完整代码
        if result['code']:
            code_length = len(result['code'])
            print(f"  ✅ Generated complete code: {code_length} characters")
            
            # 检查代码特征
            code = result['code']
            features = []
            if "def build_tfim_hamiltonian" in code:
                features.append("TFIM Hamiltonian")
            if "def create_" in code and "ansatz" in code:
                features.append("VQE Ansatz")
            if "VQE(" in code:
                features.append("VQE Algorithm")
            if "compute_minimum_eigenvalue" in code:
                features.append("Energy Calculation")
            if "ground_state_energy" in code:
                features.append("Result Extraction")
            
            print(f"  📋 Code includes: {', '.join(features)}")
        else:
            print(f"  ❌ No code generated")
        
        # 检查文件保存
        final_step = execution_history[-1] if execution_history else None
        if final_step and final_step['tool_name'] == 'QiskitCodeAssembler':
            if 'file_path' in final_step['output']:
                file_path = final_step['output']['file_path']
                if file_path != "not_saved" and file_path != "save_failed":
                    print(f"  💾 Code saved to: {file_path}")
                else:
                    print(f"  ⚠️ File save status: {file_path}")
            else:
                print(f"  ⚠️ No file path information")
        
        # 工具链完整性检查
        expected_tools = [
            'TFIMModelGenerator', 
            'TFIMHamiltonianBuilder', 
            'TFIMVQECircuitBuilder', 
            'TFIMVQEOptimizer',
            'QiskitTFIMExecutor',
            'QiskitCodeAssembler'
        ]
        
        print(f"\\n🔍 Tool Chain Completeness:")
        complete_count = 0
        for tool in expected_tools:
            if tool in used_tools:
                print(f"  ✅ {tool}")
                complete_count += 1
            else:
                print(f"  ❌ {tool} (missing)")
        
        completeness = complete_count / len(expected_tools)
        print(f"\\n📈 Completeness: {complete_count}/{len(expected_tools)} ({completeness:.1%})")
        
        # 最终状态
        if completeness == 1.0:
            print(f"\\n🎉 SUCCESS: Complete 6-tool QuantumForge V4 pipeline executed!")
            print(f"🔬 Ready-to-run VQE code generated and saved!")
        elif completeness >= 0.8:
            print(f"\\n✅ GOOD: Most tools executed successfully")
        else:
            print(f"\\n⚠️ PARTIAL: Some tools missing from execution")
        
        # 显示部分代码预览
        if result['code'] and completeness >= 0.8:
            print(f"\\n📝 Generated Code Preview:")
            lines = result['code'].split('\\n')
            preview_lines = lines[:10] + ['...', f'# ... {len(lines)-10} more lines ...', '...'] + lines[-3:]
            for line in preview_lines:
                print(f"    {line}")
    
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\\n" + "=" * 80)
    print("📋 Demo Complete")
    print("💡 Check generated .py file for complete VQE implementation")
    print("🚀 Ready for quantum computing!")


if __name__ == "__main__":
    demo_quantumforge_v4()