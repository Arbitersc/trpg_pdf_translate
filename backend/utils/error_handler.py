"""
错误处理工具
提供标准化的错误响应和日志记录
"""
import logging
from typing import Tuple, Any, Optional
from flask import jsonify
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def error_response(message: str, status_code: int = 500, error_code: Optional[str] = None) -> Tuple[Any, int]:
    """
    生成标准化的错误响应

    Args:
        message: 错误消息
        status_code: HTTP 状态码
        error_code: 错误代码（可选）

    Returns:
        Flask JSON 响应和状态码的元组
    """
    logger.error(f"Error: {message} (Code: {error_code}, Status: {status_code})")

    response = {
        'success': False,
        'error': message
    }

    if error_code:
        response['error_code'] = error_code

    return jsonify(response), status_code


def success_response(data: Any, status_code: int = 200) -> Tuple[Any, int]:
    """
    生成标准化的成功响应

    Args:
        data: 响应数据
        status_code: HTTP 状态码

    Returns:
        Flask JSON 响应和状态码的元组
    """
    return jsonify({
        'success': True,
        'data': data
    }), status_code


def handle_errors(f):
    """
    错误处理装饰器
    自动捕获异常并返回标准化的错误响应

    使用示例:
        @app.route('/api/test')
        @handle_errors
        def test():
            # 你的代码
            return success_response({'result': 'ok'})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return error_response(str(e), 400, 'VALIDATION_ERROR')
        except KeyError as e:
            return error_response(f'缺少必需的参数: {str(e)}', 400, 'MISSING_PARAMETER')
        except ConnectionError as e:
            return error_response(f'连接错误: {str(e)}', 503, 'CONNECTION_ERROR')
        except TimeoutError as e:
            return error_response(f'请求超时: {str(e)}', 504, 'TIMEOUT_ERROR')
        except Exception as e:
            logger.exception(f"Unexpected error in {f.__name__}")
            return error_response(f'服务器内部错误: {str(e)}', 500, 'INTERNAL_ERROR')
    return wrapper


def log_request(request, endpoint: str):
    """
    记录请求日志

    Args:
        request: Flask 请求对象
        endpoint: 端点名称
    """
    logger.info(f"Request: {request.method} {request.url} ({endpoint})")
    if request.is_json:
        logger.debug(f"Request body: {request.get_json()}")
