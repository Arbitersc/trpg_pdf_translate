# TRPG PDF 翻译器 / PDF阅读器

针对桌上角色扮演游戏（Tabletop Role Playing Game，缩写： TRPG）的PDF、text等文本书籍，通过大语言模型翻译生成结果文件。

## PDF阅读器功能

本项目包含一个基于前后端分离架构的PDF在线阅读器。

### 技术栈

- **前端**: React + Vite + PDF.js
- **后端**: Python + Flask
- **架构**: 前后端分离

### 项目结构

```
trpg_pdf_translate/
├── backend/              # 后端服务
│   ├── app.py           # Flask应用主文件
│   ├── requirements.txt  # Python依赖
│   └── pdfs/            # PDF文件存储目录
└── frontend/            # 前端页面
    ├── src/             # React源代码
    │   ├── components/  # React组件
    │   ├── App.jsx      # 主应用组件
    │   ├── main.jsx     # 入口文件
    │   └── *.css        # 样式文件
    ├── index.html       # HTML模板
    ├── package.json     # 前端依赖配置
    └── vite.config.js   # Vite配置
```

### 快速开始

#### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2. 启动后端服务

```bash
cd backend
python app.py
```

后端服务将在 `http://localhost:5000` 启动

#### 3. 安装前端依赖

```bash
cd frontend
npm install
```

#### 4. 添加PDF文件

将PDF文件放入 `backend/pdfs/` 目录下

#### 5. 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端服务将在 `http://localhost:8000` 启动

#### 6. 访问应用

在浏览器中打开 `http://localhost:8000` 即可使用PDF阅读器

### API接口

#### 获取PDF文件列表
```
GET http://localhost:5000/api/pdfs
```

返回示例：
```json
{
  "success": true,
  "count": 1,
  "files": [
    {
      "filename": "example.pdf",
      "size": 12345,
      "url": "/api/pdf/example.pdf"
    }
  ]
}
```

#### 下载指定PDF文件
```
GET http://localhost:5000/api/pdf/<filename>
```

### 功能特性

✅ PDF文件列表展示
✅ 在线PDF预览和翻页
✅ 响应式设计
✅ 跨域支持（CORS）
✅ 文件大小显示
✅ 页码导航
✅ React组件化开发
✅ Vite快速热更新

### 注意事项

1. 确保后端服务已启动（端口5000）
2. 将PDF文件放在 `backend/pdfs/` 目录下
3. 需要安装Node.js和npm
4. 首次运行需要执行 `npm install` 安装依赖
5. 开发环境支持热更新，修改代码后会自动刷新页面

### 构建生产版本

```bash
cd frontend
npm run build
```

构建后的文件将在 `frontend/dist` 目录下，可以部署到任何静态文件服务器。
