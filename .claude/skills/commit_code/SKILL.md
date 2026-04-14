---
name: commit_code
description: Analyzes git changes and commits related files together with meaningful commit messages
---

# commit_code 代码提交工具

## 功能
基于 git 改动自动分析修改的文件，将相关的代码改动打包提交，支持多次独立的 commit。

## 使用方法
```bash
python .claude/skills/commit_code/commit_code.py
```

## 实施步骤
1. 通过 git diff --name-only 获取所有改动文件
2. 分析文件类型和路径，根据文件类型和目录分组
3. 为每组文件生成有意义的 commit message
4. 使用 git add 批量添加文件
5. 使用 git commit 提交更改
6. 重复以上步骤处理所有改动组

## Commit 分组策略
- backend/ 目录下 Python 文件 → "backend: ..."
- test/ 目录下测试文件 → "test: ..."
- requirements.txt 等 → "deps: ..."
- 其他文件 → "chore: ..." 或 "docs: ..."

## Commit Message 格式
遵循 conventional commits 规范：
- `feat:` 新功能
- `fix:` bug修复
- `refs:` 重构
- `docs:` 文档更新
- `test:` 测试
- `deps:` 依赖更新
- `chore:` 杂项
