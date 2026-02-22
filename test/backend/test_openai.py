"""
测试 OpenAI 兼容提供商
"""
import pytest
from unittest.mock import MagicMock, patch
from backend.llm.openai import OpenAIProvider
import requests


class TestOpenAIProvider:
    """测试 OpenAIProvider 类"""

    def test_init_success(self, openai_config):
        """测试成功初始化"""
        provider = OpenAIProvider(openai_config)
        assert provider.api_key == 'test-api-key'
        assert provider.base_url == 'https://api.openai.com/v1'
        assert provider.model == 'gpt-4o-mini'
        assert provider.api_endpoint == 'https://api.openai.com/v1/chat/completions'

    def test_init_missing_api_key(self):
        """测试缺少 API Key 时初始化失败"""
        config = {'base_url': 'https://api.openai.com/v1', 'model': 'gpt-4o-mini'}

        with pytest.raises(ValueError, match="提供商需要配置 api_key"):
            OpenAIProvider(config)

    def test_init_base_url_trailing_slash(self):
        """测试 base_url 末尾斜杠处理"""
        config = {
            'api_key': 'test-key',
            'base_url': 'https://api.openai.com/v1/',
            'model': 'gpt-4o-mini'
        }

        provider = OpenAIProvider(config)
        assert provider.api_endpoint == 'https://api.openai.com/v1/chat/completions'

    def test_chat_completion_success(self, openai_config, sample_messages, mock_requests_post):
        """测试成功的聊天补全"""
        provider = OpenAIProvider(openai_config)

        result = provider.chat_completion(sample_messages)

        assert result['success'] is True
        assert result['content'] == 'Test response'
        assert result['usage']['total_tokens'] == 15
        assert result['model'] == 'test-model'

        # 验证请求参数
        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args
        assert call_args[0][0] == provider.api_endpoint
        assert call_args[1]['json']['model'] == 'gpt-4o-mini'
        assert call_args[1]['json']['messages'] == sample_messages

    def test_chat_completion_with_kwargs(self, openai_config, sample_messages, mock_requests_post):
        """测试带有额外参数的聊天补全"""
        provider = OpenAIProvider(openai_config)

        result = provider.chat_completion(
            sample_messages,
            temperature=0.7,
            max_tokens=100
        )

        assert result['success'] is True

        # 验证额外参数被传递
        call_kwargs = mock_requests_post.call_args[1]['json']
        assert call_kwargs['temperature'] == 0.7
        assert call_kwargs['max_tokens'] == 100

    def test_chat_completion_invalid_messages(self, openai_config):
        """测试无效消息列表"""
        provider = OpenAIProvider(openai_config)

        result = provider.chat_completion([])
        assert result['success'] is False
        assert 'error' in result

    def test_chat_completion_timeout(self, openai_config, sample_messages):
        """测试请求超时"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            provider = OpenAIProvider(openai_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is False
            assert result['error'] == '请求超时'

    def test_chat_connection_error(self, openai_config, sample_messages):
        """测试连接错误"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            provider = OpenAIProvider(openai_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is False
            assert '请求失败' in result['error']

    def test_chat_completion_http_error(self, openai_config, sample_messages):
        """测试 HTTP 错误"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
            mock_post.return_value = mock_response

            provider = OpenAIProvider(openai_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is False
            assert '请求失败' in result['error']

    def test_chat_completion_invalid_response(self, openai_config, sample_messages):
        """测试无效的响应格式"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {}  # 空响应
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            provider = OpenAIProvider(openai_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is False
            assert '解析响应失败' in result['error']

    def test_test_connection_success(self, openai_config, mock_requests_post):
        """测试连接测试成功"""
        provider = OpenAIProvider(openai_config)

        result = provider.test_connection()

        assert result['success'] is True
        assert result['message'] == 'API 连接成功'
        assert result['provider'] == 'openai'
        assert result['model'] == 'gpt-4o-mini'

    def test_test_connection_failure(self, openai_config):
        """测试连接测试失败"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            provider = OpenAIProvider(openai_config)
            result = provider.test_connection()

            assert result['success'] is False
            assert result['provider'] == 'openai'

    def test_get_provider_name(self, openai_config):
        """测试获取提供商名称"""
        provider = OpenAIProvider(openai_config)
        assert provider.get_provider_name() == 'openai'

    def test_get_model_name(self, openai_config):
        """测试获取模型名称"""
        provider = OpenAIProvider(openai_config)
        assert provider.get_model_name() == 'gpt-4o-mini'
