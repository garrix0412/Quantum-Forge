"""
QML Hybrid Network Builder - QuantumForge V5

QML混合网络参数标准化器，接收来自parameter_matcher的参数，进行QML混合网络特定的验证、标准化和默认值处理。
遵循QuantumForge V5的LLM驱动架构：信任上游parameter_matcher分析，专注混合网络构建逻辑。
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


class QMLHybridNetworkBuilder(BaseComponent):
    """QML混合网络构建器 - 信任parameter_matcher的智能参数分析，专注混合网络构建"""
    
    description = "Build hybrid quantum-classical neural networks for binary classification QML tasks. Creates CNN frontend → QNN → classical backend architecture optimized for 2-class problems. Follows original qml.py pattern with complementary binary outputs [x, 1-x]. Trusts parameter_matcher for network configuration."
    
    def execute(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """构建QML混合网络"""
        # 信任parameter_matcher提供的参数
        network_params = params.copy()
        
        # 应用QML混合网络特定的默认值
        complete_params = self._apply_qml_network_defaults(network_params)
        
        # 参数获取
        input_channels = complete_params.get("input_channels", 1)
        classical_layers = complete_params.get("classical_layers", [2, 16, 64])
        qnn_input_dim = complete_params.get("qnn_input_dim", 2)
        qnn_output_dim = complete_params.get("qnn_output_dim", 1)
        output_classes = complete_params.get("output_classes", 2)
        
        # 生成混合网络代码
        code = self._generate_hybrid_network_code(complete_params)
        
        # 计算network_info
        network_info = self._calculate_network_info(complete_params)
        
        # 简要描述
        notes = f"QML hybrid: CNN({classical_layers}) → QNN({qnn_input_dim}→{qnn_output_dim}) → FC({output_classes} classes)"
        
        return {
            "code": code,
            "notes": notes,
            "network_info": network_info
        }
    
    def _apply_qml_network_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用QML混合网络特定的默认值 - 信任parameter_matcher"""
        # 设置QML混合网络默认值
        defaults = {
            "input_channels": 1,                    # MNIST/FashionMNIST单通道
            "classical_layers": [2, 16, 64],       # CNN层配置（与原代码一致）
            "conv_kernel_size": 5,                  # 卷积核大小
            "pooling_size": 2,                      # 池化大小
            "dropout_rate": 0.2,                    # dropout率
            "qnn_input_dim": 2,                     # QNN输入维度（与量子比特数匹配）
            "qnn_output_dim": 1,                    # QNN输出维度
            "output_classes": 2,                    # 二分类固定为2
            "activation": "relu",                   # 激活函数
            "final_activation": "log_softmax",      # 最终激活（用于NLLLoss）
            "network_type": "CNN_QNN_FC"            # 网络架构类型
        }
        
        # 合并参数，保持parameter_matcher提供的参数优先
        complete_params = {**defaults, **params}
        
        # 智能调整：基于数据集信息调整网络结构
        dataset_info = params.get("dataset_info", {})
        if dataset_info:
            # 根据图像尺寸调整网络结构
            image_dims = dataset_info.get("image_dims", {})
            if image_dims:
                input_channels = image_dims.get("channels", 1)
                complete_params["input_channels"] = input_channels
            
            # QML专注二分类，固定输出类别数为2
            complete_params["output_classes"] = 2
        
        # 量子电路信息智能调整
        circuit_info = params.get("circuit_info", {})
        if circuit_info:
            # QNN输入维度与量子比特数匹配
            num_qubits = circuit_info.get("num_qubits", 2)
            if "qnn_input_dim" not in params:
                complete_params["qnn_input_dim"] = num_qubits
            
            # QNN输出维度与电路输出匹配
            output_dim = circuit_info.get("output_dimension", 1)
            if "qnn_output_dim" not in params:
                complete_params["qnn_output_dim"] = output_dim
        
        # 网络架构智能调整
        task_context = self._infer_network_context(params)
        if task_context == "lightweight":
            # 轻量级网络配置
            complete_params["classical_layers"] = [2, 8, 32]
            complete_params["dropout_rate"] = 0.1
        elif task_context == "complex":
            # 复杂网络配置
            complete_params["classical_layers"] = [4, 32, 128]
            complete_params["dropout_rate"] = 0.3
        
        return complete_params
    
    def _infer_network_context(self, params: Dict[str, Any]) -> str:
        """推断网络复杂度上下文以做智能调整"""
        dataset_info = params.get("dataset_info", {})
        
        # 基于数据集大小判断网络复杂度需求
        if dataset_info:
            total_samples = dataset_info.get("total_train_samples", 0)
            
            # QML二分类任务，基于样本数量判断复杂度
            if total_samples <= 200:
                return "lightweight"
            elif total_samples > 1000:
                return "complex"
        
        return "standard"
    
    def _generate_hybrid_network_code(self, params: Dict[str, Any]) -> str:
        """生成混合网络代码"""
        input_channels = params["input_channels"]
        classical_layers = params["classical_layers"]
        conv_kernel_size = params["conv_kernel_size"]
        pooling_size = params["pooling_size"]
        dropout_rate = params["dropout_rate"]
        qnn_input_dim = params["qnn_input_dim"]
        qnn_output_dim = params["qnn_output_dim"]
        output_classes = params["output_classes"]
        activation = params["activation"]
        final_activation = params["final_activation"]
        
        # 生成网络结构代码
        code = f'''# QML Hybrid Network Builder - Generated by QuantumForge V5
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import Module, Conv2d, Linear, Dropout2d, MaxPool2d
from qiskit_machine_learning.connectors import TorchConnector

# Network Configuration
INPUT_CHANNELS = {input_channels}
CLASSICAL_LAYERS = {classical_layers}  # [conv1_out, conv2_out, fc1_out]
CONV_KERNEL_SIZE = {conv_kernel_size}
POOLING_SIZE = {pooling_size}
DROPOUT_RATE = {dropout_rate}
QNN_INPUT_DIM = {qnn_input_dim}
QNN_OUTPUT_DIM = {qnn_output_dim}
OUTPUT_CLASSES = {output_classes}
ACTIVATION = "{activation}"
FINAL_ACTIVATION = "{final_activation}"

print(f"Building QML hybrid network: CNN → QNN({{QNN_INPUT_DIM}}→{{QNN_OUTPUT_DIM}}) → FC({{OUTPUT_CLASSES}} classes)")

class QMLHybridNetwork(Module):
    """
    Hybrid Quantum-Classical Neural Network
    
    Architecture: CNN Frontend → Quantum Neural Network → Classical Backend
    """
    
    def __init__(self, qnn):
        """
        Initialize hybrid network
        
        Args:
            qnn: Quantum neural network (EstimatorQNN)
        """
        super().__init__()
        
        # Classical CNN frontend'''
        
        # 添加CNN层生成代码
        code += self._generate_cnn_layers_code(classical_layers, input_channels, 
                                               conv_kernel_size, dropout_rate)
        
        # 添加量子层连接代码
        code += f'''
        
        # Quantum neural network integration
        self.qnn = TorchConnector(qnn)  # Connect QNN with PyTorch autograd
        
        # Classical backend (post-quantum processing)
        self.fc_post_quantum = Linear({qnn_output_dim}, 1)  # QML二分类输出到1维
        
        print(f"Hybrid network initialized: {{self._count_parameters()}} total parameters")
    
    def forward(self, x):
        """
        Forward pass through hybrid network
        
        Args:
            x: Input tensor [batch_size, channels, height, width]
            
        Returns:
            Output tensor [batch_size, num_classes]
        """
        # CNN frontend processing
        x = F.{activation}(self.conv1(x))
        x = F.max_pool2d(x, {pooling_size})
        x = F.{activation}(self.conv2(x))
        x = F.max_pool2d(x, {pooling_size})
        x = self.dropout(x)
        
        # Flatten for fully connected layers
        x = x.view(x.shape[0], -1)
        x = F.{activation}(self.fc1(x))
        x = self.fc_pre_quantum(x)  # Prepare input for QNN
        
        # Quantum processing
        x = self.qnn(x)  # Apply quantum neural network
        
        # Classical post-processing'''
        
        # QML专注二分类任务（与原qml.py代码兼容）
        code += f'''
        x = self.fc_post_quantum(x)  # [batch_size, 1] → [batch_size, 1]
        
        # Binary classification: create complementary outputs (following original qml.py pattern)
        if x.dim() == 1:
            x = x.unsqueeze(-1)  # Ensure proper dimensionality
        
        # Create binary outputs: [prob_class_0, prob_class_1] = [x, 1-x]
        return torch.cat((x, 1 - x), -1)'''
        
        # 添加工具方法
        code += f'''
    
    def _count_parameters(self):
        """Count total trainable parameters"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_network_info(self):
        """Get network architecture information"""
        total_params = self._count_parameters()
        classical_params = sum(p.numel() for name, p in self.named_parameters() 
                             if p.requires_grad and 'qnn' not in name)
        quantum_params = total_params - classical_params
        
        return {{
            "total_parameters": total_params,
            "classical_parameters": classical_params,
            "quantum_parameters": quantum_params,
            "architecture": "CNN_QNN_FC",
            "input_shape": [INPUT_CHANNELS, 28, 28],  # Assuming MNIST-like input
            "output_classes": OUTPUT_CLASSES
        }}

def create_hybrid_model(qnn):
    """
    Create QML hybrid network instance
    
    Args:
        qnn: Configured quantum neural network (EstimatorQNN)
        
    Returns:
        QMLHybridNetwork: Initialized hybrid model
    """
    model = QMLHybridNetwork(qnn)
    
    # Print network information
    network_info = model.get_network_info()
    print(f"Network created:")
    print(f"  Total parameters: {{network_info['total_parameters']:,}}")
    print(f"  Classical parameters: {{network_info['classical_parameters']:,}}")
    print(f"  Quantum parameters: {{network_info['quantum_parameters']:,}}")
    print(f"  Architecture: {{network_info['architecture']}}")
    
    return model

# Example usage (requires QNN from QMLQuantumCircuitBuilder):
# from qml_quantum_circuit_builder import create_qml_qnn
# qnn = create_qml_qnn()
# model = create_hybrid_model(qnn)
print("QML hybrid network ready for training")
'''
        
        return code
    
    def _generate_cnn_layers_code(self, classical_layers: list, input_channels: int, 
                                 conv_kernel_size: int, dropout_rate: float) -> str:
        """生成CNN层代码"""
        conv1_out, conv2_out, fc1_out = classical_layers
        
        return f'''
        self.conv1 = Conv2d({input_channels}, {conv1_out}, kernel_size={conv_kernel_size})
        self.conv2 = Conv2d({conv1_out}, {conv2_out}, kernel_size={conv_kernel_size})
        self.dropout = Dropout2d(p={dropout_rate})
        
        # Calculate flattened size after convolutions and pooling
        # For MNIST (28x28): after 2 conv({conv_kernel_size}x{conv_kernel_size}) + 2 maxpool(2x2)
        # Size: ((28-{conv_kernel_size}+1)/2 - {conv_kernel_size}+1)/2 = {(((28-conv_kernel_size+1)//2 - conv_kernel_size+1)//2)}
        conv_output_size = {conv2_out} * {(((28-conv_kernel_size+1)//2 - conv_kernel_size+1)//2)**2}
        
        # Classical fully connected layers
        self.fc1 = Linear(conv_output_size, {fc1_out})
        self.fc_pre_quantum = Linear({fc1_out}, QNN_INPUT_DIM)'''
    
    def _calculate_network_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """计算混合网络关键信息"""
        classical_layers = params["classical_layers"]
        input_channels = params["input_channels"]
        conv_kernel_size = params["conv_kernel_size"]
        qnn_input_dim = params["qnn_input_dim"]
        qnn_output_dim = params["qnn_output_dim"]
        output_classes = params["output_classes"]
        
        # 估算参数数量
        conv1_params = (input_channels * classical_layers[0] * conv_kernel_size**2) + classical_layers[0]
        conv2_params = (classical_layers[0] * classical_layers[1] * conv_kernel_size**2) + classical_layers[1]
        
        # FC层参数估算（基于MNIST 28x28输入）
        conv_output_size = classical_layers[1] * (((28-conv_kernel_size+1)//2 - conv_kernel_size+1)//2)**2
        fc1_params = (conv_output_size * classical_layers[2]) + classical_layers[2]
        fc_pre_quantum_params = (classical_layers[2] * qnn_input_dim) + qnn_input_dim
        fc_post_quantum_params = (qnn_output_dim * 1) + 1  # QML二分类后处理层参数
        
        classical_params = conv1_params + conv2_params + fc1_params + fc_pre_quantum_params + fc_post_quantum_params
        
        # 量子参数数量（从circuit_info获取）
        circuit_info = params.get("circuit_info", {})
        quantum_params = circuit_info.get("weight_params", 0) if circuit_info else 0
        
        total_params = classical_params + quantum_params
        
        return {
            "network_type": params["network_type"],
            "total_parameters": total_params,
            "classical_parameters": classical_params,
            "quantum_parameters": quantum_params,
            "architecture_layers": {
                "cnn_frontend": classical_layers[:2],
                "classical_fc": classical_layers[2],
                "quantum_processing": f"{qnn_input_dim}→{qnn_output_dim}",
                "output_classes": output_classes
            },
            "input_shape": [input_channels, 28, 28],  # 假设MNIST类型输入
            "parameter_breakdown": {
                "conv_layers": conv1_params + conv2_params,
                "fc_layers": fc1_params + fc_pre_quantum_params + fc_post_quantum_params,
                "quantum_circuit": quantum_params
            },
            "trainable_parameters": total_params,
            "classical_quantum_ratio": classical_params / max(quantum_params, 1)
        }