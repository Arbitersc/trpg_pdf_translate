"""
LLM 服务抽象基类
定义统一的 LLM 服务接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """LLM 服务抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 提供商

        Args:
            config: 提供商配置字典
        """
        self.config = config
        self.base_url = config.get('base_url')
        self.model = config.get('model')

    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        聊天补全接口

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数，如 temperature, max_tokens 等

        Returns:
            包含响应内容的字典
            {
                "success": True/False,
                "content": "回复内容",
                "usage": {...},  # 可选
                "raw_response": {...}  # 可选
            }
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接是否正常

        Returns:
            {
                "success": True/False,
                "message": "连接成功/失败原因",
                "provider": "提供商名称"
            }
        """
        pass

    def _validate_messages(self, messages: List[Dict[str, str]]) -> None:
        """
        验证消息格式

        Args:
            messages: 消息列表

        Raises:
            ValueError: 消息格式无效时抛出
        """
        if not messages:
            raise ValueError("消息列表不能为空")

        if not isinstance(messages, list):
            raise ValueError("消息必须是列表格式")

        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError("每条消息必须是字典格式")

            if 'role' not in msg or 'content' not in msg:
                raise ValueError("每条消息必须包含 'role' 和 'content' 字段")

            if msg['role'] not in ['system', 'user', 'assistant']:
                raise ValueError(f"不支持的消息角色: {msg['role']}")

    def get_provider_name(self) -> str:
        """获取提供商名称"""
        return self.__class__.__name__.replace('Provider', '').lower()

    def get_model_name(self) -> str:
        """获取当前模型名称"""
        return self.model
