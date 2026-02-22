"""
pytest 配置文件
提供测试所需的 fixtures 和通用配置
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_messages():
    """示例消息列表"""
    return [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Hello, how are you?'}
    ]


@pytest.fixture
def mock_response_success():
    """模拟成功的 API 响应"""
    return {
        'success': True,
        'content': 'This is a test response.',
        'usage': {
            'prompt_tokens': 10,
            'completion_tokens': 5,
            'total_tokens': 15
        },
        'model': 'test-model',
        'raw_response': {}
    }


@pytest.fixture
def openai_config():
    """OpenAI 配置"""
    return {
        'api_key': 'test-api-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini'
    }


@pytest.fixture
def ollama_config():
    """Ollama 配置"""
    return {
        'base_url': 'http://localhost:11434',
        'model': 'llama3.2'
    }


@pytest.fixture
def mock_requests_post():
    """模拟 requests.post"""
    with patch('requests.post') as mock:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test response'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5,
                'total_tokens': 15
            },
            'model': 'test-model'
        }
        mock_response.raise_for_status.return_value = None
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_requests_get():
    """模拟 requests.get"""
    with patch('requests.get') as mock:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'models': []
        }
        mock_response.raise_for_status.return_value = None
        mock.return_value = mock_response
        yield mock
