#!/usr/bin/env python3
"""
Git 代码提交脚本

基于文件类型和路径分组提交 git 改动，支持多次独立的 commit。

使用方法:
    python .claude/skills/commit_code/commit_code.py
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict


class GitAnalyzer:
    """分析 git 改动"""

    @staticmethod
    def get_changed_files(project_root: Path) -> Dict[str, List[Path]]:
        """
        获取所有改动文件，按文件状态分类

        Args:
            project_root: 项目根目录

        Returns:
            字典: {状态: [文件路径列表]}
                状态包括: 'staged', 'modified', 'untracked'
        """
        result = {
            'staged': [],     # 已暂存
            'modified': [],   # 已修改但未暂存
            'untracked': []   # 未跟踪的新文件
        }

        try:
            # 获取已暂存的文件 (HEAD -> staging area)
            staged_output = subprocess.run(
                ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
                capture_output=True,
                text=True,
                check=False,
                cwd=project_root
            )
            if staged_output.returncode == 0:
                for line in staged_output.stdout.splitlines():
                    if line.strip():
                        result['staged'].append(Path(line.strip()))

            # 获取已修改但未暂存的文件
            modified_output = subprocess.run(
                ['git', 'diff', '--name-only'],
                capture_output=True,
                text=True,
                check=False,
                cwd=project_root
            )
            if modified_output.returncode == 0:
                for line in modified_output.stdout.splitlines():
                    if line.strip():
                        result['modified'].append(Path(line.strip()))

            # 获取未跟踪的新文件
            untracked_output = subprocess.run(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                capture_output=True,
                text=True,
                check=False,
                cwd=project_root
            )
            if untracked_output.returncode == 0:
                for line in untracked_output.stdout.splitlines():
                    if line.strip():
                        result['untracked'].append(Path(line.strip()))

            return result

        except Exception as e:
            print(f"Warning: Failed to get git changes: {e}")
            return result

    @staticmethod
    def get_file_status(filepath: Path, project_root: Path) -> str:
        """
        获取单个文件的状态

        Args:
            filepath: 文件路径
            project_root: 项目根目录

        Returns:
            文件状态: 'staged', 'modified', 'untracked', 或 'none'
        """
        status_files = GitAnalyzer.get_changed_files(project_root)
        abs_path = (project_root / filepath) if not filepath.is_absolute() else filepath

        for status, files in status_files.items():
            # 比较规范化后的路径
            for f in files:
                f_abs = (project_root / f) if not f.is_absolute() else f
                if str(abs_path.resolve()) == str(f_abs.resolve()):
                    return status

        return 'none'

    @staticmethod
    def get_staged_files(project_root: Path) -> List[Path]:
        """获取已暂存的文件列表"""
        changed_files = GitAnalyzer.get_changed_files(project_root)
        return changed_files['staged']

    @staticmethod
    def get_unstaged_files(project_root: Path) -> List[Path]:
        """获取未暂存的文件列表（修改和未跟踪）"""
        changed_files = GitAnalyzer.get_changed_files(project_root)
        return changed_files['modified'] + changed_files['untracked']


class CommitGroup:
    """提交分组"""

    # Commit type 映射
    COMMIT_TYPES = {
        'backend': 'feat',
        'frontend': 'feat',
        'test': 'test',
        'docs': 'docs',
        'requirements.txt': 'deps',
        'package.json': 'deps',
        'pyproject.toml': 'deps',
        '.env': 'chore',
        'config': 'chore',
        'scripts': 'chore',
        'claude': 'chore',
    }

    # 目录到描述的映射
    DIR_DESCRIPTIONS = {
        'backend': 'backend',
        'frontend': 'frontend',
        'test': 'test',
        'tests': 'test',
        'docs': 'docs',
        'doc': 'docs',
        'src': 'source',
        'scripts': 'scripts',
    }

    @staticmethod
    def get_file_group_key(filepath: Path) -> str:
        """
        获取文件的分组key

        Args:
            filepath: 文件路径

        Returns:
            分组key，如 "backend", "test", "deps" 等
        """
        parts = filepath.parts

        # 特殊文件名
        if filepath.name in ['requirements.txt', 'package.json', 'pyproject.toml', 'setup.py', 'setup.cfg']:
            return 'deps'
        if filepath.name.startswith('.env'):
            return 'config'
        if '.claude' in parts or filepath.name == 'CLAUDE.md':
            return 'claude'

        # 根据目录分组
        for part in parts:
            lower_part = part.lower()
            if lower_part in CommitGroup.DIR_DESCRIPTIONS:
                return CommitGroup.DIR_DESCRIPTIONS[lower_part]
            if lower_part in CommitGroup.COMMIT_TYPES:
                return lower_part

        # 根据文件名分组
        if 'test' in filepath.name.lower():
            return 'test'
        if 'config' in filepath.name.lower():
            return 'config'

        # 默认分组
        return 'other'

    @staticmethod
    def get_commit_type(group_key: str) -> str:
        """获取 commit type"""
        if group_key in CommitGroup.COMMIT_TYPES:
            return CommitGroup.COMMIT_TYPES[group_key]

        # 特殊规则
        if group_key == 'test':
            return 'test'
        if group_key == 'docs':
            return 'docs'
        if group_key == 'claude':
            return 'chore'

        return 'feat'

    @staticmethod
    def generate_commit_message(group_key: str, files: List[Path]) -> str:
        """
        生成 commit message

        Args:
            group_key: 分组key
            files: 文件列表

        Returns:
            commit message
        """
        commit_type = CommitGroup.get_commit_type(group_key)
        file_names = [f.name for f in files]

        if len(files) == 1:
            scope = f"{files[0].parent}" if files[0].parent != Path('.') else file_names[0]
            subject = f"Update {scope}"
        else:
            # 使用第一个非空父目录作为scope
            common_parent = CommitGroup._get_common_parent(files)
            if common_parent and common_parent != Path('.'):
                scope = str(common_parent)
            else:
                scope = group_key

            # 生成描述
            if group_key == 'deps':
                subject = "Update dependencies"
            elif group_key == 'test':
                subject = "Add/update tests"
            elif group_key == 'docs':
                subject = "Update documentation"
            elif group_key == 'config':
                subject = "Update configuration"
            elif group_key == 'claude':
                subject = "Update Claude configuration"
            else:
                subject = f"Update {scope} files"

        # 添加文件列表到 body
        body = "\nChanges:\n" + "\n".join(f"  - {f}" for f in sorted(str(p) for p in files))

        message = f"{commit_type}: {subject}\n\n{body}"

        return message

    @staticmethod
    def _get_common_parent(files: List[Path]) -> Optional[Path]:
        """获取文件的共同父目录"""
        if not files:
            return None

        common_parent = files[0].parent
        for f in files[1:]:
            while not str(f.resolve()).startswith(str(common_parent.resolve())) and common_parent != Path('.'):
                common_parent = common_parent.parent

        return common_parent

    @staticmethod
    def group_files(files: List[Path]) -> Dict[str, List[Path]]:
        """
        将文件分组

        Args:
            files: 文件列表

        Returns:
            分组字典: {group_key: [files]}
        """
        groups = defaultdict(list)

        for f in files:
            group_key = CommitGroup.get_file_group_key(f)
            groups[group_key].append(f)

        return dict(groups)


class GitCommiter:
    """Git 提交操作"""

    @staticmethod
    def git_add(files: List[Path], project_root: Path) -> bool:
        """
        添加文件到暂存区

        Args:
            files: 文件列表
            project_root: 项目根目录

        Returns:
            是否成功
        """
        if not files:
            return True

        try:
            file_paths = [str(f) for f in files]
            subprocess.run(
                ['git', 'add'] + file_paths,
                capture_output=True,
                check=True,
                cwd=project_root
            )
            print(f"  Added {len(files)} file(s) to staging area")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  Error adding files: {e.stderr.decode()}")
            return False

    @staticmethod
    def git_commit(message: str, project_root: Path) -> bool:
        """
        提交更改

        Args:
            message: commit message
            project_root: 项目根目录

        Returns:
            是否成功
        """
        try:
            # 创建临时文件存储 commit message
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
                f.write(message)
                msg_file = f.name

            try:
                subprocess.run(
                    ['git', 'commit', '-F', msg_file],
                    capture_output=True,
                    check=True,
                    cwd=project_root
                )
                return True
            finally:
                os.unlink(msg_file)

        except subprocess.CalledProcessError as e:
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""
            if 'nothing to commit' in stdout or 'no changes added' in stdout:
                print("  No changes to commit")
                return False
            print(f"  Error committing: {stdout}{stderr}")
            return False

    @staticmethod
    def check_git_repo(project_root: Path) -> bool:
        """检查是否在 git 仓库中"""
        try:
            subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                check=True,
                cwd=project_root
            )
            return True
        except subprocess.CalledProcessError:
            return False


def commit_changes_by_groups(project_root: Optional[Path] = None, dry_run: bool = False):
    """
    按分组提交改动

    Args:
        project_root: 项目根目录，默认为当前目录
        dry_run: 是否只显示不执行
    """
    if project_root is None:
        project_root = Path.cwd().resolve()

    print(f"Project root: {project_root}\n")

    # 检查是否在 git 仓库中
    if not GitCommiter.check_git_repo(project_root):
        print("Error: Not in a git repository")
        return

    # 获取未暂存的文件
    print("Analyzing git changes...")
    changed_files = GitAnalyzer.get_changed_files(project_root)
    unstaged_files = changed_files['modified'] + changed_files['untracked']

    if not unstaged_files:
        print("No unstaged changes found")
        return

    print(f"Found {len(unstaged_files)} unstaged file(s):")
    for f in sorted(unstaged_files):
        print(f"  - {f}")
    print()

    # 分组文件
    groups = CommitGroup.group_files(unstaged_files)

    print(f"Grouped into {len(groups)} commit(s):\n")

    # 按分组提交
    for group_key, files in sorted(groups.items()):
        print(f"Group '{group_key}' ({len(files)} files):")
        for f in sorted(files):
            print(f"  - {f}")

        # 生成 commit message
        commit_msg = CommitGroup.generate_commit_message(group_key, files)
        print(f"\n  Commit message preview:")
        print("  " + "-" * 60)
        for line in commit_msg.split('\n'):
            print(f"  {line}")
        print("  " + "-" * 60)

        if dry_run:
            print(f"  [DRY RUN] Would commit these files\n")
            continue

        # 添加文件
        if not GitCommiter.git_add(files, project_root):
            print(f"  Failed to add files to staging\n")
            continue

        # 提交
        if GitCommiter.git_commit(commit_msg, project_root):
            print(f"  ✓ Committed successfully\n")
        else:
            print(f"  ✗ Failed to commit\n")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Commit git changes grouped by file type and path'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be committed without actually committing'
    )
    parser.add_argument(
        '--dir',
        type=str,
        default=None,
        help='Project root directory (default: current directory)'
    )

    args = parser.parse_args()

    project_root = Path(args.dir).resolve() if args.dir else None
    commit_changes_by_groups(project_root, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
