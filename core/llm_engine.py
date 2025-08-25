"""
LLM Engine - QuantumForge V5 核心LLM调用引擎

纯粹的LLM API调用引擎，支持OpenAI和DeepSeek模型。
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
    支持OpenAI和DeepSeek模型，纯粹的LLM API调用，无缓存功能（由Memory系统负责）
    """
    
    # 支持的模型列表
    SUPPORTED_MODELS = [
        "gpt-4o",              # OpenAI GPT-4o
        "gpt-4o-mini",         # OpenAI GPT-4o mini
        "gpt-4",               # OpenAI GPT-4
        "deepseek-chat",       # DeepSeek Chat
        "deepseek-reasoner",   # DeepSeek Reasoner
    ]
    
    def __init__(self, model: str = "gpt-4o"):
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported. Available: {self.SUPPORTED_MODELS}")
            
        self.model = model
        
        # 检查对应模型的配置
        if not self._check_config():
            provider = "OpenAI" if model.startswith("gpt-") else "DeepSeek"
            env_var = "OPENAI_API_KEY" if model.startswith("gpt-") else "DEEPSEEK_API_KEY"
            raise Exception(f"{provider} API not configured. Please check {env_var} in .env file.")
        
    def _check_config(self) -> bool:
        """检查当前模型的API配置"""
        if self.model.startswith("gpt-"):
            # OpenAI模型
            if not HAS_OPENAI:
                return False
            api_key = os.getenv('OPENAI_API_KEY')
            return bool(api_key and api_key.strip())
        
        elif self.model.startswith("deepseek-"):
            # DeepSeek模型 - 也使用OpenAI SDK
            if not HAS_OPENAI:
                return False
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                return False
            api_key = api_key.strip()
            return bool(api_key and api_key.startswith('sk-'))
        
        return False
    
    def call_llm(self, prompt: str) -> str:
        """
        核心LLM调用方法
        
        Args:
            prompt: 输入提示词
            
        Returns:
            LLM响应文本
        """
        try:
            if self.model.startswith("gpt-"):
                # OpenAI API调用
                return self._call_openai(prompt)
            
            elif self.model.startswith("deepseek-"):
                # DeepSeek API调用
                return self._call_deepseek(prompt)
            
            else:
                raise Exception(f"不支持的模型类型: {self.model}")
                
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")
    
    def _call_openai(self, prompt: str) -> str:
        """OpenAI API调用"""
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        return response.choices[0].message.content
    
    def _call_deepseek(self, prompt: str) -> str:
        """DeepSeek API调用 - 使用OpenAI SDK兼容接口"""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        
        # 验证 API Key
        if not api_key:
            raise Exception("DEEPSEEK_API_KEY environment variable is not set")
        
        api_key = api_key.strip()  # 清除可能的空格和换行符
        
        if not api_key.startswith('sk-'):
            raise Exception(f"Invalid DEEPSEEK_API_KEY format. Expected format: sk-... Got: {api_key[:10]}...")
        
        try:
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # 提供更详细的错误信息用于调试
            error_msg = str(e)
            if "authentication" in error_msg.lower():
                raise Exception(f"DeepSeek API authentication failed. Please verify your API key is valid. Error: {error_msg}")
            else:
                raise Exception(f"DeepSeek API call failed: {error_msg}")
    
    def set_model(self, model: str) -> None:
        """切换模型"""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported. Available: {self.SUPPORTED_MODELS}")
        
        old_model = self.model
        self.model = model
        
        # 重新检查配置
        if not self._check_config():
            self.model = old_model  # 恢复原模型
            provider = "OpenAI" if model.startswith("gpt-") else "DeepSeek"
            env_var = "OPENAI_API_KEY" if model.startswith("gpt-") else "DEEPSEEK_API_KEY"
            raise Exception(f"{provider} API not configured. Please check {env_var} in .env file.")
        
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

