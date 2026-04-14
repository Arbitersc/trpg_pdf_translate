#!/usr/bin/env python3
"""
CLAUDE.md 自动更新脚本

基于 git 改动扫描项目中相关目录，根据实际内容更新对应 Markdown 文件中的
目录结构表格，并添加核心文件的功能描述。

使用方法:
    python .claude/skills/update_claude_md.py
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Tuple, Dict, List, Set, Optional


class GitAnalyzer:
    """分析 git 改动"""

    @staticmethod
    def get_changed_files(project_root: Path) -> Set[Path]:
        """
        获取所有改动文件

        Args:
            project_root: 项目根目录

        Returns:
            改动文件的路径集合（相对路径）
        """
        try:
            # 获取所有修改、新增、删除的文件
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=False,
                cwd=project_root
            )

            changed_files = set()
            for line in result.stdout.splitlines():
                if line.strip():
                    # git status 输出格式: XY filename
                    # X = index status, Y = worktree status
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) >= 2:
                        filepath = parts[1]
                        changed_files.add(Path(filepath))

            return changed_files

        except Exception as e:
            print(f"Warning: Failed to get git changes: {e}")
            return set()


    @staticmethod
    def get_affected_directories(changed_files: Set[Path]) -> Set[Path]:
        """
        根据改动文件获取受影响的目录

        Args:
            changed_files: 改动文件的路径集合

        Returns:
            受影响的目录集合
        """
        affected_dirs = set()

        for filepath in changed_files:
            # 获取文件所在目录及其所有父目录
            current = filepath.parent
            while current != Path('.'):
                affected_dirs.add(current)
                current = current.parent

        # 添加根目录
        affected_dirs.add(Path('.'))

        return affected_dirs


class FileContentAnalyzer:
    """分析文件内容并提取功能描述"""

    # 需要分析的核心文件类型
    CORE_FILE_PATTERNS = {
        '.py': '_analyze_python_file',
        '.js': '_analyze_js_file',
        '.ts': '_analyze_ts_file',
        '.json': '_analyze_json_file',
        '.yaml': '_analyze_yaml_file',
        '.yml': '_analyze_yaml_file',
    }

    @staticmethod
    def analyze_file(filepath: Path) -> Optional[str]:
        """
        分析文件并提取功能描述

        Args:
            filepath: 文件路径

        Returns:
            文件功能描述，如果无法分析则返回 None
        """
        if not filepath.exists() or not filepath.is_file():
            return None

        suffix = filepath.suffix.lower()
        method_name = FileContentAnalyzer.CORE_FILE_PATTERNS.get(suffix)

        if method_name:
            method = getattr(FileContentAnalyzer, method_name)
            return method(filepath)

        return None

    @staticmethod
    def _analyze_python_file(filepath: Path) -> Optional[str]:
        """分析 Python 文件"""
        try:
            content = filepath.read_text(encoding='utf-8')

            # 提取模块文档字符串
            docstring_match = re.search(r'^\s*"""([^"]*?)"""', content, re.DOTALL)
            if docstring_match:
                docstr = docstring_match.group(1).strip()
                # 清理换行符和多余空格
                docstr = ' '.join(docstr.split())
                if docstr and len(docstr) > 10:
                    # 取第一句话作为描述
                    first_sentence = docstr.split('.')[0].strip()
                    return f"{first_sentence}."

            # 如果没有文档字符串，尝试提取类和函数的注释
            class_matches = re.findall(r'class\s+\w+.*?:\s*"""([^"]*?)"""', content, re.DOTALL)
            if class_matches:
                return f"Defines {len(class_matches)} class(es)"

            func_matches = re.findall(r'def\s+\w+.*?:\s*"""([^"]*?)"""', content, re.DOTALL)
            if func_matches:
                return f"Defines {len(func_matches)} function(s)"

            return None

        except Exception as e:
            return None

    @staticmethod
    def _analyze_js_file(filepath: Path) -> Optional[str]:
        """分析 JavaScript 文件"""
        try:
            content = filepath.read_text(encoding='utf-8')
            return FileContentAnalyzer._analyze_js_like_file(content)
        except Exception:
            return None

    @staticmethod
    def _analyze_ts_file(filepath: Path) -> Optional[str]:
        """分析 TypeScript 文件"""
        try:
            content = filepath.read_text(encoding='utf-8')
            return FileContentAnalyzer._analyze_js_like_file(content, is_ts=True)
        except Exception:
            return None

    @staticmethod
    def _analyze_js_like_file(content: str, is_ts: bool = False) -> Optional[str]:
        """分析类 JavaScript 文件内容"""
        js_ts = 'TypeScript' if is_ts else 'JavaScript'

        # 检查是否是 React 组件
        if 'export default function' in content or 'export default class' in content:
            if 'return <' in content:
                return f"React component"

        # 检查是否包含注释描述
        comment_match = re.search(r'/\*\*\s*([^*]*?)\*/', content, re.DOTALL)
        if comment_match:
            desc = comment_match.group(1).strip()
            desc = ' '.join(desc.split())  # 清理换行符和多余空格
            if desc and len(desc) > 10:
                first_sentence = desc.split('.')[0].strip()
                return f"{first_sentence}."

        # 统计导出的函数和类
        named_exports = len(re.findall(r'export (const|function|class|interface|type)', content))
        default_export = 'export default' in content

        if default_export and named_exports == 0:
            return f"{js_ts} module (default export)"
        elif named_exports > 0:
            return f"{js_ts} module ({named_exports} export(s))"

        return None

    @staticmethod
    def _analyze_json_file(filepath: Path) -> Optional[str]:
        """分析 JSON 文件"""
        try:
            content = filepath.read_text(encoding='utf-8')

            if 'dependencies' in content or 'devDependencies' in content:
                return "Dependencies configuration"

            # 提取主要键
            import json
            data = json.loads(content)
            main_keys = list(data.keys())[:3]
            return f"Configuration ({', '.join(main_keys)})"

        except Exception:
            return None

    @staticmethod
    def _analyze_yaml_file(filepath: Path) -> Optional[str]:
        """分析 YAML 文件"""
        try:
            content = filepath.read_text(encoding='utf-8')
            extract_env_vars = re.findall(r'^\s*[\w_]+:', content)
            return f"Configuration ({len(extract_env_vars)} keys)"
        except Exception:
            return None


class DirectoryAnalyzer:
    """分析目录内容并生成描述"""

    # 文件类型到描述的映射
    FILE_DESCRIPTIONS = {
        '__init__.py': 'Package initialization',
        'requirements.txt': 'Python dependencies',
        '.env': 'Environment configuration',
        '.env.example': 'Environment configuration template',
        'config.py': 'Configuration module',
        'app.py': 'Flask application entry point',
        'main.py': 'Main application entry point',
        'package.json': 'NPM dependencies',
        'vite.config.js': 'Vite build configuration',
        'pyproject.toml': 'Python project configuration',
    }

    # 目录类型到用途的映射
    DIRECTORY_PURPOSES = {
        'backend': 'Backend API and services',
        'frontend': 'Frontend UI components',
        'test': 'Test files and test data',
        'tests': 'Test files',
        'docs': 'Documentation',
        'doc': 'Documentation and test data',
        'api': 'API endpoints',
        'models': 'Data models',
        'utils': 'Utility functions',
        'services': 'Service layer',
        'components': 'UI components',
        'assets': 'Static assets',
        'styles': 'Stylesheets',
        'config': 'Configuration files',
        'scripts': 'Build and utility scripts',
    }

    @staticmethod
    def analyze_directory(dir_path: Path, changed_files: Set[Path]) -> Tuple[str, str, Dict[str, str]]:
        """
        分析目录并返回 (description, contents, file_descriptions)

        Args:
            dir_path: 目录路径
            changed_files: 改动文件的集合

        Returns:
            (目录用途描述, 内容描述, {文件名: 功能描述})
        """
        if not dir_path.exists() or not dir_path.is_dir():
            return "Directory not found", "", {}

        dir_name = dir_path.name

        # 获取目录用途描述
        description = DirectoryAnalyzer._get_directory_description(dir_name)

        # 分析目录内容和提取核心文件描述
        contents, file_descriptions = DirectoryAnalyzer._get_directory_contents(dir_path, changed_files)

        return description, contents, file_descriptions

    @staticmethod
    def _get_directory_description(dir_name: str) -> str:
        """获取目录用途描述"""
        if dir_name in DirectoryAnalyzer.DIRECTORY_PURPOSES:
            return DirectoryAnalyzer.DIRECTORY_PURPOSES[dir_name]
        return f"{dir_name.capitalize()} directory"

    @staticmethod
    def _get_directory_contents(dir_path: Path, changed_files: Set[Path]) -> Tuple[str, Dict[str, str]]:
        """
        分析目录内容并生成描述

        Returns:
            (内容描述, {文件名: 功能描述})
        """
        items = list(dir_path.iterdir())

        if not items:
            return "Empty", {}

        contents_parts = []
        file_descriptions = {}

        # 统计文件类型
        py_files = []
        js_ts_files = []
        other_files = []
        subdirs = []

        for item in items:
            if item.name.startswith('.') and item.name not in ['.env.example']:
                continue

            # 跳过 __pycache__ 目录
            if item.is_dir() and item.name == '__pycache__':
                continue

            if item.is_dir():
                subdirs.append(item.name)
            elif item.suffix == '.py':
                py_files.append(item.name)
            elif item.suffix in ['.js', '.ts']:
                js_ts_files.append(item.name)
            else:
                other_files.append(item.name)

        # 生成内容描述
        if py_files:
            meaningful_names = []
            for f in py_files:
                if f in DirectoryAnalyzer.FILE_DESCRIPTIONS:
                    meaningful_names.append(DirectoryAnalyzer.FILE_DESCRIPTIONS[f])
                elif f != '__pycache__':
                    if f.startswith('test_'):
                        meaningful_names.append(f.replace('.py', ' test file'))
                    else:
                        meaningful_names.append(f.replace('.py', ' module'))
            if meaningful_names:
                contents_parts.append(', '.join(meaningful_names[:3]))

        if js_ts_files:
            count = len(js_ts_files)
            if count > 0:
                contents_parts.append(f"{count} Web module(s)")

        if other_files:
            for f in other_files:
                if f in DirectoryAnalyzer.FILE_DESCRIPTIONS:
                    contents_parts.append(DirectoryAnalyzer.FILE_DESCRIPTIONS[f])

        if subdirs:
            contents_parts.append(f"{len(subdirs)} subdirectories")

        if not contents_parts:
            if len(items) > 0:
                contents = f"{len(items)} files"
            else:
                contents = "Empty"
        else:
            contents = '; '.join(contents_parts)

        # 分析核心文件的功能描述
        for item in items:
            if item.is_file() and not item.name.startswith('.'):
                # 优先分析改动的文件
                if item in changed_files or any(p in changed_files for p in list(item.parents)):
                    desc = FileContentAnalyzer.analyze_file(item)
                    if desc:
                        file_descriptions[item.name] = desc

        return contents, file_descriptions


class MarkdownUpdater:
    """Markdown 文档更新器"""

    @staticmethod
    def update_claude_md(
        filepath: Path,
        table_data: Dict[str, Tuple[str, str, Dict[str, str]]]
    ) -> bool:
        """
        更新 CLAUDE.md 文件

        Args:
            filepath: CLAUDE.md 文件路径
            table_data: 目录名 -> (description, contents, file_descriptions) 的映射

        Returns:
            是否成功更新
        """
        if not filepath.exists():
            print(f"Warning: {filepath} does not exist")
            return False

        content = filepath.read_text(encoding='utf-8')
        original_content = content

        # 1. 更新目录结构表格
        pattern = r'\| Directory \| Description \| Contents \|\n\|-+\|[-\s]+\|[-\s]+\|\n((?:\|[^|\n]+\|[^|\n]+\|[^|\n]+\|[\n]*)+)'

        def replace_table(match):
            original_lines = match.group(0).split('\n')
            header_title = original_lines[0]
            header_sep = original_lines[1]

            rows = [header_title, header_sep]

            for dir_name, (description, contents, _) in sorted(table_data.items()):
                rows.append(f"| {dir_name}/ | {description} | {contents} |")

            return '\n'.join(rows) + '\n\n'

        new_content = re.sub(pattern, replace_table, content, flags=re.MULTILINE)

        # 2. 添加核心文件描述部分
        core_files_section = MarkdownUpdater._generate_core_files_section(table_data)

        if core_files_section:
            # 检查是否已存在 Core Files section
            if '## Core Files' in new_content:
                # 替换现有的 Core Files section
                new_content = re.sub(
                    r'## Core Files[\s\S]*?(?=##|\Z)',
                    core_files_section,
                    new_content
                )
            else:
                # 在文档末尾添加
                new_content = new_content.rstrip() + '\n\n' + core_files_section

        if new_content != original_content:
            filepath.write_text(new_content, encoding='utf-8')
            print(f"Updated: {filepath}")
            return True
        else:
            print(f"No changes: {filepath}")
            return False

    @staticmethod
    def _generate_core_files_section(table_data: Dict[str, Tuple[str, str, Dict[str, str]]]) -> str:
        """生成核心文件描述部分"""
        if not any(file_descs for _, _, file_descs in table_data.values()):
            return ""

        lines = ["## Core Files\n"]
        lines.append("| File | Description |")
        lines.append("|------|-------------|\n")

        for dir_name, (description, contents, file_descs) in sorted(table_data.items()):
            if file_descs:
                for filename, desc in sorted(file_descs.items()):
                    lines.append(f"| {dir_name}/{filename} | {desc} |")

        return '\n'.join(lines) + '\n'


def find_relevant_claude_md_files(affected_directories: Set[Path], project_root: Path) -> List[Path]:
    """
    查找与受影响目录相关的 CLAUDE.md 文件

    Args:
        affected_directories: 受影响的目录集合（相对路径）
        project_root: 项目根目录

    Returns:
        相关的 CLAUDE.md 文件列表（绝对路径）
    """
    claude_md_files = set()

    # 确保所有路径都是绝对路径
    for dir_path in affected_directories:
        if dir_path.is_absolute():
            current = dir_path
        else:
            current = project_root / dir_path

        # 检查该目录或其父目录是否有 CLAUDE.md
        while current != project_root.parent and current.exists():
            claude_md_path = current / 'CLAUDE.md'
            if claude_md_path.exists():
                claude_md_files.add(claude_md_path.resolve())
                break
            current = current.parent

        # 检查项目根目录
        root_claude_md = project_root / 'CLAUDE.md'
        if root_claude_md.exists():
            claude_md_files.add(root_claude_md.resolve())

    return sorted(claude_md_files)


def analyze_subdirectories(
    claude_md_path: Path,
    changed_files: Set[Path],
    project_root: Path
) -> Dict[str, Tuple[str, str, Dict[str, str]]]:
    """
    分析 CLAUDE.md 所在目录的子目录

    Args:
        claude_md_path: CLAUDE.md 文件路径（绝对路径）
        changed_files: 改动文件的集合（相对路径）
        project_root: 项目根目录

    Returns:
        子目录名 -> (description, contents, file_descriptions) 的映射
    """
    parent_dir = claude_md_path.parent
    table_data = {}

    # 获取所有子目录
    for item in parent_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
            dir_name = item.name
            # 转换 changed_files 为绝对路径以便检查
            changed_abs_files = {project_root / f for f in changed_files}
            description, contents, file_descriptions = DirectoryAnalyzer.analyze_directory(item, changed_abs_files)
            table_data[dir_name] = (description, contents, file_descriptions)

    return table_data


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Update CLAUDE.md directory structure table')
    parser.add_argument('--force', '-f', action='store_true', help='Force update even if no git changes detected')
    args = parser.parse_args()

    project_root = Path.cwd().resolve()
    print(f"Project root: {project_root}\n")

    # 1. 获取 git 改动
    print("Step 1: Getting git changes...")
    changed_files = GitAnalyzer.get_changed_files(project_root)
    print(f"  Found {len(changed_files)} changed file(s)")

    for f in sorted(changed_files):
        print(f"    - {f}")

    # 2. 检测受影响的目录
    print("\nStep 2: Detecting affected directories...")
    if changed_files or not args.force:
        affected_directories = GitAnalyzer.get_affected_directories(changed_files)
    else:
        # Force mode: analyze all directories
        affected_directories = {Path('.')}
    print(f"  Found {len(affected_directories)} affected director(ies)")

    # 3. 查找相关的 CLAUDE.md 文件
    print("\nStep 3: Finding relevant CLAUDE.md files...")
    if changed_files or not args.force:
        claude_md_files = find_relevant_claude_md_files(affected_directories, project_root)
        if not claude_md_files:
            # 如果没有找到相关文件，则查找所有 CLAUDE.md
            claude_md_files = sorted(project_root.rglob('CLAUDE.md'))
    else:
        # Force mode: find all CLAUDE.md files
        claude_md_files = sorted(project_root.rglob('CLAUDE.md'))
    print(f"  Found {len(claude_md_files)} CLAUDE.md file(s)")

    # 4. 更新每个 CLAUDE.md
    print("\nStep 4: Processing CLAUDE.md files...")

    for claude_md_path in claude_md_files:
        rel_path = claude_md_path.relative_to(project_root)
        print(f"\nProcessing: {rel_path}")

        # 分析子目录
        table_data = analyze_subdirectories(claude_md_path, changed_files, project_root)

        if not table_data:
            print("  No subdirectories found")
            continue

        print("\n  Analyzed subdirectories:")
        for dir_name, (description, contents, file_descs) in sorted(table_data.items()):
            print(f"    - {dir_name}/: {contents}")
            if file_descs:
                for filename, desc in sorted(file_descs.items()):
                    print(f"        * {filename}: {desc}")

        # 更新文档
        MarkdownUpdater.update_claude_md(claude_md_path, table_data)

    print("\nDone!")


if __name__ == '__main__':
    main()
