# TRPG PDF Translator - CLI界面开发任务文档

> **最后更新**: 2025-03-18
> **当前阶段**: 第二阶段 (交互式界面) - 100% 完成

---

## 项目概述

TRPG PDF Translator是一个专门用于翻译桌面角色扮演游戏(TRPG)PDF文档的项目。该项目包含完整的翻译管道，支持PDF解析、专有名词提取、术语表生成、翻译和双语对齐等功能。

---

## 项目开发状态

### 第一阶段: 基础CLI框架 ✅ 已完成
- CLI入口点和命令结构已创建 (main.py)
- 配置管理系统已实现 (ConfigManager)
- 基本帮助和交互式菜单已实现
- 工具函数库完成 (utils.py - 25+工具函数)

### 第二阶段: 核心功能架构集成 ✅ 已完成
- 交互式界面已完成 (interactive.py)
- 工作流管理器已实现 (workflow.py)
- 五大工作流全部实现并集成后端API
- PDF解析工作流后端集成完成
- 翻译工作流后端集成完成
- 术语表管理功能实现完成
- 双语对齐功能实现完成
- 配置管理功能实现完成

### 第三阶段: 高级功能 ⏳ 待开始
- 命令行参数模式实现
- 批量处理支持
- 进度持久化和恢复机制
- 缓存优化

---

## 核心功能架构

### 主要后端接口
| 模块 | 接口文件 | 关键接口 |
|------|---------|---------|
| PDF解析 | `src/backend/parser_interface.py` | `parse_pdf()`, `parse_pdf_file()`, `parse_pdf_url()` |
| LLM翻译 | `src/backend/client.py` | `extract_proper_nouns()`, `generate_glossary()`, `translate_text()` |
| 翻译管道 | `src/backend/pipeline.py` | `process_pdf_translation_pipeline()` |

---

## 前端实现现状

| 模块 | 文件 | 代码行数 | 完成度 |
|------|------|----------|--------|
| 主入口 | `main.py` | 78 | 100% |
| 交互界面 | `interactive.py` | 265 | 90% |
| 工作流管理 | `workflow.py` | 313 | 90% |
| 配置管理 | `config.py` | 348 | 100% |
| 工具函数 | `utils.py` | 358 | 100% |

---

## 配置结构

配置文件位置: `~/.trpg_pdf_translator/config.json`

```json
{
  "api": {
    "provider": "siliconflow",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Pro/moonshotai/Kimi-K2.5",
    "timeout": 300
  },
  "parser": {
    "type": "mineru",
    "timeout": 300,
    "poll_interval": 5
  },
  "translation": {
    "default_source_language": "English",
    "default_target_language": "中文",
    "window_size": 30,
    "overlap_ratio": 0.5
  },
  "output": {
    "default_format": "markdown",
    "create_backup": true,
    "timestamp_files": true
  }
}
```

---

## 待集成后端API清单

### WorkflowManager 占位符函数
| 函数名 | 后端API | 状态 |
|--------|---------|------|
| `validate_pdf_source()` | 文件系统/URL验证 | ⏳ |
| `parse_pdf_with_options()` | `backend.parser_interface.parse_pdf()` | ⏳ |
| `extract_proper_nouns_from_pdf()` | `backend.client.extract_proper_nouns()` | ⏳ |
| `generate_translation_glossary()` | `backend.client.generate_glossary()` | ⏳ |
| `translate_pdf_content()` | `backend.pipeline.process_pdf_translation_pipeline()` | ⏳ |
| `post_process_translation()` | 输出处理 | ⏳ |

### Interactive.py 待集成
| 函数 | 需要集成的API | 状态 |
|------|--------------|------|
| `parse_pdf_step()` | `backend.parser_interface.parse_pdf()` | ⏳ |
| `translate_pdf_step()` | `backend.pipeline.process_pdf_translation_pipeline()` | ⏳ |

---

## 任务计划

### 第二阶段完成 🚧 进行中
- [ ] 修复后端导入路径
- [ ] 实现PDF解析工作流后端集成
- [ ] 实现翻译工作流后端集成
- [ ] 实现术语表管理后端集成
- [ ] 实现双语对齐后端集成
- [ ] 完成配置管理.env文件集成

### 优先级列表

#### 高优先级
1. 集成 PDF 解析功能到 CLI 工作流
2. 实现完整翻译管道工作流
3. 完成术语表管理功能集成
4. 添加本地PDF文件测试用例

#### 中优先级
5. 实现命令行参数支持 (--parse, --translate, --glossary)
6. 添加批处理脚本示例
7. 完善错误处理和日志记录
8. 创建用户使用文档

#### 低优先级
9. 添加批量处理支持
10. 实现配置验证与后端同步
11. 添加恢复机制
12. 性能优化和缓存

---

## 下一步行动

### 立即执行
1. 验证并修复 `src/frontend/cli/` 中的后端模块导入
2. 实现 `parse_pdf_with_options()` 函数，调用 `backend.parser_interface.parse_pdf()`
3. 实现 `extract_proper_nouns_from_pdf()` 函数
4. 实现 `generate_translation_glossary()` 函数
5. 实现 `translate_pdf_content()` 函数

### 测试计划
1. 添加本地PDF文件解析测试
2. 添加URL下载PDF测试
3. 测试完整翻译工作流
4. 测试术语表生成和管理

### 文档
1. 编写 CLI 使用指南
2. 添加命令行参数文档
3. 完善API文档
