"""
JSON Schema数据结构定义 - QuantumForge vNext

基于new.md规格实现的核心数据结构：
- TaskCard: 任务卡（语义理解结果）
- ComponentCard: 组件卡（组件描述）
- ParamMap: 参数映射（别名统一化）
- PipelinePlan: 流水线计划（执行顺序）
- CodeCell: 代码单元（生成片段）

所有数据结构都是纯JSON，支持序列化和验证。
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import json


@dataclass
class TaskCard:
    """
    任务卡 - 语义理解的结构化结果
    
    由SemanticAgent从自然语言query生成
    """
    domain: str                    # "spin" | "chemistry" | "optimization" | "custom"
    problem: str                   # 自由命名：如 "tfim_ground_energy"
    algorithm: str                 # "vqe" | "qaoa" | "qpe" | "vqd" | "vqls" | ...
    backend: str                   # "qiskit"
    params: Dict[str, Any]         # 用户参数和系统参数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskCard':
        """从字典创建"""
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TaskCard':
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ComponentCard:
    """
    组件卡 - 单个组件的完整描述
    
    从registry.json读取，由DiscoveryAgent筛选返回
    """
    name: str                      # "Hamiltonian.TFIM"
    kind: str                      # "hamiltonian" | "ansatz" | "primitive" | "optimizer" | "algorithm" | "reporter"
    tags: List[str]                # ["spin", "tfim"]
    needs: List[str]               # 上游需求：[] 表示源头组件
    provides: List[str]            # ["hamiltonian:pauli_op"]
    params_schema: Dict[str, Union[str, List[str]]]  # {"n": "int", "boundary": ["periodic", "open"]}
    yields: Dict[str, str]         # {"hamiltonian": "SparsePauliOp"}
    codegen_hint: Dict[str, Any]   # 代码生成提示
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentCard':
        """从字典创建"""
        return cls(**data)
    
    def is_source(self) -> bool:
        """是否为源头组件（无上游依赖）"""
        return len(self.needs) == 0
    
    def can_satisfy(self, need: str) -> bool:
        """是否能满足指定需求"""
        return need in self.provides


@dataclass
class ParamMap:
    """
    参数映射 - 别名统一化和默认值注入
    
    由ParamNormAgent生成，用于参数标准化
    """
    aliases: Dict[str, str]        # {"num_qubits": "n", "h_x": "hx"}
    defaults: Dict[str, Any]       # {"optimizer": "COBYLA", "reps": 2}
    validated: List[str]           # ["n", "hx", "j", "reps", "optimizer"]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParamMap':
        """从字典创建"""
        return cls(**data)
    
    def resolve_alias(self, param_name: str) -> str:
        """解析别名到标准参数名"""
        return self.aliases.get(param_name, param_name)
    
    def get_default(self, param_name: str) -> Any:
        """获取参数默认值"""
        return self.defaults.get(param_name)


@dataclass
class PipelineStep:
    """
    流水线步骤 - 单个组件的执行配置
    """
    use: str                       # 组件名："Hamiltonian.TFIM"
    with_params: Dict[str, str]    # 参数绑定：{"n": "$n", "hx": "$hx"}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {"use": self.use, "with": self.with_params}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineStep':
        """从字典创建"""
        return cls(use=data["use"], with_params=data["with"])


@dataclass
class PipelinePlan:
    """
    流水线计划 - 组件执行的线性顺序
    
    由PipelineAgent通过拓扑排序生成
    """
    steps: List[PipelineStep]      # 执行步骤列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {"steps": [step.to_dict() for step in self.steps]}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelinePlan':
        """从字典创建"""
        steps = [PipelineStep.from_dict(step_data) for step_data in data["steps"]]
        return cls(steps=steps)
    
    def get_component_order(self) -> List[str]:
        """获取组件执行顺序"""
        return [step.use for step in self.steps]
    
    def get_step_params(self, component_name: str) -> Optional[Dict[str, str]]:
        """获取指定组件的参数配置"""
        for step in self.steps:
            if step.use == component_name:
                return step.with_params
        return None


@dataclass
class CodeCell:
    """
    代码单元 - 单个组件生成的代码片段
    
    由CodegenAgent生成，存储在Memory中
    """
    id: str                        # 唯一标识："ham_tfim"
    imports: List[str]             # import语句列表
    helpers: List[str]             # 辅助函数定义
    definitions: List[str]         # 变量/常量定义
    invoke: str                    # 执行语句
    exports: Dict[str, str]        # {"hamiltonian": "H"}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeCell':
        """从字典创建"""
        return cls(**data)
    
    def has_exports(self) -> bool:
        """是否有导出变量"""
        return len(self.exports) > 0
    
    def get_exported_vars(self) -> List[str]:
        """获取导出变量列表"""
        return list(self.exports.values())


# =============================================================================
# 验证和工具函数
# =============================================================================

def validate_task_card(data: Dict[str, Any]) -> bool:
    """验证TaskCard数据格式"""
    required_fields = ["domain", "problem", "algorithm", "backend", "params"]
    
    # 检查必需字段
    for required_field in required_fields:
        if required_field not in data:
            return False
    
    # 检查枚举值
    valid_domains = ["spin", "chemistry", "optimization", "custom"]
    if data["domain"] not in valid_domains:
        return False
    
    # 检查params是字典
    if not isinstance(data["params"], dict):
        return False
    
    return True


def validate_component_card(data: Dict[str, Any]) -> bool:
    """验证ComponentCard数据格式"""
    required_fields = ["name", "kind", "tags", "needs", "provides", "params_schema", "yields", "codegen_hint"]
    
    # 检查必需字段
    for required_field in required_fields:
        if required_field not in data:
            return False
    
    # 检查列表字段
    list_fields = ["tags", "needs", "provides"]
    for list_field in list_fields:
        if not isinstance(data[list_field], list):
            return False
    
    # 检查字典字段
    dict_fields = ["params_schema", "yields", "codegen_hint"]
    for dict_field in dict_fields:
        if not isinstance(data[dict_field], dict):
            return False
    
    return True


def validate_param_map(data: Dict[str, Any]) -> bool:
    """验证ParamMap数据格式"""
    required_fields = ["aliases", "defaults", "validated"]
    
    # 检查必需字段
    for required_field in required_fields:
        if required_field not in data:
            return False
    
    # 检查字典字段
    if not isinstance(data["aliases"], dict) or not isinstance(data["defaults"], dict):
        return False
    
    # 检查列表字段
    if not isinstance(data["validated"], list):
        return False
    
    return True


def validate_pipeline_plan(data: Dict[str, Any]) -> bool:
    """验证PipelinePlan数据格式"""
    if "steps" not in data or not isinstance(data["steps"], list):
        return False
    
    # 检查每个步骤格式
    for step in data["steps"]:
        if not isinstance(step, dict):
            return False
        if "use" not in step or "with" not in step:
            return False
        if not isinstance(step["with"], dict):
            return False
    
    return True


def validate_code_cell(data: Dict[str, Any]) -> bool:
    """验证CodeCell数据格式"""
    required_fields = ["id", "imports", "helpers", "definitions", "invoke", "exports"]
    
    # 检查必需字段
    for required_field in required_fields:
        if required_field not in data:
            return False
    
    # 检查列表字段
    list_fields = ["imports", "helpers", "definitions"]
    for list_field in list_fields:
        if not isinstance(data[list_field], list):
            return False
    
    # 检查字符串字段
    if not isinstance(data["invoke"], str):
        return False
    
    # 检查exports字典
    if not isinstance(data["exports"], dict):
        return False
    
    return True


# =============================================================================
# 便利函数
# =============================================================================

def create_empty_task_card() -> TaskCard:
    """创建空的TaskCard"""
    return TaskCard(
        domain="spin",
        problem="",
        algorithm="vqe", 
        backend="qiskit",
        params={}
    )


def create_empty_param_map() -> ParamMap:
    """创建空的ParamMap"""
    return ParamMap(
        aliases={},
        defaults={},
        validated=[]
    )


def create_empty_pipeline_plan() -> PipelinePlan:
    """创建空的PipelinePlan"""
    return PipelinePlan(steps=[])


def create_empty_code_cell(cell_id: str) -> CodeCell:
    """创建空的CodeCell"""
    return CodeCell(
        id=cell_id,
        imports=[],
        helpers=[],
        definitions=[],
        invoke="",
        exports={}
    )