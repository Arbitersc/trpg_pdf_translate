"""
配置管理模块
从环境变量加载应用程序配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用程序配置类"""

    # LLM Provider Configuration
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    # Ollama Configuration
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')

    # Supported providers
    SUPPORTED_PROVIDERS = ['openai', 'ollama']

    @classmethod
    def validate(cls):
        """验证配置是否有效"""
        errors = []

        if cls.LLM_PROVIDER not in cls.SUPPORTED_PROVIDERS:
            errors.append(f"不支持的 LLM 提供商: {cls.LLM_PROVIDER}. 支持的提供商: {cls.SUPPORTED_PROVIDERS}")

        if cls.LLM_PROVIDER == 'openai':
            if not cls.OPENAI_API_KEY:
                errors.append("OpenAI 提供商需要配置环境变量 OPENAI_API_KEY")

        if cls.LLM_PROVIDER == 'ollama':
            if not cls.OLLAMA_BASE_URL:
                errors.append("Ollama 提供商需要配置环境变量 OLLAMA_BASE_URL")

        if errors:
            error_msg = "\n  - ".join(["配置验证失败:"] + errors)
            raise RuntimeError(error_msg)

    @classmethod
    def get_provider_config(cls, provider):
        """获取指定提供商的配置（不包含敏感信息）"""
        configs = {
            'openai': {
                'provider': 'openai',
                'base_url': cls.OPENAI_BASE_URL,
                'model': cls.OPENAI_MODEL,
                'api_key_configured': bool(cls.OPENAI_API_KEY)
            },
            'ollama': {
                'provider': 'ollama',
                'base_url': cls.OLLAMA_BASE_URL,
                'model': cls.OLLAMA_MODEL
            }
        }
        return configs.get(provider)


# 全局配置实例
config = Config()
