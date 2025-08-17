"""
QuantumForge V4 LLM Engine

统一的LLM调用接口，支持多种LLM提供商和智能prompt优化。
"""

from typing import Dict, Any, Optional, List
import json
import time
import os
from abc import ABC, abstractmethod


class LLMEngine(ABC):
    """LLM引擎抽象基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成LLM响应"""
        pass



class OpenAIEngine(LLMEngine):
    """
    OpenAI GPT引擎 - 生产环境使用
    
    需要配置OpenAI API密钥
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        # 从.env文件或环境变量获取API密钥
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key is None:
                # 尝试从.env文件读取
                try:
                    from dotenv import load_dotenv
                    load_dotenv()
                    api_key = os.getenv('OPENAI_API_KEY')
                except ImportError:
                    pass  # python-dotenv未安装
        
        self.api_key = api_key
        self.model = model
        
        # 尝试导入OpenAI
        try:
            import openai
            if self.api_key:
                self.client = openai.OpenAI(api_key=self.api_key)
                self.available = True
            else:
                print("Warning: No OpenAI API key found. Please set OPENAI_API_KEY in .env file or environment.")
                self.available = False
        except ImportError:
            print("Warning: OpenAI library not installed. Please install: pip install openai")
            self.available = False
        except Exception as e:
            print(f"Warning: OpenAI client initialization failed: {e}")
            self.available = False
    
    def generate(self, prompt: str, **kwargs) -> str:
        """调用OpenAI API生成响应"""
        if not self.available:
            raise Exception("OpenAI client is not available. Please check your API key and internet connection.")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 2000)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")


class LLMInterface:
    """
    LLM调用统一接口
    
    提供统一的LLM调用方法，支持多种引擎和智能选择
    """
    
    def __init__(self, **engine_kwargs):
        """
        初始化LLM接口
        
        Args:
            engine_kwargs: OpenAI引擎参数（api_key, model等）
        """
        self.engine_type = "openai"
        self.engine = OpenAIEngine(**engine_kwargs)
        
        self.call_history: List[Dict[str, Any]] = []
    
    def call_llm(self, prompt: str, **kwargs) -> str:
        """
        统一的LLM调用方法
        
        Args:
            prompt: 输入prompt
            **kwargs: 额外参数
            
        Returns:
            LLM生成的响应
        """
        start_time = time.time()
        
        try:
            response = self.engine.generate(prompt, **kwargs)
            
            # 记录调用历史
            self.call_history.append({
                "timestamp": time.time(),
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "response": response[:200] + "..." if len(response) > 200 else response,
                "duration": time.time() - start_time,
                "success": True
            })
            
            return response
            
        except Exception as e:
            # 记录失败
            self.call_history.append({
                "timestamp": time.time(),
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "error": str(e),
                "duration": time.time() - start_time,
                "success": False
            })
            
            raise Exception(f"LLM call failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取LLM调用统计"""
        if not self.call_history:
            return {"total_calls": 0}
        
        successful_calls = [call for call in self.call_history if call.get("success", False)]
        
        return {
            "total_calls": len(self.call_history),
            "successful_calls": len(successful_calls),
            "success_rate": len(successful_calls) / len(self.call_history),
            "average_duration": sum(call.get("duration", 0) for call in successful_calls) / len(successful_calls) if successful_calls else 0,
            "engine_type": self.engine_type
        }


# 全局LLM接口实例
_llm_interface = None

def get_llm_interface() -> LLMInterface:
    """获取全局LLM接口实例"""
    global _llm_interface
    if _llm_interface is None:
        _llm_interface = LLMInterface()
    return _llm_interface


def call_llm(prompt: str, **kwargs) -> str:
    """
    便捷的LLM调用函数
    
    Args:
        prompt: 输入prompt
        **kwargs: 额外参数
        
    Returns:
        LLM生成的响应
    """
    return get_llm_interface().call_llm(prompt, **kwargs)


def configure_llm(**engine_kwargs):
    """
    配置LLM引擎
    
    Args:
        **engine_kwargs: OpenAI引擎参数（api_key, model等）
    """
    global _llm_interface
    _llm_interface = LLMInterface(**engine_kwargs)


# 示例使用
if __name__ == "__main__":
    # 测试OpenAI引擎
    interface = LLMInterface()  # 自动从.env读取API密钥
    
    response = interface.call_llm("Select next tool for quantum computing task")
    print(f"Response: {response}")
    
    stats = interface.get_stats()
    print(f"Stats: {stats}")