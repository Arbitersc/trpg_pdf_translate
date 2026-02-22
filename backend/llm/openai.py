"""
OpenAI 兼容提供商实现
支持 OpenAI API 及兼容格式的 API（如 Azure OpenAI、硅基流动、自定义 OpenAI 兼容 API）
"""
import requests
from typing import List, Dict, Any
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 兼容提供商"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 OpenAI 提供商

        Args:
            config: 配置字典，必须包含 api_key, base_url, model
        """
        super().__init__(config)
        self.api_key = config.get('api_key')

        if not self.api_key:
            raise ValueError("提供商需要配置 api_key")

        # 构建完整的 API URL
        self.api_endpoint = f"{self.base_url.rstrip('/')}/chat/completions"

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        调用 OpenAI 聊天补全 API

        Args:
            messages: 消息列表
            **kwargs: 额外参数，如 temperature, max_tokens, top_p 等

        Returns:
            包含响应内容的字典
        """
        try:
            self._validate_messages(messages)

            # 构建请求参数
            params = {
                'model': self.model,
                'messages': messages,
                **kwargs
            }

            # 发送请求
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                self.api_endpoint,
                json=params,
                headers=headers,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            # 提取返回内容
            content = result['choices'][0]['message']['content']

            return {
                'success': True,
                'content': content,
                'usage': result.get('usage', {}),
                'model': result.get('model'),
                'raw_response': result
            }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': '请求超时'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'请求失败: {str(e)}'
            }
        except (KeyError, IndexError) as e:
            return {
                'success': False,
                'error': f'解析响应失败: {str(e)}'
            }
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        测试 OpenAI API 连接

        Returns:
            连接测试结果
        """
        try:
            # 发送一个简单的测试请求
            result = self.chat_completion(
                messages=[{'role': 'user', 'content': 'Hi'}],
                max_tokens=10
            )

            if result['success']:
                return {
                    'success': True,
                    'message': 'API 连接成功',
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
