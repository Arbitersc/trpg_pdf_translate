"""
Interactive CLI Interface for TRPG PDF Translator

This module provides the interactive menu system for the CLI.
All functionality functions use backend API calls through direct Python imports.
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow import (
    WorkflowManager,
    parse_pdf_from_backend,
    extract_proper_nouns_backend,
    generate_glossary_backend,
    translate_text_backend,
    align_bilingual_text_backend,
    update_translation_with_glossary_backend,
    save_result_to_file,
    load_glossary_from_file,
    save_glossary_to_file,
    validate_pdf_source,
    check_backend_availability
)
from config import ConfigManager
from utils import (
    print_header, get_user_choice, clear_screen, print_banner,
    print_success, print_error, print_warning, print_info,
    get_file_path, sanitize_filename, get_yes_no
)


def show_main_menu() -> str:
    """Display the main menu and return user choice."""
    print_header("TRPG PDF Translator v1.0")

    menu_options = [
        ("1", "📄 PDF解析", "提取PDF文本内容"),
        ("2", "🌐 翻译管道", "完整翻译流程"),
        ("3", "📚 术语表管理", "提取和管理专有名词"),
        ("4", "🔄 双语对齐", "对齐英文和中文文本"),
        ("5", "⚙️  配置管理", "设置API密钥和参数"),
        ("6", "ℹ️  帮助信息", "查看使用说明"),
        ("7", "🚪 退出", "退出程序")
    ]

    print("请选择要执行的操作:\n")
    for option, title, description in menu_options:
        print(f"{option}. {title:15} - {description}")

    return get_user_choice("请输入选项编号 [1-7]: ", [str(i) for i in range(1, 8)])


def run_selected_workflow(choice: str) -> None:
    """Execute the workflow based on user choice."""
    workflows = {
        "1": run_pdf_parse_workflow,
        "2": run_translation_workflow,
        "3": run_glossary_workflow,
        "4": run_alignment_workflow,
        "5": run_config_workflow,
        "6": show_help_info
    }

    if choice in workflows:
        workflows[choice]()
    else:
        print("无效的选择，请重新输入。")


def run_pdf_parse_workflow() -> None:
    """Execute PDF parsing workflow using backend API."""
    print_header("📄 PDF解析选项")

    # Check backend availability
    availability = check_backend_availability()
    if not availability['parser']:
        print_error("后端解析器模块不可用，请确保 backend.parser_interface 模块已安装")
        input("按回车键继续...")
        return

    # Get PDF source
    source = input("输入PDF文件路径或URL: ").strip()
    if not source:
        print("错误: 必须提供PDF文件路径或URL")
        return

    # Validate source
    if not validate_pdf_source(source):
        return

    # Get parsing options
    print("\n解析选项:")
    use_window = get_yes_no("使用滑动窗口 (默认: 5页/窗口)? ", default=False)
    remove_images = get_yes_no("移除图片链接? ", default=True)
    verbose = get_yes_no("详细输出模式? ", default=False)

    # Get window parameters if using sliding window
    window_size = 5
    overlap_pages = 1
    if use_window:
        ws_input = input("窗口大小 [页数, 默认5]: ").strip()
        window_size = int(ws_input) if ws_input else 5
        ol_input = input("重叠页数 [默认1]: ").strip()
        overlap_pages = int(ol_input) if ol_input else 1

    # Get output format
    print("\n输出格式:")
    print("1. 纯文本")
    print("2. Markdown格式")
    print("3. JSON格式")
    format_choice = get_user_choice("选择输出格式 [1-3]: ", ["1", "2", "3"])

    formats = {"1": "text", "2": "markdown", "3": "json"}
    output_format = formats[format_choice]

    # Confirm execution
    if not get_yes_no("\n开始解析? ", default=True):
        print("操作已取消")
        return

    # Execute parsing using backend API
    options = {
        'use_window': use_window,
        'window_size': window_size,
        'overlap_pages': overlap_pages,
        'remove_images': remove_images,
        'verbose': verbose,
        'output_format': output_format
    }

    result = parse_pdf_from_backend(source, options)

    if result.get('status') == 'success':
        print_success("\n✅ PDF解析完成！")

        # Save result
        if get_yes_no("是否保存到文件? ", default=True):
            timestamp = get_timestamp()
            filename = sanitize_filename(f"parsed_{timestamp}")

            if output_format == 'text':
                filepath = f"{filename}.txt"
            elif output_format == 'json':
                filepath = f"{filename}.json"
            else:
                filepath = f"{filename}.md"

            save_result_to_file(result['content'], filepath, output_format)

        # Display preview
        if get_yes_no("是否显示内容预览? ", default=True):
            preview_length = min(500, len(result['content']))
            print(f"\n内容预览 (前 {preview_length} 字符):")
            print("-" * 60)
            print(result['content'][:preview_length])
            if len(result['content']) > preview_length:
                print(f"\n... 还有 {len(result['content']) - preview_length} 字符")
            print("-" * 60)
    else:
        print_error("PDF解析失败")
        if 'message' in result:
            print(f"错误信息: {result['message']}")


def run_translation_workflow() -> None:
    """Execute translation pipeline workflow using backend API."""
    print_header("🌐 翻译管道选项")

    # Check backend availability
    availability = check_backend_availability()
    if not availability['parser'] or not availability['client']:
        print_error("后端模块不可用，请确保 backend.parser_interface 和 backend.client 模块已安装")
        input("按回车键继续...")
        return

    # Get PDF source
    source = input("输入PDF文件路径或URL: ").strip()
    if not source:
        print("错误: 必须提供PDF文件路径或URL")
        return

    if not validate_pdf_source(source):
        return

    # Get translation settings
    source_lang = input("源语言 [English]: ").strip() or "English"
    target_lang = input("目标语言 [中文]: ").strip() or "中文"

    # Get API settings
    api_key = os.getenv('SILICONFLOW_API_KEY')
    if not api_key:
        print_warning("未设置 SILICONFLOW_API_KEY 环境变量")
        if not get_yes_no("继续使用默认设置? ", default=False):
            print("操作已取消")
            return

    model = os.getenv('SILICONFLOW_MODEL')
    if not model:
        model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')
        print(f"使用默认模型: {model}")
    else:
        print(f"使用模型: {model}")

    # Get glossary options
    print("\n术语表选项:")
    auto_extract = get_yes_no("自动提取专有名词? ", default=True)
    use_existing = get_yes_no("使用现有术语表? ", default=False)

    glossary = {}
    if use_existing:
        glossary_path = input("术语表文件路径: ").strip()
        if glossary_path and Path(glossary_path).exists():
            glossary = load_glossary_from_file(glossary_path)
            if glossary:
                print_success(f"加载术语表: {len(glossary)} 个词条")
        else:
            print_warning("术语表文件不存在或无效")

    # Get translation parameters
    print("\n翻译参数:")
    window_size_input = input("窗口字符限制 [4000]: ").strip()
    window_size = int(window_size_input) if window_size_input else 4000
    overlap_input = input("重叠字符数 [200]: ").strip()
    overlap = int(overlap_input) if overlap_input else 200

    # Confirm execution
    if not get_yes_no("\n开始翻译? ", default=True):
        print("操作已取消")
        return

    # Parse PDF using backend API
    print("\n📄 步骤 1/4: 解析PDF文档")
    parse_options = {
        'use_window': False,
        'remove_images': True,
        'output_format': 'markdown'
    }
    parse_result = parse_pdf_from_backend(source, parse_options)

    if parse_result.get('status') != 'success':
        print_error("PDF解析失败")
        return

    text = parse_result['content']
    print_success(f"解析完成: {parse_result.get('pages', 0)} 页, {len(text)} 字符")

    # Extract proper nouns if enabled
    if auto_extract:
        print("\n📚 步骤 2/4: 提取专有名词")
        proper_nouns = extract_proper_nouns_backend(text=text, api_key=api_key, model=model)

        if proper_nouns:
            # Generate glossary from extracted nouns
            print("\n📝 步骤 3/4: 生成术语表")
            new_glossary = generate_glossary_backend(
                proper_nouns=proper_nouns,
                target_language=target_lang,
                api_key=api_key,
                model=model
            )
            glossary.update(new_glossary)

            if new_glossary:
                # Save glossary
                timestamp = get_timestamp()
                glossary_file = f"glossary_{timestamp}.json"
                save_glossary_to_file(glossary, glossary_file)

    # Translate text using backend API
    print("\n🌐 步骤 4/4: 翻译PDF内容")
    translated_text = translate_text_backend(
        text=text,
        glossary=glossary,
        source_lang=source_lang,
        target_lang=target_lang,
        api_key=api_key,
        model=model,
        window_size=window_size,
        overlap=overlap
    )

    if translated_text == text:
        print_error("翻译失败")
        return

    # Save result
    timestamp = get_timestamp()
    filename = sanitize_filename(f"translated_{timestamp}.md")
    save_result_to_file(translated_text, filename, 'markdown')

    # Update with glossary if needed
    if glossary and get_yes_no("是否使用术语表更新翻译? ", default=True):
        print("\n🔄 更新翻译...")
        updated_text = update_translation_with_glossary_backend(
            translated_text=translated_text,
            glossary=glossary,
            api_key=api_key,
            model=model
        )
        if updated_text != translated_text:
            timestamp = get_timestamp()
            filename = sanitize_filename(f"updated_{timestamp}.md")
            save_result_to_file(updated_text, filename, 'markdown')

    print_success("\n✅ 翻译完成！")


def run_glossary_workflow() -> None:
    """Execute glossary management workflow using backend API."""
    print_header("📚 术语表管理选项")

    # Check backend availability
    availability = check_backend_availability()
    if not availability['client']:
        print_error("后端LLM客户端模块不可用")
        input("按回车键继续...")
        return

    print("请选择操作:")
    print("1. 🔍 从PDF提取专有名词")
    print("2. 📝 生成翻译术语表")
    print("3. 🔄 更新现有术语表")
    print("4. 📋 查看术语表内容")
    print("5. 💾 导出术语表文件")

    operation = get_user_choice("选择操作 [1-5]: ", [str(i) for i in range(1, 6)])

    glossary_operations = {
        "1": extract_nouns_from_pdf_menu,
        "2": generate_glossary_menu,
        "3": update_glossary_menu,
        "4": view_glossary_menu,
        "5": export_glossary_menu
    }

    if operation in glossary_operations:
        glossary_operations[operation]()
    else:
        print("无效的选择")


def extract_nouns_from_pdf_menu():
    """Extract proper nouns from a PDF file using backend API."""
    print_header("🔍 从PDF提取专有名词")

    # Import parser interface
    try:
        from src.backend.parser_interface import parse_pdf
    except ImportError:
        try:
            from backend.parser_interface import parse_pdf
        except ImportError:
            print_error("无法导入 PDF 解析器")
            return

    pdf_path = get_file_path("请输入PDF文件路径: ")
    if not pdf_path:
        return

    model = input("模型名称 [Pro/moonshotai/Kimi-K2.5]: ").strip() or "Pro/moonshotai/Kimi-K2.5"
    api_key = os.getenv('SILICONFLOW_API_KEY')

    try:
        print("\n正在解析PDF...")
        result = parse_pdf(pdf_path, remove_images=True)
        if not result or not result.full_text:
            print_error("PDF解析失败")
            return

        print(f"解析完成: {len(result.pages)} 页")

        proper_nouns = extract_proper_nouns_backend(
            text=result.full_text,
            api_key=api_key,
            model=model
        )

        if proper_nouns:
            print_success(f"\n成功提取 {len(proper_nouns)} 个专有名词:")
            for i, noun in enumerate(proper_nouns[:20], 1):
                print(f"  {i:3}. {noun}")
            if len(proper_nouns) > 20:
                print(f"  ... 还有 {len(proper_nouns) - 20} 个")

            # Save to file
            if get_yes_no("\n是否保存到文件? ", default=True):
                timestamp = get_timestamp()
                filename = f"proper_nouns_{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    for noun in proper_nouns:
                        f.write(f"{noun}\n")
                print_success(f"已保存到: {filename}")
        else:
            print_warning("未提取到专有名词")

    except Exception as e:
        print_error(f"提取失败: {e}")


def generate_glossary_menu():
    """Generate translation glossary from proper nouns using backend API."""
    print_header("📝 生成翻译术语表")

    print("专有名词来源:")
    print("1. 从文件读取")
    print("2. 手动输入")

    source_type = get_user_choice("请选择 [1-2]: ", ["1", "2"])

    proper_nouns = []

    if source_type == "1":
        # Load from file
        noun_file = get_file_path("请输入专有名词列表文件: ")
        try:
            with open(noun_file, 'r', encoding='utf-8') as f:
                proper_nouns = [line.strip() for line in f if line.strip()]
            print_success(f"已读取 {len(proper_nouns)} 个专有名词")
        except Exception as e:
            print_error(f"读取文件失败: {e}")
            return
    else:
        # Manual input
        print("请输入专有名词（每行一个，空行结束）:")
        while True:
            noun = input().strip()
            if not noun:
                break
            proper_nouns.append(noun)

    if not proper_nouns:
        print_error("没有提供专有名词")
        return

    target_lang = input("目标语言 [中文]: ").strip() or "中文"
    model = input("模型名称 [Pro/moonshotai/Kimi-K2.5]: ").strip() or "Pro/moonshotai/Kimi-K2.5"
    api_key = os.getenv('SILICONFLOW_API_KEY')

    try:
        glossary = generate_glossary_backend(
            proper_nouns=proper_nouns,
            target_language=target_lang,
            api_key=api_key,
            model=model
        )

        if glossary:
            print_success(f"\n术语表生成完成:")
            for i, (orig, trans) in enumerate(list(glossary.items())[:10], 1):
                print(f"  {i:2}. {orig:30} -> {trans}")
            if len(glossary) > 10:
                print(f"  ... 还有 {len(glossary) - 10} 个")

            # Save to file
            if get_yes_no("\n是否保存到文件? ", default=True):
                timestamp = get_timestamp()
                filename = f"glossary_{timestamp}.json"
                save_glossary_to_file(glossary, filename)
        else:
            print_warning("术语表生成失败")

    except Exception as e:
        print_error(f"生成失败: {e}")


def update_glossary_menu():
    """Update existing glossary with new terms using backend API."""
    print_header("🔄 更新现有术语表")

    glossary_file = get_file_path("请输入现有术语表文件: ")
    if not Path(glossary_file).exists():
        print_error("文件不存在")
        return

    # Load existing glossary
    with open(glossary_file, 'r', encoding='utf-8') as f:
        glossary = json.load(f)

    print_success(f"已加载术语表: {len(glossary)} 个词条")

    # Get new terms
    noun_file = get_file_path("请输入新的专有名词列表文件: ", must_exist=False)
    if noun_file and Path(noun_file).exists():
        with open(noun_file, 'r', encoding='utf-8') as f:
            new_nouns = [line.strip() for line in f if line.strip()]
    else:
        print("\n请输入新的专有名词（每行一个，空行结束）:")
        new_nouns = []
        while True:
            noun = input().strip()
            if not noun:
                break
            new_nouns.append(noun)

    # Filter out existing terms
    new_terms = [n for n in new_nouns if n not in glossary]

    if not new_terms:
        print_info("没有新的专有名词需要添加")
        return

    print(f"\n将翻译 {len(new_terms)} 个新术语")

    target_lang = input("目标语言 [中文]: ").strip() or "中文"
    model = input("模型名称 [Pro/moonshotai/Kimi-K2.5]: ").strip() or "Pro/moonshotai/Kimi-K2.5"
    api_key = os.getenv('SILICONFLOW_API_KEY')

    try:
        new_translations = generate_glossary_backend(
            proper_nouns=new_terms,
            target_language=target_lang,
            api_key=api_key,
            model=model
        )

        if new_translations:
            glossary.update(new_translations)

            # Save updated glossary
            if get_yes_no("是否保存更新后的术语表? ", default=True):
                timestamp = get_timestamp()
                filename = f"glossary_{timestamp}.json"
                save_glossary_to_file(glossary, filename)

                print_success(f"术语表已更新: {len(glossary)} 个词条")
        else:
            print_warning("新术语翻译失败")

    except Exception as e:
        print_error(f"更新失败: {e}")


def view_glossary_menu():
    """View glossary content."""
    print_header("📋 查看术语表内容")

    glossary_file = get_file_path("请输入术语表文件: ")
    if not Path(glossary_file).exists():
        print_error("文件不存在")
        return

    try:
        glossary = load_glossary_from_file(glossary_file)

        print_success(f"\n术语表内容 ({len(glossary)} 个词条):")
        print("=" * 60)

        # Display in pages
        terms = list(glossary.items())
        page_size = 20
        for i in range(0, len(terms), page_size):
            page = terms[i:i+page_size]
            for j, (orig, trans) in enumerate(page, 1):
                print(f"{i+j:3}. {orig:30} -> {trans}")

            if i + page_size < len(terms):
                input(f"\n... 显示 {i+page_size}/{len(terms)}，按回车继续 ...")

        print("=" * 60)

    except Exception as e:
        print_error(f"读取失败: {e}")


def export_glossary_menu():
    """Export glossary to different formats."""
    print_header("💾 导出术语表文件")

    glossary_file = get_file_path("请输入术语表文件: ")
    if not Path(glossary_file).exists():
        print_error("文件不存在")
        return

    try:
        glossary = load_glossary_from_file(glossary_file)

        print("\n导出格式:")
        print("1. JSON 格式")
        print("2. Markdown 表格")
        print("3. Markdown 列表")
        print("4. 纯文本 (TSV)")

        format_choice = get_user_choice("选择格式 [1-4]: ", ["1", "2", "3", "4"])

        output_file = input("输出文件名: ").strip()
        if not output_file:
            timestamp = get_timestamp()
            output_file = f"glossary_export_{timestamp}"

        if format_choice == "1":
            output_file += ".json"
            save_glossary_to_file(glossary, output_file)

        elif format_choice == "2":
            output_file += ".md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 术语表翻译\n\n")
                f.write("| 原文 | 译文 |\n")
                f.write("|------|------|\n")
                for orig, trans in sorted(glossary.items()):
                    f.write(f"| {orig} | {trans} |\n")
            print_success(f"已导出到: {output_file}")

        elif format_choice == "3":
            output_file += ".md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 术语表翻译\n\n")
                for orig, trans in sorted(glossary.items()):
                    f.write(f"- [{orig}] -> {trans}\n")
            print_success(f"已导出到: {output_file}")

        else:  # TSV
            output_file += ".txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                for orig, trans in sorted(glossary.items()):
                    f.write(f"{orig}\t{trans}\n")
            print_success(f"已导出到: {output_file}")

    except Exception as e:
        print_error(f"导出失败: {e}")


def run_alignment_workflow() -> None:
    """Execute bilingual alignment workflow using backend API."""
    print_header("🔄 双语对齐选项")

    # Check backend availability
    availability = check_backend_availability()
    if not availability['client']:
        print_error("后端LLM客户端模块不可用，无法使用 LLM 进行对齐")
        input("按回车键继续...")
        return

    # Get file paths
    english_file = input("英文文本文件: ").strip()
    chinese_file = input("中文文本文件: ").strip()

    if not english_file or not chinese_file:
        print_error("必须提供英文和中文文件路径")
        return

    if not Path(english_file).exists():
        print_error(f"英文文件不存在: {english_file}")
        return

    if not Path(chinese_file).exists():
        print_error(f"中文文件不存在: {chinese_file}")
        return

    # Get alignment settings
    print("\n对齐设置:")
    window_limit_input = input("窗口字符限制 [4000]: ").strip()
    window_char_limit = int(window_limit_input) if window_limit_input else 4000
    overlap_input = input("重叠字符数 [500]: ").strip()
    overlap_chars = int(overlap_input) if overlap_input else 500

    # Get API settings
    api_key = os.getenv('SILICONFLOW_API_KEY')
    if not api_key:
        print_warning("未设置 SILICONFLOW_API_KEY 环境变量")
        if not get_yes_no("继续使用默认设置? ", default=False):
            print("操作已取消")
            return

    model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')

    # Confirm execution
    if not get_yes_no("\n开始对齐? ", default=True):
        print("操作已取消")
        return

    # Perform alignment using backend API
    try:
        print("\n📖 正在读取文件...")
        with open(english_file, 'r', encoding='utf-8') as f:
            english_text = f.read()
        with open(chinese_file, 'r', encoding='utf-8') as f:
            chinese_text = f.read()

        print(f"   英文: {len(english_text)} 字符")
        print(f"   中文: {len(chinese_text)} 字符")

        aligned_text = align_bilingual_text_backend(
            english_text=english_text,
            chinese_text=chinese_text,
            api_key=api_key,
            model=model,
            window_char_limit=window_char_limit,
            overlap_chars=overlap_chars
        )

        # Save result
        timestamp = get_timestamp()
        output_file = f"aligned_{timestamp}.md"
        save_result_to_file(aligned_text, output_file, 'markdown')

        print_success("\n双语对齐完成！")

    except Exception as e:
        print_error(f"对齐失败: {e}")
        import traceback
        print(traceback.format_exc())


def run_config_workflow() -> None:
    """Execute configuration management workflow."""
    print_header("⚙️  配置管理选项")

    # Create ConfigManager instance
    config_manager = ConfigManager()

    # Get configuration file paths
    config_paths = config_manager.get_config_paths()

    # Ensure config files exist
    if not config_manager.config_file.exists():
        print_info("配置文件不存在，正在创建默认配置文件...")
        config_manager.save_config()
        print_success(f"已创建配置文件: {config_paths['config']}")

    if not config_manager.env_file.exists():
        print_info("环境变量文件不存在，正在创建...")
        config_manager._save_env_vars_to_default()
        print_success(f"已创建环境变量文件: {config_paths['env']}")

    # Display configuration file paths
    print("\n📁 配置文件位置:")
    print(f"• 配置文件: {config_paths['config']}")
    print(f"• 环境变量: {config_paths['env']}")
    print(f"• 配置目录: {config_paths['config_dir']}")

    # Show current configuration status
    print("\n📊 当前配置状态:")
    config_manager.show_config_status()

    print("\n请选择操作:")
    print("1. 🔑 设置API密钥")
    print("2. 🤖 配置模型参数")
    print("3. 📊 设置解析器选项")
    print("4. 📁 查看配置文件")
    print("5. 🔄 重置配置")
    print("6. 💾 保存当前环境配置")
    print("7. 📥 导入配置文件")
    print("8. 📤 导出配置文件")
    print("9. ↩️  返回主菜单")

    operation = get_user_choice("选择操作 [1-9]: ", [str(i) for i in range(1, 10)])

    # Pass config_manager to sub-functions
    config_operations = {
        "1": lambda: set_api_key(config_manager),
        "2": lambda: set_model_config(config_manager),
        "3": lambda: set_parser_config(config_manager),
        "4": lambda: view_config_file(config_manager),
        "5": lambda: reset_config(config_manager),
        "6": lambda: save_config(config_manager),
        "7": lambda: import_config_file(config_manager),
        "8": lambda: export_config_file(config_manager),
        "9": lambda: None
    }

    if operation in config_operations:
        config_operations[operation]()
    else:
        print("无效的选择")


def set_api_key(config_manager: ConfigManager):
    """Set API key for translation service.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("🔑 设置API密钥")

    print("1. SiliconFlow")
    print("2. OpenAI")
    print("3. Ollama (本地)")

    provider_choice = get_user_choice("选择API提供商 [1-3]: ", ["1", "2", "3"])

    api_key = input("请输入API密钥: ").strip()

    if not api_key:
        print_error("API密钥不能为空")
        return

    # Map choice to provider name
    provider_map = {
        "1": "siliconflow",
        "2": "openai",
        "3": "ollama"
    }

    provider = provider_map[provider_choice]

    # Set API key using ConfigManager
    if config_manager.set_api_key(provider, api_key, auto_save=False):
        print_success(f"{provider} API密钥已临时设置")

        # Ask to save to .env file
        if get_yes_no("是否保存到配置文件? ", default=True):
            if config_manager.save_config():
                print_success("配置已保存")
            else:
                print_error("配置保存失败")


def set_model_config(config_manager: ConfigManager):
    """Configure model parameters.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("🤖 配置模型参数")

    current_model = config_manager.get("api.model", "Pro/moonshotai/Kimi-K2.5")
    model = input(f"模型名称 [{current_model}]: ").strip() or current_model

    if config_manager.set("api.model", model, auto_save=False):
        print(f"模型设置为: {model}")

        # Ask to save
        if get_yes_no("是否保存配置? ", default=True):
            if config_manager.save_config():
                print_success("配置已保存")
            else:
                print_error("配置保存失败")


def set_parser_config(config_manager: ConfigManager):
    """Configure parser options.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("📊 设置解析器选项")

    print("请选择解析器类型:")
    print("1. MinerU (推荐)")
    print("2. 其他 (未实现)")

    parser_type = get_user_choice("选择解析器类型 [1-2]: ", ["1", "2"])

    if parser_type == "1":
        config_manager.set("parser.type", "mineru", auto_save=False)

        # MinerU specific config
        token = input("MinerU API Token (可选，按回车跳过): ").strip()
        if token:
            config_manager.set_api_key("mineru", token, auto_save=False)

        api_url = input("MinerU API URL [https://mineru.net/api/v4]: ").strip()
        config_manager.set("parser.api_url", api_url or "https://mineru.net/api/v4", auto_save=False)

        # Ask to save
        if get_yes_no("是否保存配置? ", default=True):
            if config_manager.save_config():
                print_success("配置已保存")
            else:
                print_error("配置保存失败")

    print_success(f"解析器设置为: mineru")


def view_config_file(config_manager: ConfigManager):
    """View configuration file.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("📁 查看配置文件")

    paths = config_manager.get_config_paths()
    print(f"配置目录: {paths['config_dir']}")
    print(f"配置文件: {paths['config']}")
    print(f"环境文件: {paths['env']}\n")

    # Show config.json
    config_path = Path(paths['config'])
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print_info("配置文件内容 (config.json):")
        print("-" * 50)
        print(json.dumps(config, indent=2, ensure_ascii=False))
        print("-" * 50)
    else:
        print_info("配置文件不存在，将使用默认配置")

    # Show .env file
    env_path = Path(paths['env'])
    if env_path.exists():
        print_info("\n环境变量文件内容 (.env):")
        print("-" * 50)
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Mask API keys for security
            content = re.sub(r'(SILICONFLOW_API_KEY=|OPENAI_API_KEY=|OLLAMA_API_KEY=|MINERU_API_KEY=|MINERU_API_TOKEN=)(\S+)',
                           r'\1***MASKED***', content)
            print(content)
        print("-" * 50)
    else:
        print_info("\n环境变量文件不存在")


def reset_config(config_manager: ConfigManager):
    """Reset configuration to defaults.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("🔄 重置配置")

    if not confirm_action("确定要重置所有配置吗？", dangerous=True):
        print("操作已取消")
        return

    if config_manager.reset_config():
        print_success("配置已重置为默认值")
    else:
        print_error("配置重置失败")


def save_config(config_manager: ConfigManager):
    """Save current environment configuration to config files.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("💾 保存当前环境配置")

    if config_manager.save_config():
        print_success("配置已保存")

        # Also save env variables
        config_manager._save_env_vars_to_default()
        print_success("环境变量已保存")
    else:
        print_error("配置保存失败")


def import_config_file(config_manager: ConfigManager):
    """Import configuration from a specified file.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("📥 导入配置文件")

    # Show current config paths
    paths = config_manager.get_config_paths()
    print_info(f"默认配置目录: {paths['config_dir']}")
    print_info(f"默认配置文件: {paths['config']}")
    print_info(f"默认环境文件: {paths['env']}\n")

    # Get file path
    config_path = input("请输入配置文件路径 (.json 或 .env): ").strip()
    if not config_path:
        print_error("必须提供配置文件路径")
        return

    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        print_error(f"配置文件不存在: {config_path_obj}")
        return

    # Ask if merge or replace
    merge = get_yes_no("是否与现有配置合并? (否=替换) ", default=True)

    # Import configuration
    success = config_manager.import_config(config_path, merge=merge)

    if success:
        print_success("配置导入成功")
        print_info("配置已自动保存到默认配置目录")

        # Ask if user wants to verify
        if get_yes_no("是否查看导入后的配置状态? ", default=False):
            config_manager.show_config_status()
    else:
        print_error("配置导入失败")


def export_config_file(config_manager: ConfigManager):
    """Export current configuration to a specified file.

    Args:
        config_manager: The ConfigManager instance to use
    """
    print_header("📤 导出配置文件")

    # Show current config paths
    paths = config_manager.get_config_paths()
    print_info(f"当前配置目录: {paths['config_dir']}\n")

    # Choose export format
    print("导出格式:")
    print("1. JSON 格式 (config.json)")
    print("2. 环境变量格式 (.env)")

    format_choice = get_user_choice("选择导出格式 [1-2]: ", ["1", "2"])

    # Get output path
    if format_choice == "1":
        default_path = "config_export.json"
        suffix = ".json"
        include_env = False
    else:
        default_path = "config_export.env"
        suffix = ".env"
        include_env = True

    output_path = input(f"输出文件路径 [{default_path}]: ").strip() or default_path

    # Ensure correct suffix
    if not output_path.endswith(suffix):
        output_path += suffix

    # For .env export, ask if include all variables including empty ones
    if format_choice == "2" and include_env:
        include_all = get_yes_no("是否包含所有变量 (包括空值)? ", default=False)
    else:
        include_all = False

    # Export configuration
    success = config_manager.export_config(output_path, include_env=include_all)

    if success:
        print_success(f"配置已导出到: {output_path}")

        # Show exported path info
        output_path_obj = Path(output_path)
        print_info(f"文件大小: {output_path_obj.stat().st_size} 字节")
        print_info(f"绝对路径: {output_path_obj.absolute()}")
    else:
        print_error("配置导出失败")


def confirm_action(prompt: str, dangerous: bool = False) -> bool:
    """Confirm an action with the user."""
    if dangerous:
        print_warning("警告: 这是一个危险操作！")

    return get_yes_no(prompt, default=False)


def show_help_info() -> None:
    """Display help information."""
    print_header("ℹ️  帮助信息")

    help_text = """
TRPG PDF Translator 使用说明
============================

主要功能:
1. PDF解析 - 提取PDF文本内容，支持本地文件和URL
2. 翻译管道 - 完整的PDF翻译流程，包括术语表生成
3. 术语表管理 - 提取和管理专有名词翻译
4. 双语对齐 - 对齐英文和中文文本，生成对比视图

使用步骤:
1. 选择所需功能
2. 按照提示输入参数
3. 确认执行操作
4. 查看输出结果

配置要求:
- 需要配置API密钥和模型参数
- 支持多种PDF解析器
- 可自定义翻译参数

更多信息请参考项目文档。
"""

    print(help_text)
    input("按回车键返回主菜单...")


# Helper functions
def get_timestamp() -> str:
    """Generate a timestamp string."""
    import datetime
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
