"""
Ollama 提供商实现
支持本地 Ollama 服务
"""
import requests
from typing import List, Dict, Any
from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Ollama 提供商"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Ollama 提供商

        Args:
            config: 配置字典，必须包含 base_url, model
        """
        super().__init__(config)

        # 构建 Ollama API URL
        self.api_endpoint = f"{self.base_url.rstrip('/')}/api/chat"

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        调用 Ollama 聊天 API

        Args:
            messages: 消息列表
            **kwargs: 额外参数，如 temperature, top_p, num_predict 等

        Returns:
            包含响应内容的字典
        """
        try:
            self._validate_messages(messages)

            # 构建请求参数
            params = {
                'model': self.model,
                'messages': messages,
                'stream': False,  # 关闭流式传输
                'options': {}
            }

            # 添加额外参数到 options
            if 'temperature' in kwargs:
                params['options']['temperature'] = kwargs['temperature']
            if 'max_tokens' in kwargs:
                params['options']['num_predict'] = kwargs['max_tokens']
            if 'top_p' in kwargs:
                params['options']['top_p'] = kwargs['top_p']

            # 发送请求
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.post(
                self.api_endpoint,
                json=params,
                headers=headers,
                timeout=120  # Ollama 本地服务可能响应较慢
            )

            response.raise_for_status()
            result = response.json()

            # 提取返回内容
            content = result.get('message', {}).get('content', '')

            return {
                'success': True,
                'content': content,
                'usage': {
                    'prompt_tokens': result.get('prompt_eval_count', 0),
                    'completion_tokens': result.get('eval_count', 0),
                    'total_tokens': result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                },
                'model': self.model,
                'raw_response': result
            }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': '请求超时，Ollama 服务可能响应较慢'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f'无法连接到 Ollama 服务 ({self.base_url})，请确认服务已启动'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'请求失败: {str(e)}'
            }
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        测试 Ollama 服务连接

        Returns:
            连接测试结果
        """
        try:
            # 首先检查 Ollama 服务是否运行
            tags_url = f"{self.base_url.rstrip('/')}/api/tags"
            try:
                response = requests.get(tags_url, timeout=5)
                response.raise_for_status()
            except requests.exceptions.ConnectionError:
                return {
                    'success': False,
                    'message': f'无法连接到 Ollama 服务 ({self.base_url})，请确认服务已启动',
                    'provider': self.get_provider_name()
                }

            # 发送一个简单的测试请求
            result = self.chat_completion(
                messages=[{'role': 'user', 'content': 'Hi'}],
                max_tokens=10
            )

            if result['success']:
                return {
                    'success': True,
                    'message': 'Ollama 服务连接成功',
                    'provider': self.get_provider_name(),
                    'model': self.model
                }
            else:
                return {
                    'success': False,
                    'message': result.get('error', '连接失败'),
                    'provider': self.get_provider_name()
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'连接测试失败: {str(e)}',
                'provider': self.get_provider_name()
            }
