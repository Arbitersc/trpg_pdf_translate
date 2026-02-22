"""
LLM 服务工厂
根据配置创建对应的 LLM 服务实例
"""
from typing import Dict, Any, Optional
from .base import BaseLLMProvider
from .openai import OpenAIProvider
from .ollama import OllamaProvider


class LLMProviderFactory:
    """LLM 提供商工厂"""

    # 提供商映射
    _providers = {
        'openai': OpenAIProvider,
        'ollama': OllamaProvider
    }

    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> BaseLLMProvider:
        """
        根据配置创建 LLM 提供商实例

        Args:
            provider_type: 提供商类型 (openai/ollama)
            config: 配置字典

        Returns:
            LLM 提供商实例

        Raises:
            ValueError: 不支持的提供商类型
        """
        provider_class = cls._providers.get(provider_type.lower())

        if not provider_class:
            raise ValueError(f"不支持的 LLM 提供商: {provider_type}")

        try:
            return provider_class(config)
        except ValueError as e:
            raise ValueError(f"初始化 {provider_type} 提供商失败: {str(e)}")

    @classmethod
    def register_provider(cls, provider_type: str, provider_class: type) -> None:
        """
        注册新的 LLM 提供商

        Args:
            provider_type: 提供商类型名称
            provider_class: 提供商类（必须继承自 BaseLLMProvider）
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError("提供商类必须继承自 BaseLLMProvider")

        cls._providers[provider_type.lower()] = provider_class

    @classmethod
    def get_supported_providers(cls) -> list:
        """
        获取支持的提供商列表

        Returns:
            提供商类型列表
        """
        return list(cls._providers.keys())

    @classmethod
    def create_from_config(cls, config_obj) -> BaseLLMProvider:
        """
        从配置对象创建 LLM 提供商

        Args:
            config_obj: 配置对象（包含 LLM_PROVIDER, OPENAI_*, OLLAMA_* 等属性）

        Returns:
            LLM 提供商实例

        Raises:
            ValueError: 配置缺失或无效时
        """
        provider_type = config_obj.LLM_PROVIDER

        provider_configs = {
            'openai': {
                'api_key': config_obj.OPENAI_API_KEY,
                'base_url': config_obj.OPENAI_BASE_URL,
                'model': config_obj.OPENAI_MODEL
            },
            'ollama': {
                'base_url': config_obj.OLLAMA_BASE_URL,
                'model': config_obj.OLLAMA_MODEL
            }
        }

        config = provider_configs.get(provider_type)

        if not config:
            raise ValueError(f"未找到提供商 {provider_type} 的配置")

        # 验证配置值不为空
        if provider_type == 'openai':
            if not config.get('api_key'):
                raise ValueError(f"OpenAI 提供商需要配置环境变量 OPENAI_API_KEY")
            if not config.get('base_url'):
                raise ValueError(f"OpenAI 提供商需要配置环境变量 OPENAI_BASE_URL")
            if not config.get('model'):
                raise ValueError(f"OpenAI 提供商需要配置环境变量 OPENAI_MODEL")
        elif provider_type == 'ollama':
            if not config.get('base_url'):
                raise ValueError(f"Ollama 提供商需要配置环境变量 OLLAMA_BASE_URL")
            if not config.get('model'):
                raise ValueError(f"Ollama 提供商需要配置环境变量 OLLAMA_MODEL")

        return cls.create_provider(provider_type, config)


# 全局 LLM 服务实例（延迟初始化）
_llm_service: Optional[BaseLLMProvider] = None


def get_llm_service(config_obj) -> BaseLLMProvider:
    """
    获取 LLM 服务实例（单例模式）

    Args:
        config_obj: 配置对象

    Returns:
        LLM 提供商实例
    """
    global _llm_service

    if _llm_service is None:
        _llm_service = LLMProviderFactory.create_from_config(config_obj)

    return _llm_service


def reset_llm_service():
    """重置 LLM 服务实例（用于配置变更后重新初始化）"""
    global _llm_service
    _llm_service = None
