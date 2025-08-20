"""
LLM Engine - QuantumForge V5 核心LLM调用引擎

纯粹的LLM API调用引擎，支持多模型选择。
基于 IMPLEMENTATION_ROADMAP.md 中的 Task 1.1 设计。
"""

import os

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件
except ImportError:
    pass


class LLMEngine:
    """
    QuantumForge V5 核心LLM调用引擎
    纯粹的LLM API调用，无缓存功能（由Memory系统负责）
    """
    
    # 支持的模型列表
    SUPPORTED_MODELS = [
        "gpt-4o",           # OpenAI GPT-4o
        "gpt-4o-mini",      # OpenAI GPT-4o mini
        "gpt-4",            # OpenAI GPT-4
    ]
    
    def __init__(self, model: str = "gpt-4o"):
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported. Available: {self.SUPPORTED_MODELS}")
            
        self.model = model
        
        # 检查OpenAI配置
        if not self._check_openai_config():
            raise Exception("OpenAI API not configured. Please check OPENAI_API_KEY in .env file.")
        
    def _check_openai_config(self) -> bool:
        """检查OpenAI API配置"""
        if not HAS_OPENAI:
            return False
            
        api_key = os.getenv('OPENAI_API_KEY')
        return bool(api_key)
    
    def call_llm(self, prompt: str) -> str:
        """
        核心LLM调用方法
        
        Args:
            prompt: 输入提示词

            
        Returns:
            LLM响应文本
        """
        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")
    
    def set_model(self, model: str) -> None:
        """切换模型"""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported. Available: {self.SUPPORTED_MODELS}")
        self.model = model
        
    def get_model(self) -> str:
        """获取当前模型"""
        return self.model
    
    def list_models(self) -> list:
        """获取支持的模型列表"""
        return self.SUPPORTED_MODELS.copy()


# 便利函数
def call_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    便利函数：快速LLM调用
    保持与现有代码的兼容性
    """
    # 使用全局引擎实例
    if not hasattr(call_llm, '_engine') or call_llm._engine.get_model() != model:
        call_llm._engine = LLMEngine(model=model)
    
    return call_llm._engine.call_llm(prompt)

