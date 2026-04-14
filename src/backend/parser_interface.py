"""
Parser Interface Module

Provides a unified interface for accessing different PDF parsers
through a factory pattern. This module abstracts away the details
of specific parser implementations.
"""

import os
import re
from typing import Dict, Any, Optional, Union, Type, List
from pathlib import Path

# Import base parser classes first
from .parsers.base import PDFParserBase, ParseResult, ParserError

# Import parser implementations
from .parsers.mineru.client import MinerUClient
from .parsers.mineru.extractor import MinerUExtractor

# Import shared configuration loader and load environment
from .config_loader import load_environment_config
load_environment_config()


# Registry of available parsers
_PARSER_REGISTRY: Dict[str, Type[PDFParserBase]] = {
    "mineru": MinerUExtractor,
}


class ParserFactory:
    """
    Factory class for creating parser instances.

    Supports creation of different parser types with configuration.
    """

    @staticmethod
    def create_parser(
        parser_type: str = "mineru",
        **kwargs
    ) -> PDFParserBase:
        """
        Create a parser instance of the specified type.

        Args:
            parser_type: Type of parser to create ("mineru")
            **kwargs: Parser-specific configuration

        Returns:
            Instance of the requested parser

        Raises:
            ValueError: If parser_type is not supported
        """
        parser_type = parser_type.lower()

        if parser_type not in _PARSER_REGISTRY:
            available = ", ".join(_PARSER_REGISTRY.keys())
            raise ValueError(
                f"Unknown parser type: {parser_type}. "
                f"Available parsers: {available}"
            )

        parser_class = _PARSER_REGISTRY[parser_type]
        return parser_class(**kwargs)

    @staticmethod
    def register_parser(
        parser_type: str,
        parser_class: Type[PDFParserBase]
    ) -> None:
        """
        Register a new parser type with the factory.

        Args:
            parser_type: Unique identifier for the parser
            parser_class: Parser class implementing PDFParserBase
        """
        _PARSER_REGISTRY[parser_type.lower()] = parser_class

    @staticmethod
    def get_available_parsers() -> List[str]:
        """
        Get list of available parser types.

        Returns:
            List of registered parser type identifiers
        """
        return list(_PARSER_REGISTRY.keys())


def get_default_parser_config() -> Dict[str, Any]:
    """
    Get default parser configuration from environment variables.

    Reads configuration for the default parser (MinerU) from environment.

    Returns:
        Dictionary with parser configuration
    """
    config = {
        "parser_type": os.getenv("PDF_PARSER_TYPE", "mineru").lower(),
    }

    # MinerU-specific configuration
    if config["parser_type"] == "mineru":
        config["token"] = os.getenv("MINERU_API_TOKEN")
        config["api_url"] = os.getenv("MINERU_API_URL", "https://mineru.net/api/v4")
        config["model_version"] = os.getenv("MINERU_MODEL_VERSION", "vlm")
        config["timeout"] = int(os.getenv("MINERU_TIMEOUT", "300"))
        config["poll_interval"] = int(os.getenv("MINERU_POLL_INTERVAL", "5"))

    return config


def _remove_markdown_images(text: str) -> str:
    """
    Remove all markdown image links from text.

    Removes patterns like: ![alt](images/...) and ![](images/...)

    Args:
        text: Text containing markdown image links

    Returns:
        Text with all image links removed
    """
    # Match markdown image syntax: ![alt](image_url) or ![](image_url)
    # This matches both with and without alt text
    pattern = r'!\[.*?\]\(images/[^)]+\)'
    return re.sub(pattern, '', text)


def _postprocess_result(
    result: ParseResult,
    remove_images: bool = False
) -> ParseResult:
    """
    Apply post-processing to parsed result.

    Args:
        result: ParseResult to post-process
        remove_images: Whether to remove markdown image links

    Returns:
        Post-processed ParseResult
    """
    if not remove_images:
        return result

    # Clean full_text
    result.full_text = _remove_markdown_images(result.full_text)

    # Clean individual page texts
    for page in result.pages:
        page.text = _remove_markdown_images(page.text)

    return result


def create_parser(
    parser_type: Optional[str] = None,
    use_env_config: bool = True,
    **kwargs
) -> PDFParserBase:
    """
    Create a parser instance with optional environment-based configuration.

    This is a convenience function that combines config loading and parser creation.

    Args:
        parser_type: Type of parser to create (uses default if not specified)
        use_env_config: Whether to load configuration from environment variables
        **kwargs: Additional parser configuration (overrides env config)

    Returns:
        Configured parser instance

    Example:
        # Use default configuration from environment
        parser = create_parser()

        # Specify parser type explicitly
        parser = create_parser(parser_type="mineru")

        # Override specific configuration
        parser = create_parser(token="custom_token", timeout=600)
    """
    # Determine parser type
    if parser_type is None:
        env_config = get_default_parser_config()
        parser_type = env_config.get("parser_type", "mineru")

    # Load environment config if requested
    if use_env_config:
        env_config = get_default_parser_config()
        # Only add settings for the requested parser type
        if parser_type.lower() == "mineru":
            kwargs.setdefault("token", env_config.get("token"))
            kwargs.setdefault("api_url", env_config.get("api_url"))
            kwargs.setdefault("model_version", env_config.get("model_version"))
            kwargs.setdefault("timeout", env_config.get("timeout"))
            kwargs.setdefault("poll_interval", env_config.get("poll_interval"))

    return ParserFactory.create_parser(parser_type, **kwargs)


def parse_pdf(
    source: Union[str, Path],
    parser_type: Optional[str] = None,
    remove_images: bool = True,
    **kwargs
) -> ParseResult:
    """
    Parse a PDF file or URL.

    Convenience function that creates a parser and parses the file in one call.

    Args:
        source: Path to local file or URL
        parser_type: Type of parser to use (uses default if not specified)
        remove_images: Whether to remove markdown image links (default: True)
        **kwargs: Additional parsing options

    Returns:
        ParseResult with extracted content

    Example:
        result = parse_pdf("/path/to/document.pdf")
        print(result.full_text)

        # Parse with options
        result = parse_pdf(
            "/path/to/document.pdf",
            page_ranges="1-10",
            verbose=True
        )
    """
    parser = create_parser(parser_type=parser_type, **kwargs)
    result = parser.parse(source, **kwargs)
    return _postprocess_result(result, remove_images=remove_images)


def parse_pdf_file(
    file_path: Union[str, Path],
    parser_type: Optional[str] = None,
    remove_images: bool = True,
    **kwargs
) -> ParseResult:
    """
    Parse a local PDF file.

    Convenience function for parsing local files.

    Args:
        file_path: Path to the PDF file
        parser_type: Type of parser to use
        remove_images: Whether to remove markdown image links (default: True)
        **kwargs: Additional parsing options

    Returns:
        ParseResult with extracted content
    """
    parser = create_parser(parser_type=parser_type, **kwargs)
    result = parser.parse_file(file_path, **kwargs)
    return _postprocess_result(result, remove_images=remove_images)


def parse_pdf_url(
    url: str,
    parser_type: Optional[str] = None,
    remove_images: bool = True,
    **kwargs
) -> ParseResult:
    """
    Parse a PDF from URL.

    Convenience function for parsing from URLs.

    Args:
        url: URL to the PDF file
        parser_type: Type of parser to use
        remove_images: Whether to remove markdown image links (default: True)
        **kwargs: Additional parsing options

    Returns:
        ParseResult with extracted content
    """
    parser = create_parser(parser_type=parser_type, **kwargs)
    result = parser.parse_url(url, **kwargs)
    return _postprocess_result(result, remove_images=remove_images)


def parse_pdf_with_window(
    source: Union[str, Path],
    parser_type: Optional[str] = None,
    window_size: int = 5,
    overlap_pages: int = 1,
    remove_images: bool = True,
    **kwargs
) -> ParseResult:
    """
    Parse a PDF file or URL using sliding window approach.

    Convenience function that creates a parser and parses with
    sliding windows in one call.

    Args:
        source: Path to local file or URL
        parser_type: Type of parser to use (uses default if not specified)
        window_size: Number of pages per window (default: 5)
        overlap_pages: Number of overlapping pages (default: 1)
        remove_images: Whether to remove markdown image links (default: True)
        **kwargs: Additional parsing options

    Returns:
        ParseResult with extracted content

    Example:
        # Parse with default settings (5-page windows, 1-page overlap)
        result = parse_pdf_with_window("/path/to/document.pdf")

        # Parse with custom settings
        result = parse_pdf_with_window(
            "/path/to/document.pdf",
            window_size=10,
            overlap_pages=2,
            verbose=True
        )
    """
    parser = create_parser(parser_type=parser_type, **kwargs)

    is_url = str(source).startswith(("http://", "https://"))

    if is_url:
        result = parser.parse_url_with_window(
            url=str(source),
            window_size=window_size,
            overlap_pages=overlap_pages,
            **kwargs
        )
    else:
        result = parser.parse_file_with_window(
            file_path=Path(source),
            window_size=window_size,
            overlap_pages=overlap_pages,
            **kwargs
        )

    return _postprocess_result(result, remove_images=remove_images)


# Re-export key classes and functions
__all__ = [
    "ParserFactory",
    "create_parser",
    "parse_pdf",
    "parse_pdf_file",
    "parse_pdf_url",
    "parse_pdf_with_window",
    "get_default_parser_config",
    "PDFParserBase",
    "ParseResult",
    "ParserError",
    # Parser-specific exports
    "MinerUClient",
    "MinerUExtractor",
    # Post-processing functions
    "_remove_markdown_images",
    "_postprocess_result",
]
