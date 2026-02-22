"""
Flask后端服务 - 提供PDF文件API和LLM服务
"""
from flask import Flask, send_file, jsonify, request
from flask_cors import CORS
import os

# 导入配置和LLM模块
from config import config
from llm.factory import get_llm_service, reset_llm_service, LLMProviderFactory
from utils.error_handler import error_response, success_response, handle_errors, log_request

app = Flask(__name__)
CORS(app)  # 允许跨域请求


# 验证配置 - 如果配置错误则终止程序
try:
    config.validate()
except RuntimeError as e:
    print("=" * 60)
    print("错误: LLM 配置验证失败，程序终止")
    print(str(e))
    print("\n请在 .env 文件或环境变量中配置以下参数：")
    print(f"  LLM_PROVIDER: {config.LLM_PROVIDER}")

    if config.LLM_PROVIDER == 'openai':
        print("  OPENAI_API_KEY: 您的 OpenAI API 密钥")
        print("  OPENAI_BASE_URL: API 基础 URL (默认: https://api.openai.com/v1)")
        print("  OPENAI_MODEL: 模型名称 (默认: gpt-4o-mini)")
    elif config.LLM_PROVIDER == 'ollama':
        print("  OLLAMA_BASE_URL: Ollama 服务地址 (默认: http://localhost:11434)")
        print("  OLLAMA_MODEL: 模型名称 (默认: llama3.2)")

    print("=" * 60)
    import sys
    sys.exit(1)

# PDF文件存储目录
PDF_DIRECTORY = 'pdfs'

# 确保PDF目录存在
os.makedirs(PDF_DIRECTORY, exist_ok=True)


@app.route('/')
def index():
    """首页"""
    return jsonify({
        'message': 'PDF服务后端API',
        'endpoints': {
            'list_pdfs': '/api/pdfs - 获取所有PDF文件列表',
            'get_pdf': '/api/pdf/<filename> - 下载指定PDF文件',
            'health': '/health - 健康检查',
            'llm_providers': '/api/llm/providers - 获取支持的LLM提供商列表',
            'llm_config': '/api/llm/config - 获取当前LLM配置',
            'llm_test': '/api/llm/test - 测试LLM连接 (POST)',
            'llm_chat': '/api/llm/chat - LLM聊天补全 (POST)'
        }
    })


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})


@app.route('/api/pdfs', methods=['GET'])
def list_pdfs():
    """获取所有PDF文件列表"""
    try:
        pdf_files = []
        for filename in os.listdir(PDF_DIRECTORY):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(PDF_DIRECTORY, filename)
                pdf_files.append({
                    'filename': filename,
                    'size': os.path.getsize(file_path),
                    'url': f'/api/pdf/{filename}'
                })
        return jsonify({
            'success': True,
            'count': len(pdf_files),
            'files': pdf_files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/pdf/<filename>', methods=['GET'])
def get_pdf(filename):
    """下载指定PDF文件"""
    try:
        file_path = os.path.join(PDF_DIRECTORY, filename)

        # 安全检查：确保文件在PDF目录中
        if not os.path.abspath(file_path).startswith(os.path.abspath(PDF_DIRECTORY)):
            return jsonify({'error': '非法的文件路径'}), 400

        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(file_path, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ LLM API 端点 ============


@app.route('/api/llm/providers', methods=['GET'])
def get_providers():
    """获取支持的 LLM 提供商列表"""
    try:
        providers = []
        for provider in LLMProviderFactory.get_supported_providers():
            provider_info = config.get_provider_config(provider)
            if provider_info:
                providers.append(provider_info)

        return jsonify({
            'success': True,
            'providers': providers,
            'current_provider': config.LLM_PROVIDER
        })
    except Exception as e:
        return error_response(f'获取提供商列表失败: {str(e)}')


@app.route('/api/llm/config', methods=['GET'])
def get_llm_config():
    """获取当前 LLM 配置（不暴露敏感信息）"""
    try:
        provider_config = config.get_provider_config(config.LLM_PROVIDER)
        if not provider_config:
            return error_response(f'无效的提供商: {config.LLM_PROVIDER}', 400, 'INVALID_PROVIDER')

        return jsonify({
            'success': True,
            'provider': config.LLM_PROVIDER,
            'config': provider_config
        })
    except Exception as e:
        return error_response(f'获取配置失败: {str(e)}')


@app.route('/api/llm/test', methods=['POST'])
@handle_errors
def test_llm():
    """测试 LLM 连接"""
    log_request(request, '/api/llm/test')

    try:
        llm_service = get_llm_service(config)
        result = llm_service.test_connection()

        if result['success']:
            return success_response(result)
        else:
            return error_response(result.get('message', '连接测试失败'), 503, 'CONNECTION_FAILED')
    except ValueError as e:
        return error_response(f'LLM 配置错误: {str(e)}', 400, 'CONFIG_ERROR')
    except Exception as e:
        return error_response(f'测试连接失败: {str(e)}', 500, 'TEST_ERROR')


@app.route('/api/llm/chat', methods=['POST'])
@handle_errors
def chat_completion():
    """LLM 聊天补全接口"""
    log_request(request, '/api/llm/chat')

    # 验证请求体
    if not request.is_json:
        return error_response('请求体必须是 JSON 格式', 400, 'INVALID_REQUEST')

    data = request.get_json()

    # 验证必需参数
    messages = data.get('messages')
    if not messages:
        return error_response('缺少必需参数: messages', 400, 'MISSING_PARAMETER')

    try:
        llm_service = get_llm_service(config)

        # 提取可选参数
        kwargs = {}
        if 'temperature' in data:
            kwargs['temperature'] = float(data['temperature'])
        if 'max_tokens' in data:
            kwargs['max_tokens'] = int(data['max_tokens'])
        if 'top_p' in data:
            kwargs['top_p'] = float(data['top_p'])

        # 调用 LLM
        result = llm_service.chat_completion(messages, **kwargs)

        if result['success']:
            return success_response(result)
        else:
            return error_response(result.get('error', '调用失败'), 500, 'LLM_ERROR')
    except ValueError as e:
        return error_response(f'LLM 配置错误: {str(e)}', 400, 'CONFIG_ERROR')
    except Exception as e:
        return error_response(f'调用 LLM 失败: {str(e)}', 500, 'CHAT_ERROR')


@app.route('/api/llm/config', methods=['POST'])
@handle_errors
def update_llm_config():
    """更新 LLM 配置（仅更新环境变量，需要重启服务生效）"""
    log_request(request, '/api/llm/config')

    if not request.is_json:
        return error_response('请求体必须是 JSON 格式', 400, 'INVALID_REQUEST')

    data = request.get_json()

    # 验证提供商类型
    provider = data.get('provider')
    if not provider:
        return error_response('缺少必需参数: provider', 400, 'MISSING_PARAMETER')

    if provider not in config.SUPPORTED_PROVIDERS:
        return error_response(
            f'不支持的提供商: {provider}. 支持的提供商: {config.SUPPORTED_PROVIDERS}',
            400,
            'INVALID_PROVIDER'
        )

    # 返回配置建议（实际配置需要通过 .env 文件或环境变量）
    return jsonify({
        'success': True,
        'message': '配置已验证，请通过 .env 文件或环境变量更新配置，然后重启服务',
        'suggested_config': {
            'LLM_PROVIDER': provider,
            'note': '请根据提供商配置相应的环境变量',
            'openai': {
                'env_vars': ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL']
            },
            'ollama': {
                'env_vars': ['OLLAMA_BASE_URL', 'OLLAMA_MODEL']
            }
        }
    })


if __name__ == '__main__':
    print("=" * 50)
    print("PDF服务后端启动中...")
    print(f"PDF文件目录: {os.path.abspath(PDF_DIRECTORY)}")
    print("=" * 50)
    print(f"LLM 提供商: {config.LLM_PROVIDER}")

    if config.LLM_PROVIDER == 'openai':
        print(f"OpenAI 模型: {config.OPENAI_MODEL}")
        print(f"OpenAI Base URL: {config.OPENAI_BASE_URL}")
        print(f"API Key 已配置: {'是' if config.OPENAI_API_KEY else '否'}")
    elif config.LLM_PROVIDER == 'ollama':
        print(f"Ollama 模型: {config.OLLAMA_MODEL}")
        print(f"Ollama 地址: {config.OLLAMA_BASE_URL}")

    print("=" * 50)
    print("请将PDF文件放在pdfs/目录下")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
