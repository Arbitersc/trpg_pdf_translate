"""
Workflow Manager for TRPG PDF Translator CLI

This module provides workflow management for multi-step operations.
All functionality functions use backend API calls through direct Python imports.
"""

import time
import os
import sys
import json
import re
from pathlib import Path
from typing import Callable, List, Tuple, Optional, Dict, Any, Union

from utils import print_progress, print_error, print_success, print_info, print_warning

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import backend modules - use proper imports as per src/backend/CLAUDE.md
_api_available = False
_parser_available = False
_pipeline_available = False

BackendParserInterface = None
BackendClient = None
BackendPipeline = None
BackendUnifiedPipeline = None

try:
    from backend import (
        parse_pdf,
        parse_pdf_with_window,
        parse_pdf_file,
        parse_pdf_url,
        get_default_parser_config,
        create_parser,
        load_environment_config,
        get_loaded_env_path
    )
    BackendParserInterface = {
        'parse_pdf': parse_pdf,
        'parse_pdf_with_window': parse_pdf_with_window,
        'parse_pdf_file': parse_pdf_file,
        'parse_pdf_url': parse_pdf_url,
        'get_default_parser_config': get_default_parser_config,
        'create_parser': create_parser
    }
    _parser_available = True
    _config_loader_available = True
except ImportError as e:
    print_warning(f"警告: parser_interface 导入失败: {e}")
    _config_loader_available = False

try:
    from backend.client import SiliconFlowClient
    BackendClient = SiliconFlowClient
    _api_available = True
except ImportError as e:
    print_warning(f"警告: SiliconFlowClient 导入失败: {e}")

try:
    from backend.pipeline import (
        TranslationPipeline,
        UnifiedTranslationPipeline,
        split_text_by_strategy
    )
    BackendPipeline = TranslationPipeline
    BackendUnifiedPipeline = UnifiedTranslationPipeline
    _pipeline_available = True
except ImportError as e:
    print_warning(f"警告: pipeline 导入失败: {e}")


def check_backend_availability() -> Dict[str, bool]:
    """Check availability of backend modules.

    Returns:
        Dict mapping module names to availability status
    """
    return {
        'parser': _parser_available,
        'client': _api_available,
        'pipeline': _pipeline_available,
        'config_loader': _config_loader_available
    }


def reload_backend_config(env_path: Optional[Path] = None) -> bool:
    """Reload backend configuration from specified path.

    This function allows the frontend CLI to reload environment configuration
    after the user changes API keys or other settings.

    Args:
        env_path: Optional custom path to .env file. If None, reloads from default locations.

    Returns:
        True if reload was successful, False otherwise

    Example:
        # Reload from default locations
        reload_backend_config()

        # Reload from specific path
        reload_backend_config(Path.home() / ".trpg_pdf_translator" / ".env")
    """
    if not _config_loader_available:
        print_warning("警告: 配置加载器不可用，无法重新加载配置")
        return False

    try:
        from src.backend import reload_environment_config
        reload_environment_config(env_path)
        return True
    except ImportError:
        print_warning("警告: reload_environment_config 导入失败")
        return False


class WorkflowManager:
    """Manages multi-step workflows with progress tracking and error handling."""

    def __init__(self):
        self.steps: List[Tuple[Callable, str, str]] = []  # (function, description, active_form)
        self.current_step = 0
        self.total_steps = 0
        self.results = {}
        self.context: Dict[str, Any] = {}  # Store context between steps

    def add_step(self, step_func: Callable, description: str, active_form: Optional[str] = None):
        """Add a workflow step.

        Args:
            step_func: Function to execute for this step
            description: Description of what this step does
            active_form: Present continuous form for progress display
        """
        if active_form is None:
            active_form = description
        self.steps.append((step_func, description, active_form))
        self.total_steps = len(self.steps)

    def set_context(self, key: str, value: Any):
        """Store a value in the workflow context.

        Args:
            key: Context key
            value: Value to store
        """
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a value from the workflow context.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Value from context or default
        """
        return self.context.get(key, default)

    def run(self) -> bool:
        """Execute the complete workflow.

        Returns:
            bool: True if all steps completed successfully, False otherwise
        """
        if not self.steps:
            print("警告: 工作流为空")
            return False

        # Check backend availability
        availability = check_backend_availability()
        if not any(availability.values()):
            print_error("错误: 后端模块不可用，请确保 backend 模块已正确安装")
            print(f"   Parser: {'✅' if availability['parser'] else '❌'}")
            print(f"   Client: {'✅' if availability['client'] else '❌'}")
            print(f"   Pipeline: {'✅' if availability['pipeline'] else '❌'}")
            return False

        print(f"\n开始执行工作流 ({self.total_steps} 个步骤)...\n")

        for i, (step_func, description, active_form) in enumerate(self.steps, 1):
            self.current_step = i

            # Show progress
            print_progress(i, self.total_steps, description)

            try:
                # Execute step
                result = step_func()
                self.results[f"step_{i}"] = result

                # Show completion
                print(f"✅ {description} - 完成\n")

            except KeyboardInterrupt:
                print(f"\n❌ {description} - 被用户取消")
                return False

            except Exception as e:
                print_error(f"{description} - 失败: {e}")

                # Ask user what to do
                choice = self._handle_error(e, description)
                if choice == "retry":
                    return self._retry_step(i - 1)  # Adjust for 0-index
                elif choice == "skip":
                    print(f"⚠️  {description} - 已跳过")
                    continue
                else:  # abort
                    return False

        print("🎉 所有步骤已完成！")
        return True

    def _handle_error(self, error: Exception, step_description: str) -> str:
        """Handle workflow errors and get user input.

        Args:
            error: The exception that occurred
            step_description: Description of the failed step

        Returns:
            str: User choice ('retry', 'skip', 'abort')
        """
        print(f"\n步骤失败: {step_description}")
        print(f"错误详情: {error}")

        while True:
            print("\n请选择操作:")
            print("1. 🔄 重试当前步骤")
            print("2. ⏭️  跳过当前步骤")
            print("3. 🚫 中止工作流")

            choice = input("请输入选项 [1-3]: ").strip()

            if choice == "1":
                return "retry"
            elif choice == "2":
                return "skip"
            elif choice == "3":
                return "abort"
            else:
                print("无效选择，请重新输入")

    def _retry_step(self, step_index: int) -> bool:
        """Retry a specific step.

        Args:
            step_index: Index of the step to retry (0-indexed)

        Returns:
            bool: True if retry successful, False otherwise
        """
        if step_index < 0 or step_index >= len(self.steps):
            print("错误: 无效的步骤索引")
            return False

        step_func, description, active_form = self.steps[step_index]

        print(f"\n🔄 重试步骤: {description}")

        try:
            result = step_func()
            self.results[f"step_{step_index + 1}"] = result
            print(f"✅ {description} - 重试成功\n")

            # Continue with remaining steps
            for i in range(step_index + 1, len(self.steps)):
                step_func, description, active_form = self.steps[i]
                self.current_step = i + 1

                print_progress(i + 1, self.total_steps, description)
                result = step_func()
                self.results[f"step_{i + 1}"] = result
                print(f"✅ {description} - 完成\n")

            return True

        except Exception as e:
            print_error(f"重试失败: {e}")
            return False

    def show_progress(self):
        """Show current workflow progress."""
        if self.total_steps == 0:
            print("工作流未开始")
            return

        progress = (self.current_step / self.total_steps) * 100
        print(f"进度: {self.current_step}/{self.total_steps} ({progress:.1f}%)")

        if self.current_step > 0 and self.current_step <= len(self.steps):
            _, description, active_form = self.steps[self.current_step - 1]
            print(f"当前步骤: {active_form}")

    def get_result(self, step_key: str):
        """Get result from a specific step.

        Args:
            step_key: Key identifying the step (e.g., 'step_1')

        Returns:
            The result stored for that step, or None if not found
        """
        return self.results.get(step_key)

    def clear(self):
        """Clear the workflow and reset state."""
        self.steps.clear()
        self.current_step = 0
        self.total_steps = 0
        self.results.clear()
        self.context.clear()


# ============================================================================
# Backend Integration Functions - Using backend API as per src/backend/CLAUDE.md
# ============================================================================

def validate_pdf_source(source: str) -> bool:
    """Validate PDF source file or URL.

    Args:
        source: PDF file path or URL

    Returns:
        bool: True if source is valid, False otherwise
    """
    # Check if it's a URL
    if source.startswith(('http://', 'https://')):
        # Basic URL validation
        if not source.lower().endswith('.pdf'):
            print(f"⚠️  警告: URL 看起来不是 PDF 文件")
        return True

    # Check if it's a local file
    path = Path(source)
    if not path.exists():
        print_error(f"文件不存在: {source}")
        return False

    if not path.is_file():
        print_error(f"路径不是文件: {source}")
        return False

    if path.suffix.lower() != '.pdf':
        print_error(f"文件不是 PDF 格式: {source}")
        return False

    # Check file size
    file_size = path.stat().st_size
    if file_size == 0:
        print_error(f"PDF 文件为空: {source}")
        return False

    print(f"✅ PDF 验证通过: {source} ({file_size / 1024 / 1024:.2f} MB)")
    return True


def parse_pdf_from_backend(source: str, options: dict) -> dict:
    """Parse PDF using backend parser_interface API.

    Args:
        source: PDF file path or URL
        options: Parsing options dictionary including:
            - use_window: bool - use sliding window
            - window_size: int - pages per window for sliding window
            - overlap_pages: int - overlap pages for sliding window
            - remove_images: bool - remove markdown image links
            - verbose: bool - verbose output
            - output_format: str - 'text', 'markdown', or 'json'

    Returns:
        dict: Parsing result with status and content
    """
    if not _parser_available:
        return {"status": "error", "message": "后端解析器不可用"}

    try:
        is_url = source.startswith(('http://', 'https://'))
        use_window = options.get('use_window', False)
        remove_images = options.get('remove_images', True)
        window_size = options.get('window_size', 5)
        overlap_pages = options.get('overlap_pages', 1)
        output_format = options.get('output_format', 'markdown')

        print(f"📄 正在解析 PDF: {source}")
        print(f"   模式: {'URL' if is_url else '本地文件'}")

        # Call backend parser_interface API
        if use_window:
            result = BackendParserInterface['parse_pdf_with_window'](
                source=source,
                window_size=window_size,
                overlap_pages=overlap_pages,
                verbose=options.get('verbose', False)
            )
        else:
            if is_url:
                result = BackendParserInterface['parse_pdf_url'](
                    url=source,
                    remove_images=remove_images
                )
            else:
                result = BackendParserInterface['parse_pdf_file'](
                    file_path=source,
                    remove_images=remove_images
                )

        if not result or not result.full_text:
            return {"status": "error", "message": "解析失败：未提取到文本"}

        # Format output based on format option
        content = result.full_text

        if output_format == 'json':
            # Add metadata to JSON output
            output = {
                "status": "success",
                "content": content,
                "format": "json",
                "pages": len(result.pages),
                "metadata": {
                    "page_breaks": result.page_breaks,
                    "total_pages": len(result.pages)
                }
            }
        else:
            output = {
                "status": "success",
                "content": content,
                "format": output_format,
                "pages": len(result.pages)
            }

        print(f"✅ 解析完成: {len(result.pages)} 页, {len(content)} 字符")
        return output

    except Exception as e:
        print_error(f"解析失败: {e}")
        return {"status": "error", "message": str(e)}


def extract_proper_nouns_backend(text: str, api_key: str = None, model: str = None) -> list:
    """Extract proper nouns using backend SiliconFlowClient API.

    Args:
        text: PDF text content
        api_key: API key for translation service (uses env var if not provided)
        model: Model name for LLM (uses env var if not provided)

    Returns:
        list: List of extracted proper nouns
    """
    if not _api_available:
        print_warning("后端翻译客户端不可用")
        return []

    try:
        if not text:
            print("⚠️  警告: 没有提供文本内容，跳过专有名词提取")
            return []

        print("🔍 正在提取专有名词...")

        # Load API key from environment if not provided
        if not api_key:
            api_key = os.getenv('SILICONFLOW_API_KEY')

        if not api_key:
            print_warning("未配置 API 密钥，无法使用 LLM 提取专有名词")
            return []

        if not model:
            model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')

        # Create backend client and extract proper nouns
        client = BackendClient(api_key=api_key)

        # Use first chunk of text for extraction to avoid context limits
        sample_text = text[:5000] if len(text) > 5000 else text

        proper_nouns = client.extract_proper_nouns(
            model=model,
            text=sample_text,
            stream_print=False
        )

        # Remove duplicates while preserving order
        proper_nouns = list(dict.fromkeys(proper_nouns))

        if proper_nouns:
            print_success(f"提取到 {len(proper_nouns)} 个专有名词")
            print(f"   前10个: {proper_nouns[:10]}...")
        else:
            print_warning("未提取到专有名词")

        return proper_nouns

    except Exception as e:
        print_error(f"专有名词提取失败: {e}")
        return []


def generate_glossary_backend(proper_nouns: list, target_language: str = "中文",
                              api_key: str = None, model: str = None) -> dict:
    """Generate translation glossary using backend SiliconFlowClient API.

    Args:
        proper_nouns: List of proper nouns to translate
        target_language: Target language (default: Chinese)
        api_key: API key for translation service (uses env var if not provided)
        model: Model name for LLM (uses env var if not provided)

    Returns:
        dict: Glossary mapping original terms to translations
    """
    if not _api_available:
        print_warning("后端翻译客户端不可用")
        return {}

    try:
        if not proper_nouns or not isinstance(proper_nouns, list):
            print_warning("没有提供专有名词列表，跳过术语表生成")
            return {}

        print(f"📝 正在生成 {len(proper_nouns)} 个专有名词的翻译术语表...")

        if not api_key:
            api_key = os.getenv('SILICONFLOW_API_KEY')

        if not api_key:
            print_warning("未配置 API 密钥，无法生成术语表")
            return {}

        if not model:
            model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')

        client = BackendClient(api_key=api_key)

        # Use backend client API
        glossary = client.generate_glossary(
            model=model,
            proper_nouns=proper_nouns,
            target_language=target_language,
            stream_print=False
        )

        if glossary:
            print_success(f"术语表生成完成: {len(glossary)} 个词条")
            # Show some examples
            examples = list(glossary.items())[:5]
            print(f"   示例: {examples}")
        else:
            print_warning("术语表生成失败")

        return glossary

    except Exception as e:
        print_error(f"术语表生成失败: {e}")
        return {}


def translate_text_backend(text: str, glossary: dict = None,
                          source_lang: str = "English", target_lang: str = "中文",
                          api_key: str = None, model: str = None,
                          window_size: int = 4000, overlap: int = 200) -> str:
    """Translate text using backend SiliconFlowClient API.

    Args:
        text: Text to translate
        glossary: Translation glossary (optional)
        source_lang: Source language
        target_lang: Target language
        api_key: API key for translation service (uses env var if not provided)
        model: Model name for LLM (uses env var if not provided)
        window_size: Character limit per chunk
        overlap: Overlap characters between chunks

    Returns:
        str: Translated text
    """
    if not _api_available:
        print_warning("后端翻译客户端不可用")
        return text

    try:
        print(f"🌐 正在翻译文本 ({len(text)} 字符)...")

        if not api_key:
            api_key = os.getenv('SILICONFLOW_API_KEY')

        if not api_key:
            print_warning("未配置 API 密钥，无法翻译")
            return text

        if not model:
            model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')

        client = BackendClient(api_key=api_key)

        # Use backend client API
        translated_text = client.translate_text(
            model=model,
            text=text,
            source_language=source_lang,
            target_language=target_lang,
            glossary=glossary or {},
            stream_print=True,
            chunk_size=window_size,
            overlap=overlap
        )

        print_success(f"翻译完成: {len(translated_text)} 字符")
        return translated_text

    except Exception as e:
        print_error(f"翻译失败: {e}")
        return text


def update_translation_with_glossary_backend(translated_text: str, glossary: dict,
                                             api_key: str = None, model: str = None) -> str:
    """Update translated text with glossary using backend API.

    Args:
        translated_text: Translated text to update
        glossary: Glossary for consistency update
        api_key: API key for translation service (uses env var if not provided)
        model: Model name for LLM (uses env var if not provided)

    Returns:
        str: Updated translation
    """
    if not _api_available:
        print_warning("后端翻译客户端不可用")
        return translated_text

    try:
        if not translated_text or not glossary:
            return translated_text

        print("🔄 正在使用术语表更新翻译...")

        if not api_key:
            api_key = os.getenv('SILICONFLOW_API_KEY')

        if not api_key:
            print_warning("未配置 API 密钥，无法更新翻译")
            return translated_text

        if not model:
            model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')

        client = BackendClient(api_key=api_key)

        updated_text = client.update_translation_with_glossary(
            model=model,
            translation=translated_text,
            glossary=glossary,
            stream_print=False
        )

        print_success("翻译更新完成")
        return updated_text

    except Exception as e:
        print_error(f"翻译更新失败: {e}")
        return translated_text


def align_bilingual_text_backend(english_text: str, chinese_text: str,
                                 api_key: str = None, model: str = None,
                                 window_char_limit: int = 4000, overlap_chars: int = 500) -> str:
    """Align bilingual text using backend SiliconFlowClient API.

    Args:
        english_text: English text
        chinese_text: Chinese text
        api_key: API key for translation service (uses env var if not provided)
        model: Model name for LLM (uses env var if not provided)
        window_char_limit: Character limit per window
        overlap_chars: Overlap characters between windows

    Returns:
        str: Aligned bilingual text
    """
    if not _api_available:
        print_warning("后端翻译客户端不可用")
        return ""

    try:
        print("🔄 正在对齐双语文本...")

        if not api_key:
            api_key = os.getenv('SILICONFLOW_API_KEY')

        if not api_key:
            print_warning("未配置 API 密钥，无法对齐双语文本")
            return ""

        if not model:
            model = os.getenv('SILICONFLOW_MODEL', 'Pro/moonshotai/Kimi-K2.5')

        client = BackendClient(api_key=api_key)

        aligned_text = client.align_bilingual_text(
            model=model,
            english_text=english_text,
            chinese_text=chinese_text,
            stream_print=True,
            window_char_limit=window_char_limit,
            overlap_chars=overlap_chars
        )

        print_success("双语对齐完成")
        return aligned_text

    except Exception as e:
        print_error(f"双语对齐失败: {e}")
        return ""


def split_text_backend(text: str, strategy: str = "paragraph",
                      window_char_limit: int = 4000, overlap_paragraphs: int = 2) -> List[str]:
    """Split text using backend pipeline API.

    Args:
        text: Text to split
        strategy: Splitting strategy ('paragraph', 'sentence', 'char')
        window_char_limit: Character limit per window
        overlap_paragraphs: Number of paragraphs to overlap

    Returns:
        List of text chunks
    """
    if not _pipeline_available:
        print_warning("后端 pipeline 不可用，使用简单分割")
        # Fallback: simple paragraph split
        paragraphs = re.split(r'\n\n+', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    try:
        return split_text_by_strategy(
            text=text,
            strategy=strategy,
            window_char_limit=window_char_limit,
            overlap_paragraphs=overlap_paragraphs
        )
    except Exception as e:
        print_error(f"文本分割失败: {e}")
        return [text]


def run_translation_pipeline_backend(source: str, target_language: str = "中文",
                                     export_bilingual: bool = False,
                                     optimize_formatting: bool = False,
                                     api_key: str = None, model: str = None) -> dict:
    """Run complete translation pipeline using backend TranslationPipeline class.

    Args:
        source: PDF file path or URL
        target_language: Target language
        export_bilingual: Whether to export bilingual format
        optimize_formatting: Whether to optimize PDF formatting
        api_key: API key for translation service (uses env var if not provided)
        model: Model name for LLM (uses env var if not provided)

    Returns:
        dict: Translation result
    """
    if not _pipeline_available or not BackendPipeline:
        print_warning("后端翻译流水线不可用")
        return {"status": "error", "message": "Backend pipeline not available"}

    try:
        print("🚀 正在启动翻译流水线...")

        pipeline = BackendPipeline(api_key=api_key, model=model)

        result = pipeline.process_document(
            pdf_path=source,
            target_language=target_language,
            export_bilingual=export_bilingual,
            optimize_formatting=optimize_formatting
        )

        print_success("翻译流水线执行完成")
        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        print_error(f"翻译流水线执行失败: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Helper Functions
# ============================================================================

def save_result_to_file(content: str, filepath: str, format: str = 'markdown') -> bool:
    """Save content to a file.

    Args:
        content: Content to save
        filepath: Output file path
        format: Output format ('markdown', 'text', 'json')

    Returns:
        bool: True if successful
    """
    try:
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"content": content}, f, ensure_ascii=False, indent=2)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        print_success(f"结果已保存到: {filepath}")
        return True

    except Exception as e:
        print_error(f"保存文件失败: {e}")
        return False


def load_glossary_from_file(filepath: str) -> dict:
    """Load glossary from JSON file.

    Args:
        filepath: Path to glossary JSON file

    Returns:
        dict: Glossary dictionary
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"加载术语表失败: {e}")
        return {}


def save_glossary_to_file(glossary: dict, filepath: str) -> bool:
    """Save glossary to JSON file.

    Args:
        glossary: Glossary dictionary
        filepath: Output file path

    Returns:
        bool: True if successful
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)
        print_success(f"术语表已保存到: {filepath}")
        return True
    except Exception as e:
        print_error(f"保存术语表失败: {e}")
        return False


# ============================================================================
# Workflow Creator Functions
# ============================================================================

def create_pdf_parse_workflow(source: str, options: dict) -> WorkflowManager:
    """Create a workflow for PDF parsing.

    Args:
        source: PDF file path or URL
        options: Parsing options dictionary

    Returns:
        WorkflowManager: Configured workflow
    """
    workflow = WorkflowManager()

    # Step 1: Validate source
    workflow.add_step(
        lambda: validate_pdf_source(source),
        "验证PDF源文件",
        "正在验证PDF源文件"
    )

    # Step 2: Parse PDF
    workflow.add_step(
        lambda: parse_pdf_from_backend(source, options),
        "解析PDF内容",
        "正在解析PDF内容"
    )

    return workflow


def create_translation_workflow(source: str, translation_config: dict) -> WorkflowManager:
    """Create a workflow for PDF translation.

    Args:
        source: PDF file path or URL
        translation_config: Translation configuration

    Returns:
        WorkflowManager: Configured workflow
    """
    workflow = WorkflowManager()

    # Add PDF source to workflow context
    workflow.set_context('source', source)

    # Step 1: Parse PDF
    def parse_step():
        options = {
            'use_window': False,
            'remove_images': True,
            'output_format': 'markdown'
        }
        result = parse_pdf_from_backend(source, options)
        if result.get('status') == 'success':
            workflow.set_context('text', result.get('content', ''))
            workflow.set_context('pages', result.get('pages', 0))
        return result

    workflow.add_step(
        parse_step,
        "解析PDF文档",
        "正在解析PDF文档"
    )

    # Step 2: Extract proper nouns (if enabled)
    if translation_config.get('auto_extract', True):
        def extract_step():
            text = workflow.get_context('text', '')
            api_key = translation_config.get('api_key')
            model = translation_config.get('model')
            proper_nouns = extract_proper_nouns_backend(text=text, api_key=api_key, model=model)
            workflow.set_context('proper_nouns', proper_nouns)
            return proper_nouns

        workflow.add_step(
            extract_step,
            "提取专有名词",
            "正在提取专有名词"
        )

    # Step 3: Generate glossary
    def glossary_step():
        proper_nouns = workflow.get_context('proper_nouns', [])
        if not proper_nouns:
            return {}

        api_key = translation_config.get('api_key')
        model = translation_config.get('model')
        target_lang = translation_config.get('target_language', '中文')

        glossary = generate_glossary_backend(
            proper_nouns=proper_nouns,
            target_language=target_lang,
            api_key=api_key,
            model=model
        )
        workflow.set_context('glossary', glossary)
        return glossary

    workflow.add_step(
        glossary_step,
        "生成术语表",
        "正在生成术语表"
    )

    # Step 4: Translate content
    def translate_step():
        text = workflow.get_context('text', '')
        glossary = workflow.get_context('glossary', {})
        api_key = translation_config.get('api_key')
        model = translation_config.get('model')
        source_lang = translation_config.get('source_language', 'English')
        target_lang = translation_config.get('target_language', '中文')

        translated_text = translate_text_backend(
            text=text,
            glossary=glossary,
            source_lang=source_lang,
            target_lang=target_lang,
            api_key=api_key,
            model=model
        )
        workflow.set_context('translated_text', translated_text)
        return translated_text

    workflow.add_step(
        translate_step,
        "翻译PDF内容",
        "正在翻译PDF内容"
    )

    return workflow
