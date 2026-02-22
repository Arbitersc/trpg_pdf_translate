# 环境变量配置指南

本文档说明如何配置 `.env` 文件，确保生产、开发和测试环境的安全性。

## 文件结构

```
backend/
├── .env                 # 实际环境配置（**不要提交到 Git**）
├── .env.example         # 生产/开发环境配置示例
├── .env.test.example    # 测试环境配置示例
test/
├── .env                 # 测试环境配置（**不要提交到 Git**）
```

## 配置步骤

### 1. 创建环境配置文件

```bash
# 进入 backend 目录
cd backend

# 从示例文件复制
cp .env.example .env

# 编辑 .env 文件，填入实际配置
vim .env  # 或使用其他编辑器
```

### 2. 配置 LLM 提供商

#### 使用 OpenAI 官方 API

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

#### 使用硅基流动 (SiliconFlow)

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-siliconflow-api-key
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=Pro/zai-org/GLM-4.7
```

#### 使用智谱 AI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-zhipu-ai-api-key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4-flash
```

#### 使用本地 Ollama

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 3. 配置 Flask 应用

开发环境（默认）：

```bash
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

生产环境：

```bash
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### 4. 启动应用

```bash
# 确保 Python 依赖已安装
pip install -r requirements.txt

# 启动后端服务
python app.py
```

## 测试环境配置

测试环境使用独立的配置文件，确保测试不影响生产环境。

```bash
# 测试配置已自动创建在 test/.env
# 测试使用 mock，不需要真实的 API 密钥

# 运行测试
pytest test/
```

## 安全注意事项

### ✅ 应该提交到 Git

- `.env.example` - 配置示例，不包含敏感信息
- `.env.test.example` - 测试配置示例
- 所有 `.env.example` 文件

### ❌ 不应提交到 Git

- `.env` - 包含真实密钥的配置文件
- `.env.*` - 除 `.example` 外的所有环境配置文件
- `.envrc` - direnv 配置文件

### ✅ 已在 `.gitignore` 中忽略

```
.env
.env.*
.envrc
backend/.env
test/.env
test/.env.*
```

## 常见问题

### Q: 如何获取 API 密钥？

**OpenAI 官方**: https://platform.openai.com/api-keys

**硅基流动**: https://siliconflow.cn/account/ak

**智谱 AI**: https://open.bigmodel.cn/usercenter/apikeys

### Q: 如何检查配置是否生效？

```bash
# 启动应用时会显示配置信息
python app.py
```

输出示例：
```
==================================================
PDF服务后端启动中...
PDF文件目录: /path/to/backend/pdfs
==================================================
LLM 提供商: openai
OpenAI 模型: gpt-4o-mini
OpenAI Base URL: https://api.openai.com/v1
API Key 已配置: 是
==================================================
```

### Q: 配置错误时会发生什么？

如果必需的环境参数缺失，应用会显示详细的错误信息并退出：

```
==================================================
错误: LLM 配置验证失败，程序终止
配置验证失败:
  - OpenAI 提供商需要配置环境变量 OPENAI_API_KEY

请在 .env 文件或环境变量中配置以下参数：
  LLM_PROVIDER: openai
  OPENAI_API_KEY: 您的 OpenAI API 密钥
  OPENAI_BASE_URL: API 基础 URL (默认: https://api.openai.com/v1)
  OPENAI_MODEL: 模型名称 (默认: gpt-4o-mini)
==================================================
```

### Q: 如何在不同环境间切换？

方法 1: 使用不同的配置文件
```bash
# 开发环境
cp .env.example .env.development
cp .env.development .env

# 生产环境
cp .env.example .env.production
# 编辑 .env.production 填入生产配置
cp .env.production .env
```

方法 2: 使用环境变量覆盖
```bash
# 临时覆盖
FLASK_DEBUG=false python app.py

# 或使用 export
export FLASK_DEBUG=false
python app.py
```

## 生产环境部署建议

1. **使用环境变量而非 .env 文件**
   ```bash
   export OPENAI_API_KEY="your-production-key"
   export LLM_PROVIDER="openai"
   python app.py
   ```

2. **使用密钥管理服务**
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault

3. **设置适当的文件权限**
   ```bash
   chmod 600 backend/.env
   ```

4. **启用 HTTPS**
   - 使用反向代理（Nginx、Apache）
   - 配置 SSL/TLS 证书
