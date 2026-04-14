---
name: claude-update
description: Analyzes git changes and updates CLAUDE.md directory structure tables with actual content and core file descriptions
---

# claude_update 自动更新 CLAUDE.md 目录结构表格

## 功能
基于 git 改动自动扫描项目中相关目录，根据实际内容更新对应 Markdown 文件中的目录结构表格，并添加核心文件的功能描述。

## 使用方法
```bash
python .claude/skills/update_claude_md.py
```

## 实施步骤
1. 通过 git 命令查看所有改动文件
2. 检测涉及改动的目录所对应的 CLAUDE.md
3. 分析目录结构并更新表格内容
4. 读取核心文件内容，提取功能信息并添加到 CLAUDE.md
