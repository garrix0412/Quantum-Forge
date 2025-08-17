# QuantumForge V4 Intelligent

LLM驱动的智能量子代码生成器

## 使用方法

```python
from core.orchestrator import IntelligentToolOrchestrator

orchestrator = IntelligentToolOrchestrator()
code = orchestrator.generate_quantum_code("Generate VQE code for 4-qubit TFIM model")
print(code)
```

## 项目结构

- `core/` - 核心架构组件
- `tools/` - 量子计算工具
- `tests/` - 测试文件
- `examples/` - 使用示例