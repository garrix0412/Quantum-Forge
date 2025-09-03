"""
语义理解引擎 - QuantumForge vNext

将用户自然语言查询转换为TaskCard。
基于new.md第4.3节规格和LLM引擎实现。
"""

from typing import Dict, Any
try:
    from .llm_engine import create_engine
    from .schemas import TaskCard
except ImportError:
    # 直接运行时的兼容处理
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from llm_engine import create_engine
    from schemas import TaskCard


def parse(query: str) -> Dict[str, Any]:
    """
    解析用户查询为TaskCard
    
    Args:
        query: 用户自然语言查询
        
    Returns:
        TaskCard字典
    """
    # 创建LLM引擎
    engine = create_engine()
    
    # 调用SemanticAgent
    task_card_dict = engine.task_understanding(query)
    
    return task_card_dict


def parse_to_dataclass(query: str) -> TaskCard:
    """
    解析用户查询为TaskCard数据类
    
    Args:
        query: 用户自然语言查询
        
    Returns:
        TaskCard数据类实例
    """
    task_card_dict = parse(query)
    
    # 转换为数据类
    return TaskCard(
        domain=task_card_dict["domain"],
        problem=task_card_dict["problem"], 
        algorithm=task_card_dict["algorithm"],
        backend=task_card_dict["backend"],
        params=task_card_dict["params"]
    )


def validate_query(query: str) -> bool:
    """
    验证查询是否可以处理
    
    Args:
        query: 用户查询
        
    Returns:
        是否可以处理这个查询
    """
    if not query or not query.strip():
        return False
    
    # 基础长度检查
    if len(query.strip()) < 5:
        return False
    
    return True


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing SemanticEngine...")
    
    # 测试用例
    test_queries = [
        "帮我计算8比特TFIM的基态能量",
        "使用VQE算法计算TFIM基态，比特数为10",
        "Calculate TFIM ground state energy with VQE",
        "我想用QAOA算法解决优化问题"
    ]
    
    for query in test_queries:
        print(f"\n🔍 测试查询: {query}")
        
        # 验证查询
        if not validate_query(query):
            print("❌ 查询验证失败")
            continue
        
        try:
            # 解析为字典
            task_card_dict = parse(query)
            print(f"📋 TaskCard (dict): {task_card_dict}")
            
            # 解析为数据类
            task_card = parse_to_dataclass(query)
            print(f"📦 TaskCard (dataclass): {task_card.domain}.{task_card.problem}.{task_card.algorithm}")
            
            # 验证结果一致性
            assert task_card.domain == task_card_dict["domain"]
            assert task_card.problem == task_card_dict["problem"]
            assert task_card.algorithm == task_card_dict["algorithm"]
            
            print("✅ 解析成功！")
            
        except Exception as e:
            print(f"❌ 解析失败: {str(e)}")
    
    print("\n🎉 SemanticEngine测试完成！")