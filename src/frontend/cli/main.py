#!/usr/bin/env python3
"""
TRPG PDF Translator CLI Entry Point

This module provides the main command-line interface for the TRPG PDF Translator.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add the current directory to Python path for relative imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import modules directly (now that current_dir is in path)
from interactive import show_main_menu, run_selected_workflow
from config import ConfigManager
from utils import print_banner, clear_screen


def main():
    """Main CLI entry point."""
    try:
        # Check if running in interactive mode
        if len(sys.argv) == 1 or sys.argv[1] == "--interactive":
            run_interactive_mode()
        else:
            run_command_line_mode()
    except KeyboardInterrupt:
        print("\n\n操作已取消。再见！")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


def run_interactive_mode():
    """Run the interactive CLI mode."""
    clear_screen()
    print_banner()

    while True:
        try:
            choice = show_main_menu()
            if choice == "7":  # Exit
                print("\n感谢使用 TRPG PDF Translator！再见！")
                break

            run_selected_workflow(choice)

            # Ask if user wants to continue
            print("\n" + "="*50)
            continue_choice = input("是否继续使用其他功能？(y/N): ").strip().lower()
            if continue_choice not in ['y', 'yes']:
                print("\n感谢使用 TRPG PDF Translator！再见！")
                break

            clear_screen()
            print_banner()

        except KeyboardInterrupt:
            print("\n\n操作已取消。")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            input("按回车键继续...")


def run_command_line_mode():
    """Run command-line mode with arguments."""
    # This will be implemented in Phase 2
    print("命令行模式将在第二阶段实现")
    print("当前参数:", sys.argv[1:])
    print("请使用交互式模式: python -m src.frontend.cli.main")


if __name__ == "__main__":
    main()