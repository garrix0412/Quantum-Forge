"""
执行上下文 - QuantumForge vNext

统一的执行上下文对象，用于在整个处理流程中累积和传递数据。
替代多参数传递，简化函数接口，提高代码可维护性。
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from core.execution_memory import Memory, create as create_memory
from core.cache_manager import CacheManager, create_cache_manager


@dataclass
class ExecutionMetrics:
    """执行指标"""
    start_time: float = field(default_factory=time.time)
    stage_times: Dict[str, float] = field(default_factory=dict)
    agent_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def mark_stage_start(self, stage_name: str) -> None:
        """标记阶段开始"""
        self.stage_times[f"{stage_name}_start"] = time.time()
    
    def mark_stage_end(self, stage_name: str) -> None:
        """标记阶段结束"""
        self.stage_times[f"{stage_name}_end"] = time.time()
    
    def get_stage_duration(self, stage_name: str) -> Optional[float]:
        """获取阶段执行时间"""
        start_key = f"{stage_name}_start"
        end_key = f"{stage_name}_end"
        
        if start_key in self.stage_times and end_key in self.stage_times:
            return self.stage_times[end_key] - self.stage_times[start_key]
        
        return None
    
    def get_total_time(self) -> float:
        """获取总执行时间"""
        return time.time() - self.start_time


class ExecutionContext:
    """
    执行上下文 - 统一的数据传递容器
    
    用于在整个QuantumForge处理流程中累积和传递数据：
    Query → TaskCard → Components → ParamMap → PipelinePlan → Memory → Code
    """
    
    def __init__(
        self, 
        query: str, 
        enable_cache: bool = True,
        debug: bool = False
    ):
        """
        初始化执行上下文
        
        Args:
            query: 用户查询
            enable_cache: 是否启用缓存
            debug: 是否启用调试模式
        """
        # 基本信息
        self.query = query
        self.debug = debug
        
        # 流程数据（逐步填充）
        self.task_card: Optional[Dict[str, Any]] = None
        self.components: List[Dict[str, Any]] = []
        self.param_map: Optional[Dict[str, Any]] = None
        self.pipeline_plan: Optional[Dict[str, Any]] = None
        self.memory: Memory = create_memory()
        self.final_code: Optional[str] = None
        
        # 系统组件
        self.cache_manager: CacheManager = create_cache_manager(enable_cache=enable_cache)
        self.metrics: ExecutionMetrics = ExecutionMetrics()
        
        # 错误信息
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    # =============================================================================
    # 链式数据设置方法
    # =============================================================================
    
    def set_task_card(self, task_card: Dict[str, Any]) -> 'ExecutionContext':
        """设置任务卡"""
        self.task_card = task_card
        self._debug_print(f"📋 TaskCard设置: {task_card.get('domain', 'unknown')}.{task_card.get('algorithm', 'unknown')}")
        return self
    
    def set_components(self, components: List[Dict[str, Any]]) -> 'ExecutionContext':
        """设置组件列表"""
        self.components = components
        component_names = [comp.get('name', 'unknown') for comp in components]
        self._debug_print(f"🧱 Components设置: {component_names}")
        return self
    
    def set_param_map(self, param_map: Dict[str, Any]) -> 'ExecutionContext':
        """设置参数映射"""
        self.param_map = param_map
        param_count = len(param_map.get('normalized_params', {}))
        self._debug_print(f"🔧 ParamMap设置: {param_count}个参数")
        return self
    
    def set_pipeline_plan(self, pipeline_plan: Dict[str, Any]) -> 'ExecutionContext':
        """设置管道计划"""
        self.pipeline_plan = pipeline_plan
        step_count = len(pipeline_plan.get('execution_order', []))
        self._debug_print(f"📊 PipelinePlan设置: {step_count}个步骤")
        return self
    
    def set_final_code(self, code: str) -> 'ExecutionContext':
        """设置最终代码"""
        self.final_code = code
        self._debug_print(f"✅ 最终代码设置: {len(code)}字符")
        return self
    
    # =============================================================================
    # 数据访问方法
    # =============================================================================
    
    def get_task_card(self) -> Dict[str, Any]:
        """获取任务卡"""
        if self.task_card is None:
            raise ValueError("TaskCard未设置")
        return self.task_card
    
    def get_components(self) -> List[Dict[str, Any]]:
        """获取组件列表"""
        return self.components
    
    def get_param_map(self) -> Dict[str, Any]:
        """获取参数映射"""
        if self.param_map is None:
            raise ValueError("ParamMap未设置")
        return self.param_map
    
    def get_pipeline_plan(self) -> Dict[str, Any]:
        """获取管道计划"""
        if self.pipeline_plan is None:
            raise ValueError("PipelinePlan未设置")
        return self.pipeline_plan
    
    def get_memory(self) -> Memory:
        """获取执行内存"""
        return self.memory
    
    def get_final_code(self) -> str:
        """获取最终代码"""
        if self.final_code is None:
            raise ValueError("最终代码未生成")
        return self.final_code
    
    # =============================================================================
    # 缓存集成方法
    # =============================================================================
    
    def check_query_cache(self) -> Optional[str]:
        """检查查询缓存"""
        if self.task_card is None:
            return None
        
        cached_code = self.cache_manager.get_cached_query_result(self.query, self.task_card)
        if cached_code:
            self.metrics.cache_hits += 1
            self._debug_print("🚀 缓存命中：直接返回缓存结果")
        else:
            self.metrics.cache_misses += 1
        
        return cached_code
    
    def cache_final_result(self) -> None:
        """缓存最终结果"""
        if self.task_card and self.final_code:
            self.cache_manager.cache_query_result(self.query, self.task_card, self.final_code)
    
    # =============================================================================
    # 辅助方法
    # =============================================================================
    
    def add_error(self, error_msg: str) -> None:
        """添加错误信息"""
        self.errors.append(error_msg)
        self._debug_print(f"❌ 错误: {error_msg}")
    
    def add_warning(self, warning_msg: str) -> None:
        """添加警告信息"""
        self.warnings.append(warning_msg)
        self._debug_print(f"⚠️ 警告: {warning_msg}")
    
    def _debug_print(self, message: str) -> None:
        """调试输出"""
        if self.debug:
            print(message)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "query": self.query,
            "total_time": self.metrics.get_total_time(),
            "stage_times": {
                stage: self.metrics.get_stage_duration(stage)
                for stage in ["semantic", "discovery", "param_norm", "pipeline", "codegen", "assembly"]
                if self.metrics.get_stage_duration(stage) is not None
            },
            "agent_calls": self.metrics.agent_calls,
            "cache_performance": {
                "hits": self.metrics.cache_hits,
                "misses": self.metrics.cache_misses,
                "hit_rate": self.metrics.cache_hits / max(1, self.metrics.cache_hits + self.metrics.cache_misses)
            },
            "components_count": len(self.components),
            "final_code_length": len(self.final_code) if self.final_code else 0,
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def is_complete(self) -> bool:
        """是否完成处理"""
        return (
            self.task_card is not None and
            len(self.components) > 0 and
            self.param_map is not None and
            self.pipeline_plan is not None and
            self.final_code is not None
        )


# =============================================================================
# 便利函数
# =============================================================================

def create_context(query: str, enable_cache: bool = True, debug: bool = False) -> ExecutionContext:
    """
    创建执行上下文
    
    Args:
        query: 用户查询
        enable_cache: 是否启用缓存
        debug: 是否启用调试模式
        
    Returns:
        ExecutionContext实例
    """
    return ExecutionContext(query=query, enable_cache=enable_cache, debug=debug)


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing ExecutionContext...")
    
    # 创建上下文
    context = create_context("测试查询", debug=True)
    
    # 测试链式调用
    test_task_card = {"domain": "spin", "algorithm": "vqe", "params": {"n": 4}}
    test_components = [{"name": "Test.Component", "kind": "test"}]
    test_param_map = {"normalized_params": {"n": 4}, "aliases": {}, "defaults": {}}
    
    context.set_task_card(test_task_card)\
           .set_components(test_components)\
           .set_param_map(test_param_map)
    
    # 验证数据
    assert context.get_task_card() == test_task_card
    assert context.get_components() == test_components
    assert context.get_param_map() == test_param_map
    
    print("✅ 链式调用工作正常")
    
    # 测试缓存功能
    context.cache_manager.cache_query_result("测试", test_task_card, "test_code")
    cached = context.check_query_cache()
    print(f"🚀 缓存测试: {'命中' if cached else '未命中'}")
    
    # 显示摘要
    print("\n📊 执行摘要:")
    summary = context.get_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    print("\n🎉 ExecutionContext测试完成！")