"""
Utility Functions for TRPG PDF Translator CLI

This module provides common utility functions used throughout the CLI.
"""

import os
import sys
import time
from typing import List, Optional, Callable


def clear_screen():
    """Clear the terminal screen."""
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Unix/Linux/MacOS
        os.system('clear')


def print_banner():
    """Print the application banner."""
    try:
        import pyfiglet
        line1 = pyfiglet.figlet_format("TRPG PDF", font="slant", width=80)
        line2 = pyfiglet.figlet_format("TRANSLATOR", font="slant", width=80)
        print(line1 + line2)
    except ImportError:
        print("TRPG PDF TRANSLATOR")
    print("  v1.0 - TRPG专用PDF翻译工具\n")


def print_header(title: str, width: int = 50):
    """Print a formatted header.

    Args:
        title: Header title
        width: Header width
    """
    print("\n" + "=" * width)
    print(f"{title:^{width}}")
    print("=" * width)


def print_progress(current: int, total: int, description: str, bar_length: int = 30):
    """Print a progress bar.

    Args:
        current: Current progress
        total: Total steps
        description: Progress description
        bar_length: Length of progress bar
    """
    progress = current / total
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    percentage = progress * 100

    print(f"\r[{bar}] {percentage:.1f}% - {description}", end="")
    if current == total:
        print()  # New line when complete


def print_success(message: str):
    """Print a success message.

    Args:
        message: Success message
    """
    print(f"✅ {message}")


def print_error(message: str):
    """Print an error message.

    Args:
        message: Error message
    """
    print(f"❌ {message}")


def print_warning(message: str):
    """Print a warning message.

    Args:
        message: Warning message
    """
    print(f"⚠️  {message}")


def print_info(message: str):
    """Print an info message.

    Args:
        message: Info message
    """
    print(f"ℹ️  {message}")


def get_user_choice(prompt: str, valid_choices: List[str]) -> str:
    """Get validated user choice.

    Args:
        prompt: Input prompt
        valid_choices: List of valid choices

    Returns:
        str: User's choice
    """
    while True:
        choice = input(prompt).strip()
        if choice in valid_choices:
            return choice
        else:
            print(f"无效选择，请从 {valid_choices} 中选择")


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user.

    Args:
        prompt: Input prompt
        default: Default value if empty input

    Returns:
        bool: True for yes, False for no
    """
    default_text = "Y/n" if default else "y/N"
    full_prompt = f"{prompt} [{default_text}]: "

    while True:
        choice = input(full_prompt).strip().lower()

        if choice == "":
            return default
        elif choice in ["y", "yes"]:
            return True
        elif choice in ["n", "no"]:
            return False
        else:
            print("请输入 y/yes 或 n/no")


def get_file_path(prompt: str, must_exist: bool = True) -> str:
    """Get a valid file path from user.

    Args:
        prompt: Input prompt
        must_exist: Whether file must exist

    Returns:
        str: Valid file path
    """
    while True:
        path = input(prompt).strip()

        if not path:
            print("错误: 必须提供文件路径")
            continue

        if must_exist and not os.path.exists(path):
            print(f"错误: 文件不存在: {path}")
            continue

        return path


def get_directory_path(prompt: str, must_exist: bool = True) -> str:
    """Get a valid directory path from user.

    Args:
        prompt: Input prompt
        must_exist: Whether directory must exist

    Returns:
        str: Valid directory path
    """
    while True:
        path = input(prompt).strip()

        if not path:
            print("错误: 必须提供目录路径")
            continue

        if must_exist and not os.path.isdir(path):
            print(f"错误: 目录不存在: {path}")
            continue

        return path


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_time_duration(seconds: float) -> str:
    """Format time duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        str: Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def confirm_action(prompt: str, dangerous: bool = False) -> bool:
    """Confirm an action with the user.

    Args:
        prompt: Confirmation prompt
        dangerous: Whether this is a dangerous action

    Returns:
        bool: True if confirmed, False otherwise
    """
    if dangerous:
        print_warning("警告: 这是一个危险操作！")

    return get_yes_no(prompt, default=False)


def wait_with_spinner(duration: int, message: str = "处理中"):
    """Display a spinner while waiting.

    Args:
        duration: Wait duration in seconds
        message: Message to display
    """
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    start_time = time.time()

    while time.time() - start_time < duration:
        for frame in spinner:
            if time.time() - start_time >= duration:
                break
            print(f"\r{frame} {message}", end="", flush=True)
            time.sleep(0.1)

    print("\r✅ 完成" + " " * 20)


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        bool: True if format appears valid
    """
    # Basic validation - check if it looks like a typical API key
    if not api_key or len(api_key) < 10:
        return False

    # Check for common API key patterns
    if api_key.startswith("sk-") or api_key.startswith("pk-"):
        return True

    # Check for base64-like format (alphanumeric with possible dashes/underscores)
    import re
    if re.match(r'^[a-zA-Z0-9_-]{20,}$', api_key):
        return True

    return True  # Be permissive for unknown formats


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be filesystem-safe.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    import re
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    return sanitized


def create_backup_file(filepath: str) -> bool:
    """Create a backup of a file.

    Args:
        filepath: Path to file to backup

    Returns:
        bool: True if backup successful
    """
    import shutil
    from datetime import datetime

    if not os.path.exists(filepath):
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"

    try:
        shutil.copy2(filepath, backup_path)
        print_info(f"备份已创建: {backup_path}")
        return True
    except IOError as e:
        print_error(f"备份创建失败: {e}")
        return False


def check_disk_space(path: str, required_mb: int = 100) -> bool:
    """Check if sufficient disk space is available.

    Args:
        path: Path to check disk space for
        required_mb: Required space in MB

    Returns:
        bool: True if sufficient space available
    """
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        free_mb = free // (1024 * 1024)

        if free_mb < required_mb:
            print_warning(f"磁盘空间不足: {free_mb}MB 可用，需要 {required_mb}MB")
            return False

        return True
    except OSError:
        print_warning("无法检查磁盘空间")
        return True  # Assume sufficient if check fails