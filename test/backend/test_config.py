"""
测试配置系统
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from backend.config import Config
from backend.llm.factory import LLMProviderFactory, get_llm_service, reset_llm_service
from backend.llm.openai import OpenAIProvider
from backend.llm.ollama import OllamaProvider


class TestConfig:
    """测试 Config 类"""

    def test_default_values_exist(self):
        """测试配置值存在"""
        assert Config.LLM_PROVIDER in ['openai', 'ollama']
        assert Config.OPENAI_BASE_URL
        assert Config.OPENAI_MODEL
        assert Config.OLLAMA_BASE_URL
        assert Config.OLLAMA_MODEL
        assert Config.SUPPORTED_PROVIDERS == ['openai', 'ollama']

    def test_validate_with_openai_provider(self):
        """测试验证 OpenAI 提供商配置"""
        with patch.object(Config, 'OPENAI_API_KEY', 'test-api-key'):
            # 应该通过验证
            Config.validate()

    def test_validate_with_ollama_provider(self):
        """测试验证 Ollama 提供商配置"""
        with patch.object(Config, 'LLM_PROVIDER', 'ollama'):
            # 应该通过验证
            Config.validate()

    def test_validate_missing_openai_api_key(self):
        """测试缺少 OpenAI API Key 时验证失败"""
        with patch.object(Config, 'OPENAI_API_KEY', ''):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                Config.validate()

    def test_validate_unsupported_provider(self):
        """测试不支持的提供商"""
        with patch.object(Config, 'LLM_PROVIDER', 'unsupported'):
            with pytest.raises(RuntimeError, match="不支持的 LLM 提供商"):
                Config.validate()

    def test_get_provider_config_openai(self):
        """测试获取 OpenAI 提供商配置"""
        with patch.object(Config, 'OPENAI_API_KEY', 'test-key'):
            config = Config.get_provider_config('openai')
            assert config['provider'] == 'openai'
            assert config['base_url'] == Config.OPENAI_BASE_URL
            assert config['model'] == Config.OPENAI_MODEL
            assert config['api_key_configured'] is True

    def test_get_provider_config_ollama(self):
        """测试获取 Ollama 提供商配置"""
        config = Config.get_provider_config('ollama')
        assert config['provider'] == 'ollama'
        assert config['base_url'] == Config.OLLAMA_BASE_URL
        assert config['model'] == Config.OLLAMA_MODEL

    def test_get_provider_config_invalid(self):
        """测试获取不存在的提供商配置"""
        config = Config.get_provider_config('invalid')
        assert config is None


class TestLLMProviderFactory:
    """测试 LLM 提供商工厂"""

    def test_create_openai_provider(self):
        """测试创建 OpenAI 提供商"""
        config = {
            'api_key': 'test-api-key',
            'base_url': 'https://api.openai.com/v1',
            'model': 'gpt-4o-mini'
        }
        provider = LLMProviderFactory.create_provider('openai', config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == 'test-api-key'

    def test_create_ollama_provider(self):
        """测试创建 Ollama 提供商"""
        config = {
            'base_url': 'http://localhost:11434',
            'model': 'llama3.2'
        }
        provider = LLMProviderFactory.create_provider('ollama', config)
        assert isinstance(provider, OllamaProvider)
        assert provider.base_url == 'http://localhost:11434'

    def test_create_provider_invalid(self):
        """测试创建不支持的提供商"""
        with pytest.raises(ValueError, match="不支持的 LLM 提供商"):
            LLMProviderFactory.create_provider('invalid', {})

    def test_get_supported_providers(self):
        """测试获取支持的提供商列表"""
        providers = LLMProviderFactory.get_supported_providers()
        assert 'openai' in providers
        assert 'ollama' in providers

    def test_create_from_config_openai(self):
        """测试从配置对象创建 OpenAI 提供商"""
        mock_config = MagicMock()
        mock_config.LLM_PROVIDER = 'openai'
        mock_config.OPENAI_API_KEY = 'test-api-key'
        mock_config.OPENAI_BASE_URL = 'https://api.openai.com/v1'
        mock_config.OPENAI_MODEL = 'gpt-4o-mini'

        provider = LLMProviderFactory.create_from_config(mock_config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == 'test-api-key'

    def test_create_from_config_ollama(self):
        """测试从配置对象创建 Ollama 提供商"""
        mock_config = MagicMock()
        mock_config.LLM_PROVIDER = 'ollama'
        mock_config.OLLAMA_BASE_URL = 'http://localhost:11434'
        mock_config.OLLAMA_MODEL = 'llama3.2'

        provider = LLMProviderFactory.create_from_config(mock_config)
        assert isinstance(provider, OllamaProvider)
        assert provider.base_url == 'http://localhost:11434'

    def test_create_from_config_missing_openai_api_key(self):
        """测试创建 OpenAI 提供商时缺少 API Key"""
        mock_config = MagicMock()
        mock_config.LLM_PROVIDER = 'openai'
        mock_config.OPENAI_API_KEY = ''
        mock_config.OPENAI_BASE_URL = 'https://api.openai.com/v1'
        mock_config.OPENAI_MODEL = 'gpt-4o-mini'

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            LLMProviderFactory.create_from_config(mock_config)

    def test_create_from_config_missing_ollama_base_url(self):
        """测试创建 Ollama 提供商时缺少 base_url"""
        mock_config = MagicMock()
        mock_config.LLM_PROVIDER = 'ollama'
        mock_config.OLLAMA_BASE_URL = ''
        mock_config.OLLAMA_MODEL = 'llama3.2'

        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            LLMProviderFactory.create_from_config(mock_config)


class TestLLMServiceSingleton:
    """测试 LLM 服务单例"""

    def test_get_llm_service_singleton(self):
        """测试单例模式"""
        mock_config = MagicMock()
        mock_config.LLM_PROVIDER = 'ollama'
        mock_config.OLLAMA_BASE_URL = 'http://localhost:11434'
        mock_config.OLLAMA_MODEL = 'llama3.2'

        reset_llm_service()
        provider1 = get_llm_service(mock_config)
        provider2 = get_llm_service(mock_config)

        # 应该返回同一个实例
        assert provider1 is provider2
        assert isinstance(provider1, OllamaProvider)

    def test_reset_llm_service(self):
        """测试重置 LLM 服务"""
        mock_config = MagicMock()
        mock_config.LLM_PROVIDER = 'ollama'
        mock_config.OLLAMA_BASE_URL = 'http://localhost:11434'
        mock_config.OLLAMA_MODEL = 'llama3.2'

        provider1 = get_llm_service(mock_config)
        reset_llm_service()
        provider2 = get_llm_service(mock_config)

        # 重置后应该是不同的实例
        assert provider1 is not provider2

    def test_get_llm_service_integration_with_config(self):
        """测试 get_llm_service 与 Config 的集成"""
        # 使用 Config 类创建提供商
        reset_llm_service()
        provider = get_llm_service(Config)

        # 验证提供商类型正确
        assert provider.get_provider_name() == Config.LLM_PROVIDER

        # 如果是 OpenAI，验证模型名称
        if Config.LLM_PROVIDER == 'openai':
            assert provider.get_model_name() == Config.OPENAI_MODEL
        elif Config.LLM_PROVIDER == 'ollama':
            assert provider.get_model_name() == Config.OLLAMA_MODEL
