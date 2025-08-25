"""
QML Quantum Circuit Builder - QuantumForge V5

QML量子电路参数标准化器，接收来自parameter_matcher的参数，进行量子电路特定的验证、标准化和默认值处理。
遵循QuantumForge V5的LLM驱动架构：信任上游parameter_matcher分析，专注量子电路构建逻辑。
专注于QML任务的量子电路构建，支持多种ansatz配置的灵活性。
"""

from typing import Dict, Any

# 导入基类
try:
    from ..base_component import BaseComponent
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from components.base_component import BaseComponent


class QMLQuantumCircuitBuilder(BaseComponent):
    """QML量子电路构建器 - 信任parameter_matcher的智能参数分析，专注量子电路构建"""
    
    description = "Build quantum circuits for machine learning tasks. Supports multiple feature maps (ZZFeatureMap, PauliFeatureMap, RawFeatureVector) and ansatz types (RealAmplitudes, EfficientSU2, TwoLocal) with intelligent parameter configuration. Creates EstimatorQNN with gradient support for hybrid training. Trusts parameter_matcher for circuit configuration."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """构建QML量子电路"""
        # 信任parameter_matcher提供的参数
        circuit_params = params.copy()
        
        # 应用QML量子电路特定的默认值
        complete_params = self._apply_qml_circuit_defaults(circuit_params)
        
        # 参数获取
        num_qubits = complete_params.get("num_qubits", 2)
        feature_map_type = complete_params.get("feature_map_type", "ZZFeatureMap")
        ansatz_type = complete_params.get("ansatz_type", "RealAmplitudes")
        ansatz_reps = complete_params.get("ansatz_reps", 1)
        
        # 生成量子电路代码
        code = self._generate_quantum_circuit_code(complete_params)
        
        # 计算circuit_info
        circuit_info = self._calculate_circuit_info(num_qubits, feature_map_type, ansatz_type, ansatz_reps)
        
        # 简要描述
        notes = f"QML circuit: {feature_map_type} + {ansatz_type}({ansatz_reps} reps) on {num_qubits} qubits"
        
        return {
            "code": code,
            "notes": notes,
            "circuit_info": circuit_info
        }
    
    def _apply_qml_circuit_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用QML量子电路特定的默认值 - 信任parameter_matcher"""
        # 设置QML量子电路默认值
        defaults = {
            "num_qubits": 2,                      # 默认2量子比特（与原QML代码一致）
            "feature_map_type": "ZZFeatureMap",   # ZZ feature map（与原代码一致）
            "ansatz_type": "RealAmplitudes",      # Real amplitudes ansatz（与原代码一致）
            "ansatz_reps": 1,                     # ansatz重复层数（与原代码一致）
            "feature_map_reps": 1,                # feature map重复次数
            "feature_map_entanglement": "full",   # feature map纠缠结构
            "ansatz_entanglement": "full",        # ansatz纠缠结构
            "input_gradients": True,              # 启用混合梯度（关键参数）
            "estimator_type": "StatevectorEstimator"  # 默认状态向量估计器
        }
        
        # 合并参数，保持parameter_matcher提供的参数优先
        complete_params = {**defaults, **params}
        
        # 智能调整：基于数据集特性的启发式规则
        task_context = self._infer_qml_context(params)
        
        if task_context == "lightweight":
            # 轻量级配置
            if "ansatz_reps" not in params:
                complete_params["ansatz_reps"] = 1
        elif task_context == "complex":
            # 复杂任务配置
            if "ansatz_reps" not in params:
                complete_params["ansatz_reps"] = 2
        
        # 量子比特数量智能调整
        dataset_info = params.get("dataset_info", {})
        if dataset_info and "image_dims" in dataset_info:
            # 基于数据集维度智能推断量子比特数（但保持合理范围）
            image_size = dataset_info["image_dims"].get("height", 28) * dataset_info["image_dims"].get("width", 28)
            if image_size <= 784:  # MNIST/FashionMNIST类型
                suggested_qubits = min(4, max(2, int(image_size**0.25)))  # 2-4量子比特
                if "num_qubits" not in params:
                    complete_params["num_qubits"] = suggested_qubits
        
        return complete_params
    
    def _infer_qml_context(self, params: Dict[str, Any]) -> str:
        """推断QML任务复杂度以做智能调整"""
        dataset_info = params.get("dataset_info", {})
        
        if dataset_info:
            # 基于数据集规模判断复杂度
            total_samples = dataset_info.get("total_train_samples", 0)
            num_classes = dataset_info.get("num_classes", 2)
            
            # QML专注二分类，基于样本数量判断复杂度
            if total_samples <= 200:
                return "lightweight"
            elif total_samples > 1000:
                return "complex"
        
        return "standard"
    
    
    def _generate_quantum_circuit_code(self, params: Dict[str, Any]) -> str:
        """生成量子电路代码"""
        num_qubits = params["num_qubits"]
        feature_map_type = params["feature_map_type"]
        ansatz_type = params["ansatz_type"]
        ansatz_reps = params["ansatz_reps"]
        feature_map_reps = params.get("feature_map_reps", 1)
        feature_map_entanglement = params.get("feature_map_entanglement", "full")
        ansatz_entanglement = params.get("ansatz_entanglement", "full")
        input_gradients = params.get("input_gradients", True)
        estimator_type = params.get("estimator_type", "StatevectorEstimator")
        
        # 基础代码框架
        code = f'''# QML Quantum Circuit Builder - Generated by QuantumForge V5
from qiskit import QuantumCircuit
from qiskit.circuit.library import ZZFeatureMap, PauliFeatureMap, RealAmplitudes, EfficientSU2, TwoLocal
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit.primitives import {estimator_type}

# Quantum Circuit Configuration
NUM_QUBITS = {num_qubits}
FEATURE_MAP_TYPE = "{feature_map_type}"
ANSATZ_TYPE = "{ansatz_type}" 
ANSATZ_REPS = {ansatz_reps}
FEATURE_MAP_REPS = {feature_map_reps}
INPUT_GRADIENTS = {input_gradients}

print(f"Building QML circuit: {{FEATURE_MAP_TYPE}} + {{ANSATZ_TYPE}} on {{NUM_QUBITS}} qubits")

def create_qml_circuit():
    """
    Create QML quantum circuit with feature map and ansatz
    
    Returns:
        tuple: (quantum_circuit, input_params, weight_params)
    """
    # Create feature map'''
        
        # 添加feature map生成代码
        code += self._generate_feature_map_code(feature_map_type, num_qubits, 
                                              feature_map_reps, feature_map_entanglement)
        
        # 添加ansatz生成代码  
        code += self._generate_ansatz_code(ansatz_type, num_qubits, 
                                         ansatz_reps, ansatz_entanglement)
        
        # 添加电路组合和QNN创建代码
        code += f'''
    
    # Combine feature map and ansatz
    qc = QuantumCircuit(NUM_QUBITS)
    qc.compose(feature_map, inplace=True)
    qc.compose(ansatz, inplace=True)
    
    print(f"Circuit depth: {{qc.depth()}}")
    print(f"Circuit gates: {{qc.count_ops()}}")
    
    return qc, feature_map.parameters, ansatz.parameters

def create_qml_qnn():
    """
    Create EstimatorQNN for quantum machine learning
    
    Returns:
        EstimatorQNN: Configured quantum neural network
    """
    # Create circuit and parameter sets
    circuit, input_params, weight_params = create_qml_circuit()
    
    # Create estimator
    estimator = {estimator_type}()
    
    # Create QNN with gradient support for hybrid training
    qnn = EstimatorQNN(
        circuit=circuit,
        input_params=input_params,
        weight_params=weight_params,
        input_gradients=INPUT_GRADIENTS,  # Enable hybrid gradient computation
        estimator=estimator
    )
    
    print(f"QNN created: {{len(input_params)}} input params, {{len(weight_params)}} weight params")
    print(f"Gradient support: {{INPUT_GRADIENTS}}")
    
    return qnn

# Create the QML quantum neural network
qnn = create_qml_qnn()
print("QML quantum circuit ready for hybrid training")
'''
        
        return code
    
    def _generate_feature_map_code(self, feature_map_type: str, num_qubits: int, 
                                 reps: int, entanglement: str) -> str:
        """生成feature map代码"""
        if feature_map_type == "ZZFeatureMap":
            return f'''
    feature_map = ZZFeatureMap(
        feature_dimension={num_qubits},
        reps={reps},
        entanglement="{entanglement}"
    )'''
        elif feature_map_type == "PauliFeatureMap":
            return f'''
    feature_map = PauliFeatureMap(
        feature_dimension={num_qubits},
        reps={reps},
        entanglement="{entanglement}",
        paulis=['Z', 'ZZ']
    )'''
        else:  # Default to ZZFeatureMap
            return f'''
    feature_map = ZZFeatureMap(
        feature_dimension={num_qubits},
        reps={reps},
        entanglement="{entanglement}"
    )'''
    
    def _generate_ansatz_code(self, ansatz_type: str, num_qubits: int, 
                            reps: int, entanglement: str) -> str:
        """生成ansatz代码"""
        if ansatz_type == "RealAmplitudes":
            return f'''
    
    # Create ansatz (RealAmplitudes - real-valued parameters only)
    ansatz = RealAmplitudes(
        num_qubits={num_qubits},
        reps={reps},
        entanglement="{entanglement}"
    )'''
        elif ansatz_type == "EfficientSU2":
            return f'''
    
    # Create ansatz (EfficientSU2 - hardware efficient)
    ansatz = EfficientSU2(
        num_qubits={num_qubits},
        reps={reps},
        entanglement="{entanglement}"
    )'''
        elif ansatz_type == "TwoLocal":
            return f'''
    
    # Create ansatz (TwoLocal - flexible parameterization)
    ansatz = TwoLocal(
        num_qubits={num_qubits},
        rotation_blocks=['ry', 'rz'],
        entanglement_blocks='cx',
        entanglement="{entanglement}",
        reps={reps}
    )'''
        else:  # Default to RealAmplitudes
            return f'''
    
    # Create ansatz (RealAmplitudes - default)
    ansatz = RealAmplitudes(
        num_qubits={num_qubits},
        reps={reps},
        entanglement="{entanglement}"
    )'''
    
    def _calculate_circuit_info(self, num_qubits: int, feature_map_type: str, 
                              ansatz_type: str, ansatz_reps: int) -> Dict[str, Any]:
        """计算量子电路关键信息"""
        
        # 估算参数数量（基于ansatz类型和量子比特数）
        if ansatz_type == "RealAmplitudes":
            # RealAmplitudes: 每层每个qubit一个RY参数 + 最后一层
            weight_params = (ansatz_reps + 1) * num_qubits
        elif ansatz_type == "EfficientSU2":
            # EfficientSU2: 每层每个qubit两个参数 (RY + RZ)
            weight_params = ansatz_reps * num_qubits * 2 + num_qubits
        elif ansatz_type == "TwoLocal":
            # TwoLocal: 取决于rotation_blocks数量，这里假设['ry', 'rz']
            weight_params = ansatz_reps * num_qubits * 2 + num_qubits * 2
        else:
            # 默认估算
            weight_params = (ansatz_reps + 1) * num_qubits
        
        # Feature map输入参数数量
        if feature_map_type in ["ZZFeatureMap", "PauliFeatureMap"]:
            input_params = num_qubits  # 特征维度等于量子比特数
        else:
            input_params = num_qubits
        
        # 估算电路深度
        feature_map_depth = 2  # 基础feature map深度
        ansatz_depth = ansatz_reps * 2 + 1  # ansatz深度估算
        total_depth = feature_map_depth + ansatz_depth
        
        return {
            "num_qubits": num_qubits,
            "weight_params": weight_params,
            "input_params": input_params,
            "total_params": weight_params + input_params,
            "circuit_depth": total_depth,
            "feature_map_type": feature_map_type,
            "ansatz_type": ansatz_type,
            "ansatz_reps": ansatz_reps,
            "input_dimension": input_params,      # 与经典网络接口
            "output_dimension": 1,               # QNN输出维度
            "gradient_support": True             # 支持混合梯度
        }