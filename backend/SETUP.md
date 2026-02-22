# 快速开始指南

## 配置环境变量（3步）

### 1. 复制配置示例

```bash
cd backend
cp .env.example .env
```

### 2. 编辑配置文件

```bash
# 编辑 .env 文件，至少配置以下必需项：
vim .env
```

**最简配置示例**（使用 OpenAI）：
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**使用硅基流动**：
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-siliconflow-api-key
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=Pro/zai-org/GLM-4.7
```

**使用本地 Ollama**：
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 3. 启动应用

```bash
# 安装依赖（首次运行）
pip install -r requirements.txt

# 启动后端
python app.py
```

## 运行测试

```bash
# 测试环境已自动配置，无需额外设置
pytest test/backend/
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `python app.py` | 启动后端服务 |
| `pytest test/` | 运行所有测试 |
| `pytest test/backend/test_openai.py` | 运行 OpenAI 提供商测试 |
| `pytest test/backend/test_ollama.py` | 运行 Ollama 提供商测试 |

## 文件说明

| 文件 | 说明 | 是否提交到 Git |
|------|------|---------------|
| `backend/.env` | 实际配置文件 | ❌ 不提交 |
| `backend/.env.example` | 配置示例 | ✅ 应提交 |
| `backend/.env.test.example` | 测试配置示例 | ✅ 应提交 |
| `test/.env` | 测试配置 | ❌ 不提交 |
| `backend/CONFIG.md` | 详细配置文档 | ✅ 应提交 |

## 安全检查

验证 .env 文件不会被意外提交：

```bash
# 检查 .gitignore 是否正确忽略
git check-ignore backend/.env
# 应输出: backend/.env

# 确认 .example 文件不会被忽略
git check-ignore backend/.env.example
# 应无输出（表示不会被忽略）
```

## 故障排除

### 问题：启动时提示配置错误

```
错误: LLM 配置验证失败，程序终止
配置验证失败:
  - OpenAI 提供商需要配置环境变量 OPENAI_API_KEY
```

**解决**：检查 `backend/.env` 文件，确保已配置 `OPENAI_API_KEY`

### 问题：测试失败

**解决**：测试环境使用 mock，无需真实 API 密钥。如果测试失败，检查是否正确安装了依赖：

```bash
pip install -r requirements.txt
```

### 问题：API 调用失败

**解决**：
1. 确认 API 密钥正确
2. 检查网络连接
3. 验证 base_url 是否正确
4. 查看应用日志中的错误信息

## 获取更多帮助

- 详细配置说明：查看 `backend/CONFIG.md`
- API 文档：访问 `http://localhost:5000/` 查看 API 端点
- 健康检查：访问 `http://localhost:5000/health`
