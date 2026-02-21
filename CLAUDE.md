# CLAUDE.md - TRPG PDF 翻译器

## WHAT: Project Overview

TRPG PDF 翻译器是一个针对桌上角色扮演游戏（TRPG）PDF 文本的翻译工具，通过大语言模型翻译生成结果文件。

项目包含一个基于前后端分离架构的 PDF 在线阅读器。

**Tech Stack**: Vue 3 · Vite · PDF.js · Element Plus · Tailwind CSS · Python 3 · Flask · Flask-CORS

**Core Directories**:

- `backend/` - Flask 后端服务
  - `app.py` - Flask 应用主文件
  - `requirements.txt` - Python 依赖
- `frontend/` - Vue 3 前端页面
  - `src/` - Vue 源代码
  - `index.html` - HTML 模板
  - `package.json` - 前端依赖配置
  - `vite.config.js` - Vite 配置
- `test/` - 测试目录
  - `backend/` - 后端测试
  - `frontend/` - 前端测试
- `.claude/` - Claude Code 配置
  - `agents/` - Agent 配置

## WHY: Purpose

- 为 TRPG 游戏玩家提供 PDF 规则书的翻译功能
- 提供在线 PDF 阅读器，支持翻页和术语查看
- 前后端分离架构，便于开发和部署
- 支持大语言模型进行智能翻译

## HOW: Core Commands

```bash
# Backend Setup
cd backend
pip install -r requirements.txt          # Install Python dependencies
python app.py                            # Start backend (port 5000)

# Frontend Setup
cd frontend
npm install                              # Install Node.js dependencies
npm run dev                              # Start dev server (port 8000)
npm run build                            # Build for production

# Testing
pytest test/                             # Run backend tests
npm test                                 # Run frontend tests

# Check services
curl http://localhost:5000/health        # Check backend health
curl http://localhost:5000/api/pdfs      # List PDF files
```

**Critical Startup Sequence**:
1. Start backend first (`python app.py` from `backend/` directory)
2. Wait for backend to be ready (port 5000)
3. Then start frontend (`npm run dev` from `frontend/` directory)

## Boundaries

### Constraints

- 前端和后端必须分别启动，后端先于前端
- 后端端口固定为 5000，前端端口为 8000
- PDF 文件必须放置在 `backend/pdfs/` 目录
- 需要跨域支持（CORS）已通过 Flask-CORS 配置
- 当前使用 React（非 Vue 3，package.json 显示为 React）

### Always Do

- 读取相关文件后再修改代码
- 确保后端服务在端口 5000 运行后再测试前端
- 遵循现有代码模式
- 新功能添加相应测试
- 提交前运行相关测试

### Ask First

- 修改后端 API 端点结构
- 添加新的 npm 或 pip 依赖
- 更改跨域（CORS）配置
- 修改端口配置（5000/8000）
- 更改 PDF 存储目录结构
- 删除或重命名公共 API

### Never Do

- 硬编码文件路径或端点
- 跳过测试直接提交
- 使用通配符导入（`from x import *`）
- 修改安全检查逻辑（app.py 中的路径安全检查）
- 忽略错误处理

## Progressive Disclosure: Detailed Guides

| Task                      | Reference                                       |
| ------------------------- | ----------------------------------------------- |
| Backend API 开发           | `backend/app.py`                                |
| 前端组件开发               | `frontend/src/components/*.jsx`                |
| PDF 阅读器功能            | `frontend/src/components/PdfViewer.jsx`        |
| PDF 文件管理              | `frontend/src/components/PdfManager.jsx`       |
| 术语查看器                | `frontend/src/components/TerminologyViewer.jsx`|
| API 端点                  | `GET /api/pdfs`, `GET /api/pdf/<filename>`     |
| 样式修改                  | `frontend/src/**/*.css`                         |

## Extended Configuration

See `.claude/agents/`, `.claude/skills/`, `.claude/commands/`, and `.claude/rules/` for
specialized instructions.

### Agents

| Agent        | Purpose              | Activation Trigger                    |
| ------------ | -------------------- | -------------------------------------- |
| `test-runner` | Test execution       | 运行测试、检查测试结果、验证代码功能时 |

