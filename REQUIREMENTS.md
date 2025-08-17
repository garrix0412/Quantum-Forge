# QuantumForge V4 智能量子代码生成器 - 需求文档

## 📋 项目概述

**项目名称**: QuantumForge V4 Intelligent Quantum Code Generator  
**版本**: 2.0 (完全重构版本)  
**目标**: 通过自然语言输入生成完整可执行的量子计算代码

## 🎯 核心需求

### **用户体验需求**
- **输入**: 英文自然语言描述
  - 示例: `"Generate VQE code for 4-qubit TFIM model with coupling strength 1.5"`
- **输出**: 完整可执行的Python量子代码
  - **重要**: 只输出代码定义，不包含执行结果或打印语句
  - 用户自己负责运行和验证代码
- **交互**: 最简洁的界面，隐藏所有中间处理过程

### **技术架构需求**

#### **1. LLM驱动的智能工具编排**
```
用户查询 → LLM分析任务 → LLM选择工具 → LLM决定执行顺序 → 逐步执行
```

**核心特性**:
- **动态工具选择**: LLM根据任务智能选择需要的工具
- **动态执行顺序**: LLM决定工具的执行顺序，不是固定的
- **步进式执行**: 每执行一个工具后，LLM评估是否继续执行下一个
- **智能停止**: LLM判断任务完成时自动停止

#### **2. 完整Memory历史系统**
```python
Memory功能需求:
- 存储每个工具的完整输出
- 为后续工具提供所有历史上下文
- 支持智能上下文提取和压缩
- 跟踪完整的执行历史和状态变化
```

#### **3. 工具链架构**
**当前专注**: TFIM + VQE + Qiskit工具链 (6个工具)
1. `TFIMModelGenerator` - 生成TFIM模型参数
2. `TFIMHamiltonianBuilder` - 构建哈密顿量代码
3. `TFIMVQECircuitBuilder` - 构建VQE电路代码
4. `TFIMVQEOptimizer` - 生成优化器代码
5. `QiskitTFIMExecutor` - 生成VQE执行代码
6. `QiskitCodeAssembler` - 组装完整可执行代码

#### **4. 扩展性需求**
- **框架扩展**: 支持未来扩展到Cirq, PennyLane等
- **模型扩展**: 支持未来扩展到Heisenberg, Hubbard等模型
- **算法扩展**: 支持未来扩展到QAOA, QML等算法
- **工具插件化**: 新工具可以轻松注册和被LLM自动使用

## 🏗️ 架构设计决策

### **已确认的设计决策**

#### ✅ **核心架构模式**
- **LLM驱动**: 每个关键决策点都由LLM智能判断
- **串行执行**: 不需要并行优化，按顺序执行工具
- **Memory传递**: 通过完整Memory在工具间传递上下文

#### ✅ **工具设计模式**
- **每个工具调用LLM**: 基于Memory历史生成高质量代码片段
- **专家角色定位**: 每个工具是特定领域的LLM专家
- **代码片段输出**: 工具输出代码片段，不是数据结构

#### ✅ **错误处理策略**
- **简单直接**: 错误直接报告给用户，不做自动恢复
- **失败快速**: 任何工具失败时立即停止，不继续执行

#### ✅ **性能要求**
- **串行处理**: 不需要并行化，简单的顺序执行
- **响应时间**: 用户可以等待几十秒生成高质量代码
- **成本控制**: 通过prompt优化控制LLM调用成本

### **明确拒绝的设计**
❌ 复杂的错误恢复机制  
❌ 性能并行化优化  
❌ 复杂的监控和统计  
❌ 代码执行和结果计算  
❌ 结果验证和质量检查  
❌ 用户界面美化和体验优化  

## 🎯 功能需求详解

### **1. IntelligentToolOrchestrator (核心)**
```python
class IntelligentToolOrchestrator:
    def generate_quantum_code(self, query: str) -> str:
        """主入口函数"""
        
    def _llm_select_next_tool(self) -> Optional[BaseTool]:
        """LLM选择下一个执行的工具"""
        
    def _llm_evaluate_progress(self) -> bool:
        """LLM评估是否继续执行"""
```

**职责**:
- 接收用户自然语言查询
- 调用LLM分析任务需求
- 动态选择和排序工具
- 逐步执行工具链
- 返回最终完整代码

### **2. Memory系统**
```python
class Memory:
    def add_tool_output(self, tool_name: str, output: dict):
        """添加工具输出到历史"""
        
    def get_context_for_tool(self, tool_name: str) -> str:
        """为特定工具提取相关上下文"""
        
    def get_final_code(self) -> str:
        """获取最终生成的代码"""
```

**职责**:
- 存储完整的工具执行历史
- 智能提取相关上下文给LLM
- 管理代码片段的积累
- 提供最终代码组装

### **3. 工具基类和注册**
```python
class BaseTool(ABC):
    def execute(self, memory: Memory) -> dict:
        """执行工具，基于Memory历史"""
        
class ToolRegistry:
    def register(self, name: str, tool_class: Type[BaseTool]):
        """注册工具"""
        
    def get_tool_descriptions(self) -> Dict[str, str]:
        """获取工具描述供LLM选择"""
```

**职责**:
- 提供统一的工具接口
- 支持工具的动态注册和发现
- 为LLM提供工具选择信息

### **4. LLM集成接口**
```python
def call_llm(prompt: str, **kwargs) -> str:
    """统一的LLM调用接口"""
```

**职责**:
- 统一的LLM调用管理
- Prompt模板和优化
- 错误处理和重试

## 📁 目标文件结构

```
quantumforge_v4_intelligent/
├── README.md                    # 项目说明
├── REQUIREMENTS.md              # 本需求文档
├── main.py                      # 主入口
├── core/
│   ├── __init__.py
│   ├── orchestrator.py          # IntelligentToolOrchestrator
│   ├── memory.py               # Memory系统
│   └── llm_engine.py           # LLM调用接口
├── tools/
│   ├── __init__.py
│   ├── base_tool.py            # BaseTool基类
│   ├── registry.py             # 工具注册系统
│   └── tfim/
│       ├── __init__.py
│       ├── tfim_model_generator.py
│       ├── tfim_hamiltonian_builder.py
│       ├── tfim_vqe_circuit_builder.py
│       ├── tfim_vqe_optimizer.py
│       ├── qiskit_tfim_executor.py
│       └── qiskit_code_assembler.py
├── tests/
│   ├── test_orchestrator.py
│   ├── test_memory.py
│   └── test_tools.py
└── examples/
    └── example_usage.py
```

## 🚀 实施计划

### **阶段1: 核心架构 (优先级: 🔴 高)**
- [ ] 实现 `IntelligentToolOrchestrator`
- [ ] 实现 `Memory` 完整历史系统
- [ ] 实现统一的 LLM 调用接口
- [ ] 基础的工具注册系统

### **阶段2: 工具实现 (优先级: 🔴 高)**
- [ ] 重构 `BaseTool` 接口 (简化版)
- [ ] 实现6个TFIM工具链
- [ ] 修改工具输出格式为代码片段
- [ ] 确保最终代码不包含执行部分

### **阶段3: 集成测试 (优先级: 🟡 中)**
- [ ] 端到端测试用例
- [ ] LLM工具选择准确性测试
- [ ] Memory上下文传递测试
- [ ] 最终代码质量验证

### **阶段4: 优化和文档 (优先级: 🟢 低)**
- [ ] Prompt优化和成本控制
- [ ] 使用文档和示例
- [ ] 代码注释和API文档

## 🧪 验收标准

### **功能验收**
✅ 用户输入: `"Generate VQE code for 4-qubit TFIM model"`  
✅ 系统输出: 完整的Qiskit VQE代码，可直接运行  
✅ 代码不包含: `result.run()`, `print()` 等执行语句  
✅ LLM智能选择合适的工具和执行顺序  
✅ Memory正确传递所有历史上下文  

### **技术验收**
✅ 架构支持扩展新框架(Cirq, PennyLane)  
✅ 架构支持扩展新模型(Heisenberg, Hubbard)  
✅ 工具注册系统支持动态添加工具  
✅ LLM能够自动发现和使用新注册的工具  
✅ 错误信息清晰，便于调试  

### **性能验收**
✅ 单次查询生成代码时间 < 2分钟  
✅ LLM调用成本在可接受范围内  
✅ Memory系统不会内存泄漏  
✅ 代码生成成功率 > 80%  

## 🚨 风险和约束

### **技术风险**
- **LLM API稳定性**: 依赖外部LLM服务的可用性
- **Prompt质量**: LLM工具选择和代码生成的准确性
- **Memory复杂度**: 大型项目中Memory可能过于庞大

### **项目约束**
- **只支持英文**: 不考虑多语言支持
- **只输出代码**: 不负责代码执行和结果验证
- **单一任务**: 一次只处理一个代码生成任务

### **成本约束**
- **LLM调用成本**: 需要控制在合理范围内
- **开发时间**: 重构时间不超过2周
- **维护成本**: 保持代码简单易维护

## 📈 成功指标

### **用户满意度**
- 生成代码的可用性和正确性
- 用户学习和使用的便捷性
- 相比手工编写的效率提升

### **技术指标**
- 代码生成成功率
- LLM工具选择准确率
- 系统响应时间
- 扩展性验证

---

**文档版本**: 1.0  
**创建日期**: 2024-08-16  
**最后更新**: 2024-08-16  
**下次评审**: 实现阶段1后