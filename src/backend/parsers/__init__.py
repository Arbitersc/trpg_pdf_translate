"""
PDF Parser Framework

Base classes and interfaces for PDF text extraction.
"""

from .base import PDFParserBase, ParseResult, PageResult, ParserError, FileFormatError, APIError, TaskTimeoutError

__all__ = [
    "PDFParserBase",
    "ParseResult",
    "PageResult",
    "ParserError",
    "FileFormatError",
    "APIError",
    "TaskTimeoutError"
]
