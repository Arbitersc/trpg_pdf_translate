"""
测试 Ollama 提供商
"""
import pytest
from unittest.mock import MagicMock, patch
from backend.llm.ollama import OllamaProvider
import requests


class TestOllamaProvider:
    """测试 OllamaProvider 类"""

    def test_init_success(self, ollama_config):
        """测试成功初始化"""
        provider = OllamaProvider(ollama_config)
        assert provider.base_url == 'http://localhost:11434'
        assert provider.model == 'llama3.2'
        assert provider.api_endpoint == 'http://localhost:11434/api/chat'

    def test_init_base_url_trailing_slash(self):
        """测试 base_url 末尾斜杠处理"""
        config = {
            'base_url': 'http://localhost:11434/',
            'model': 'llama3.2'
        }

        provider = OllamaProvider(config)
        assert provider.api_endpoint == 'http://localhost:11434/api/chat'

    def test_chat_completion_success(self, ollama_config, sample_messages, mock_requests_post):
        """测试成功的聊天补全"""
        # 修改 mock 返回 Ollama 格式
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {
                'content': 'Test response'
            },
            'prompt_eval_count': 10,
            'eval_count': 5
        }
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response):
            provider = OllamaProvider(ollama_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is True
            assert result['content'] == 'Test response'
            assert result['usage']['total_tokens'] == 15
            assert result['model'] == 'llama3.2'

    def test_chat_completion_with_temperature(self, ollama_config, sample_messages):
        """测试带有 temperature 参数的聊天补全"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {'content': 'Response'},
            'prompt_eval_count': 10,
            'eval_count': 5
        }
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response) as mock_post:
            provider = OllamaProvider(ollama_config)
            result = provider.chat_completion(sample_messages, temperature=0.7)

            assert result['success'] is True

            # 验证参数被正确传递到 options
            call_json = mock_post.call_args[1]['json']
            assert call_json['options']['temperature'] == 0.7

    def test_chat_completion_with_max_tokens(self, ollama_config, sample_messages):
        """测试带有 max_tokens 参数的聊天补全"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {'content': 'Response'},
            'prompt_eval_count': 10,
            'eval_count': 5
        }
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response) as mock_post:
            provider = OllamaProvider(ollama_config)
            result = provider.chat_completion(sample_messages, max_tokens=100)

            assert result['success'] is True

            # 验证参数被正确传递为 num_predict
            call_json = mock_post.call_args[1]['json']
            assert call_json['options']['num_predict'] == 100

    def test_chat_completion_with_top_p(self, ollama_config, sample_messages):
        """测试带有 top_p 参数的聊天补全"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {'content': 'Response'},
            'prompt_eval_count': 10,
            'eval_count': 5
        }
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response) as mock_post:
            provider = OllamaProvider(ollama_config)
            result = provider.chat_completion(sample_messages, top_p=0.9)

            assert result['success'] is True

            # 验证参数被正确传递
            call_json = mock_post.call_args[1]['json']
            assert call_json['options']['top_p'] == 0.9

    def test_chat_completion_invalid_messages(self, ollama_config):
        """测试无效消息列表"""
        provider = OllamaProvider(ollama_config)

        result = provider.chat_completion([])
        assert result['success'] is False
        assert 'error' in result

    def test_chat_completion_timeout(self, ollama_config, sample_messages):
        """测试请求超时"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            provider = OllamaProvider(ollama_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is False
            assert result['error'] == '请求超时，Ollama 服务可能响应较慢'

    def test_chat_completion_connection_error(self, ollama_config, sample_messages):
        """测试连接错误"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            provider = OllamaProvider(ollama_config)
            result = provider.chat_completion(sample_messages)

            assert result['success'] is False
            assert '无法连接到 Ollama 服务' in result['error']

    def test_test_connection_service_not_running(self, ollama_config):
        """测试 Ollama 服务未运行"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            provider = OllamaProvider(ollama_config)
            result = provider.test_connection()

            assert result['success'] is False
            assert '无法连接到 Ollama 服务' in result['message']

    def test_test_connection_success(self, ollama_config, mock_requests_get):
        """测试连接测试成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {'content': 'Hi'},
            'prompt_eval_count': 10,
            'eval_count': 5
        }
        mock_response.raise_for_status.return_value = None

        with patch('requests.post', return_value=mock_response):
            provider = OllamaProvider(ollama_config)
            result = provider.test_connection()

            assert result['success'] is True
            assert result['message'] == 'Ollama 服务连接成功'
            assert result['provider'] == 'ollama'
            assert result['model'] == 'llama3.2'

    def test_test_connection_failure(self, ollama_config, mock_requests_get):
        """测试连接测试失败"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            provider = OllamaProvider(ollama_config)
            result = provider.test_connection()

            assert result['success'] is False
            assert result['provider'] == 'ollama'

    def test_get_provider_name(self, ollama_config):
        """测试获取提供商名称"""
        provider = OllamaProvider(ollama_config)
        assert provider.get_provider_name() == 'ollama'

    def test_get_model_name(self, ollama_config):
        """测试获取模型名称"""
        provider = OllamaProvider(ollama_config)
        assert provider.get_model_name() == 'llama3.2'
