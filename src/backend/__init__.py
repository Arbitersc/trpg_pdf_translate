"""
TRPG PDF Translator Backend

Package for translating TRPG documents using LLMs.
Includes PDF parsing capabilities.
"""

from .client import SiliconFlowClient
from .pipeline import TranslationPipeline
from .parser_interface import (
    ParserFactory,
    create_parser,
    parse_pdf,
    parse_pdf_file,
    parse_pdf_url,
    parse_pdf_with_window,
    get_default_parser_config
)
from .config_loader import (
    load_environment_config,
    get_loaded_env_path,
    get_env_value,
    reload_environment_config
)

__all__ = [
    "SiliconFlowClient",
    "TranslationPipeline",
    "ParserFactory",
    "create_parser",
    "parse_pdf",
    "parse_pdf_file",
    "parse_pdf_url",
    "parse_pdf_with_window",
    "get_default_parser_config",
    # Config loader exports
    "load_environment_config",
    "get_loaded_env_path",
    "get_env_value",
    "reload_environment_config"
]

__version__ = "0.1.0"
