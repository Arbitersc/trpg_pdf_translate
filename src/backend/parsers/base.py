"""
Base classes for PDF parsers.

Provides abstract interface and data structures for PDF text extraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import json


@dataclass
class PageResult:
    """
    Result of parsing a single page from a PDF.

    Attributes:
        page_number: The page number (1-indexed)
        text: Extracted text content
        images: List of image paths or descriptions
        tables: List of table data (if any)
        metadata: Additional page-level metadata
    """
    page_number: int
    text: str
    images: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"PageResult(page={self.page_number}, text='{text_preview}')"


@dataclass
class ParseResult:
    """
    Complete result of parsing a PDF document.

    Attributes:
        success: Whether parsing was successful
        file_path: Path or URL of the parsed file
        total_pages: Total number of pages parsed
        pages: List of individual page results
        full_text: Complete text from all pages concatenated
        metadata: Document-level metadata
        errors: List of any errors encountered during parsing
    """

    success: bool
    file_path: Union[str, Path]
    total_pages: int
    pages: List[PageResult]
    full_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"ParseResult(status={status}, pages={self.total_pages}, errors={len(self.errors)})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "file_path": str(self.file_path),
            "total_pages": self.total_pages,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "images": p.images,
                    "tables": p.tables,
                    "metadata": p.metadata
                }
                for p in self.pages
            ],
            "full_text": self.full_text,
            "metadata": self.metadata,
            "errors": self.errors
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_json(self, file_path: Union[str, Path]) -> None:
        """Save result to JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())


class PDFParserBase(ABC):
    """
    Abstract base class for PDF parsers.

    All PDF parser implementations should inherit from this class
    and implement the required methods.
    """

    def __init__(self, **kwargs):
        """
        Initialize the parser with configuration options.

        Args:
            **kwargs: Parser-specific configuration options
        """
        self.config = kwargs

    @abstractmethod
    def parse_file(
        self,
        file_path: Union[str, Path],
        **kwargs
    ) -> ParseResult:
        """
        Parse a local PDF file.

        Args:
            file_path: Path to the PDF file
            **kwargs: Additional parsing options

        Returns:
            ParseResult containing the extracted content
        """
        pass

    @abstractmethod
    def parse_url(
        self,
        url: str,
        **kwargs
    ) -> ParseResult:
        """
        Parse a PDF from a URL.

        Args:
            url: URL to the PDF file
            **kwargs: Additional parsing options

        Returns:
            ParseResult containing the extracted content
        """
        pass

    def parse(
        self,
        source: Union[str, Path],
        **kwargs
    ) -> ParseResult:
        """
        Parse a PDF from file path or URL (auto-detected).

        Args:
            source: Path to local file or URL
            **kwargs: Additional parsing options

        Returns:
            ParseResult containing the extracted content
        """
        source_str = str(source)

        # Check if source is a URL
        if source_str.startswith(("http://", "https://")):
            return self.parse_url(source_str, **kwargs)

        # Otherwise treat as local file path
        return self.parse_file(source, **kwargs)

    def get_page_text(self, page_number: int, result: ParseResult) -> str:
        """
        Get text for a specific page.

        Args:
            page_number: Page number (1-indexed)
            result: ParseResult from a previous parse operation

        Returns:
            Text content for the specified page

        Raises:
            IndexError: If page_number is out of range
        """
        if not result.pages or page_number < 1 or page_number > len(result.pages):
            raise IndexError(f"Page {page_number} is out of range (1-{len(result.pages)})")

        return result.pages[page_number - 1].text

    def parse_with_sliding_window(
        self,
        source: Union[str, Path],
        window_size: int = 5,
        overlap_pages: int = 1,
        is_url: bool = False,
        **kwargs
    ) -> ParseResult:
        """
        Parse a PDF using sliding window approach with overlapping pages.

        This is a base implementation that can be overridden by subclasses
        for more efficient window parsing.

        Args:
            source: Path to local file or URL
            window_size: Number of pages per window
            overlap_pages: Number of overlapping pages between windows
            is_url: Whether source is a URL
            **kwargs: Additional parsing options

        Returns:
            ParseResult with merged content
        """
        # Default implementation requires override by subclass
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support sliding window parsing. "
            f"Use parse_file_with_window or parse_url_with_window for specific parsers."
        )

    def parse_file_with_window(
        self,
        file_path: Union[str, Path],
        window_size: int = 5,
        overlap_pages: int = 1,
        **kwargs
    ) -> ParseResult:
        """
        Parse a local PDF file using sliding window approach.

        Args:
            file_path: Path to the PDF file
            window_size: Number of pages per window
            overlap_pages: Number of overlapping pages
            **kwargs: Additional parsing options

        Returns:
            ParseResult with merged content
        """
        return self.parse_with_sliding_window(
            file_path,
            window_size=window_size,
            overlap_pages=overlap_pages,
            is_url=False,
            **kwargs
        )

    def parse_url_with_window(
        self,
        url: str,
        window_size: int = 5,
        overlap_pages: int = 1,
        **kwargs
    ) -> ParseResult:
        """
        Parse a PDF from URL using sliding window approach.

        Args:
            url: URL to the PDF file
            window_size: Number of pages per window
            overlap_pages: Number of overlapping pages
            **kwargs: Additional parsing options

        Returns:
            ParseResult with merged content
        """
        return self.parse_with_sliding_window(
            url,
            window_size=window_size,
            overlap_pages=overlap_pages,
            is_url=True,
            **kwargs
        )

    def get_text_range(
        self,
        start_page: int,
        end_page: int,
        result: ParseResult
    ) -> str:
        """
        Get text for a range of pages.

        Args:
            start_page: Starting page number (1-indexed, inclusive)
            end_page: Ending page number (1-indexed, inclusive)
            result: ParseResult from a previous parse operation

        Returns:
            Text content for the specified page range

        Raises:
            IndexError: If page numbers are out of range
        """
        if not result.pages:
            raise IndexError("No pages in result")

        if start_page < 1 or start_page > len(result.pages):
            raise IndexError(f"Start page {start_page} is out of range (1-{len(result.pages)})")

        if end_page < 1 or end_page > len(result.pages):
            raise IndexError(f"End page {end_page} is out of range (1-{len(result.pages)})")

        if start_page > end_page:
            raise IndexError(f"Start page {start_page} must be <= end page {end_page}")

        pages_text = []
        for i in range(start_page - 1, end_page):
            pages_text.append(result.pages[i].text)

        return "\n\n".join(pages_text)


class ParserError(Exception):
    """Base exception for parser errors."""
    pass


class FileFormatError(ParserError):
    """Raised when file format is not supported."""
    pass


class APIError(ParserError):
    """Raised when API communication fails."""
    pass


class TaskTimeoutError(ParserError):
    """Raised when parsing task times out."""
    pass
