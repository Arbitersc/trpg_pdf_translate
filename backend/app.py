"""
Flask后端服务 - 提供PDF文件API
"""
from flask import Flask, send_file, jsonify, render_template
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

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
            'health': '/health - 健康检查'
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


if __name__ == '__main__':
    print("=" * 50)
    print("PDF服务后端启动中...")
    print(f"PDF文件目录: {os.path.abspath(PDF_DIRECTORY)}")
    print("请将PDF文件放在pdfs/目录下")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
