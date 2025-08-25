"""
QAOA Graph Builder - QuantumForge V5 图生成组件

生成QAOA优化所需的图结构，支持多种图类型和配置。
基于 IMPLEMENTATION_ROADMAP.md 中的组件化设计。
"""

import numpy as np
import networkx as nx
from typing import Dict, Any

# 导入基础组件类
try:
    from ..base_component import BaseComponent
except ImportError:
    # 在直接运行时使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_component import BaseComponent


class QAOAGraphBuilder(BaseComponent):
    """
    QAOA图生成器
    
    职责：生成QAOA算法所需的图结构
    - 信任parameter_matcher的智能参数分析
    - 生成图并输出标准化的图信息
    - 为下游组件提供清晰的接口
    """
    
    description = "Generate graph structures for QAOA MaxCut optimization. Supports random graphs, complete graphs, and custom edge configurations."
    
    def __init__(self):
        super().__init__()
        self.graph = None
        self.edge_list = []
        self.graph_info = {}
    
    def process(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        主处理函数：生成QAOA优化图
        
        信任parameter_matcher的智能分析，直接使用提供的参数
        
        Args:
            parameters: parameter_matcher解析的参数字典
                
        Returns:
            标准化的图信息字典，供下游组件使用
        """
        try:
            # 信任parameter_matcher分析结果，直接提取参数
            num_nodes = parameters.get('num_nodes', 4)
            graph_type = parameters.get('graph_type', 'random')
            edge_prob = parameters.get('edge_prob', 1.0)
            custom_edges = parameters.get('custom_edges', [])
            seed = parameters.get('seed', 42)
            
            # 设置随机种子确保可重现性
            np.random.seed(seed)
            
            # 根据参数生成对应图结构
            if graph_type == 'complete':
                self.graph = nx.complete_graph(num_nodes)
            elif graph_type == 'custom' and custom_edges:
                self.graph = nx.Graph()
                self.graph.add_nodes_from(range(num_nodes))
                self.graph.add_edges_from(custom_edges)
            else:  # 默认随机图
                self.graph = nx.erdos_renyi_graph(num_nodes, edge_prob, seed=seed)
                # 确保图连通性
                if self.graph.number_of_edges() == 0:
                    self.graph.add_edge(0, min(1, num_nodes - 1))
            
            # 提取关键信息
            self.edge_list = list(self.graph.edges())
            
            # 构建轻量级输出（只传递生成参数，不传递具体边列表）
            self.graph_info = {
                'num_nodes': num_nodes,
                'graph_type': graph_type,
                'edge_prob': edge_prob,
                'custom_edges': custom_edges,
                'seed': seed,
                'generation_params': True  # 标识这是生成参数而非实际图数据
            }
            
            return {
                'success': True,
                'graph_info': self.graph_info,
                'message': f"图参数配置完成: {graph_type}图, {num_nodes}节点"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"图生成失败: {str(e)}",
                'graph_info': None,
                'edge_list': []
            }
    
