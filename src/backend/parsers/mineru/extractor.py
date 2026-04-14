"""
MinerU PDF Extractor

Implements PDF text extraction using the MinerU API.
Supports sliding window-based parsing with overlap for context preservation.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
import tempfile

from .client import MinerUClient
from ..base import PDFParserBase, ParseResult, PageResult, APIError, TaskTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MinerUExtractor(PDFParserBase):
    """
    PDF parser implementation using MinerU API.

    Supports both URL-based and local file parsing.
    """

    def __init__(
        self,
        client: Optional[MinerUClient] = None,
        **kwargs
    ):
        """
        Initialize MinerU extractor.

        Args:
            client: Optional MinerUClient instance (creates new one if not provided)
            **kwargs: Additional configuration options passed to client
        """
        super().__init__(**kwargs)

        if client:
            self.client = client
        else:
            # Filter out non-client parameters
            client_kwargs = {k: v for k, v in kwargs.items()
                           if k not in ['verbose', 'dry_run', 'force_total_pages',
                                      'window_size', 'overlap_pages', 'is_url']}
            self.client = MinerUClient(**client_kwargs)

        # Store configuration
        self.model_version = self.client.model_version
        self.timeout = self.client.timeout

    def _parse_result_from_directory(
        self,
        result_dir: Path,
        file_path: Union[str, Path]
    ) -> ParseResult:
        """
        Parse results from extracted directory.

        Args:
            result_dir: Directory containing extracted ZIP content
            file_path: Original file path or URL

        Returns:
            ParseResult with extracted content
        """
        errors = []

        # Find markdown files (typically in */md/ directory)
        md_files = list(result_dir.glob("**/*.md"))

        # Find JSON files for structured data
        json_files = list(result_dir.glob("**/*.json"))

        if not md_files:
            errors.append("No markdown files found in result")
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=errors
            )

        # Parse structure from JSON if available
        structure_data = {}
        if json_files:
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        # Check if data is a valid dictionary
                        if isinstance(json_data, dict):
                            structure_data.update(json_data)
                        elif isinstance(json_data, list):
                            # Handle list-based JSON structures
                            # MinerU may return a list of page data
                            if json_data:
                                for idx, item in enumerate(json_data):
                                    if isinstance(item, dict):
                                        # Use index as key if appropriate
                                        structure_data[f"page_{idx + 1}"] = item
                except Exception as e:
                    errors.append(f"Failed to parse JSON {json_file}: {e}")

        # Check if there's a single "full.md" file (monolithic output)
        full_md_file = next((f for f in md_files if f.stem == "full" and "md" in str(f.parent)), None)

        # Extract pages from markdown files
        pages = []
        total_text = ""

        if full_md_file:
            # Single full.md file - treat as one page or try to split by page markers
            logger.info(f"Found single full.md file at: {full_md_file}")

            with open(full_md_file, 'r', encoding='utf-8') as f:
                text = f.read()

            # Try to detect if this has page markers (e.g., "--- Page N ---" patterns)
            page_pattern = r'(?:^|\n)---\s*Page\s+(\d+)\s*---'

            page_splits = list(re.finditer(page_pattern, text, re.MULTILINE))

            if page_splits:
                # Split by detected page markers
                last_end = 0
                for i, match in enumerate(page_splits):
                    page_num = int(match.group(1))

                    # Get text for this page
                    if i + 1 < len(page_splits):
                        page_text = text[match.start():page_splits[i + 1].start()].strip()
                    else:
                        page_text = text[match.start():].strip()

                    pages.append(PageResult(
                        page_number=page_num,
                        text=page_text,
                        images=[],
                        tables=[],
                        metadata={"source_file": str(full_md_file.relative_to(result_dir))}
                    ))

                # Fix overlapping at boundaries
                for i in range(1, len(pages)):
                    pages[i].text = pages[i].text[pages[i].text.find('\n') + 1:]

            else:
                # No page markers detected, treat as single page
                pages.append(PageResult(
                    page_number=1,
                    text=text,
                    images=structure_data.get("images", []),
                    tables=structure_data.get("tables", []),
                    metadata={
                        "source_file": str(full_md_file.relative_to(result_dir)),
                        "full_document": True
                    }
                ))

            total_text = "\n\n".join([p.text for p in pages])
        else:
            # Multiple markdown files - process individually
            pages = []
            total_text = ""

            # Sort markdown files to ensure correct order
        # MinerU typically names files as 0.md, 1.md, 2.md, etc. in md/ directory
        # or uses page numbers directly
        def sort_key(md_path):
            # Try to extract numeric prefix from filename
            name = md_path.stem
            # Handle paths like "md/0.md" -> extract "0"
            match = re.search(r'(\d+)', name)
            if match:
                return int(match.group(1))
            # Fallback to alphabetical sort
            return name

        for md_file in sorted(md_files, key=sort_key):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    text = f.read()

                # Try to extract page number from filename
                # Files are usually named like "0.md", "1.md", "page_1.md" or "1-page.md"
                page_match = re.search(r'(\d+)', md_file.stem)
                page_number = int(page_match.group(1)) + 1 if page_match else len(pages) + 1

                # Extract metadata for this page
                page_metadata = {}
                md_file_name = md_file.name
                if md_file_name in structure_data:
                    page_metadata = structure_data[md_file_name]

                # Add file path to metadata for reference
                page_metadata["source_file"] = str(md_file.relative_to(result_dir))

                pages.append(PageResult(
                    page_number=page_number,
                    text=text,
                    images=page_metadata.get("images", []),
                    tables=page_metadata.get("tables", []),
                    metadata=page_metadata
                ))

                total_text += text + "\n\n"

            except Exception as e:
                errors.append(f"Failed to read markdown file {md_file}: {e}")

        # Create parse result
        return ParseResult(
            success=len(pages) > 0,
            file_path=file_path,
            total_pages=len(pages),
            pages=pages,
            full_text=total_text.strip(),
            metadata={
                "extractor": "mineru",
                "model_version": self.model_version,
                "result_dir": str(result_dir)
            },
            errors=errors
        )

    def parse_file(
        self,
        file_path: Union[str, Path],
        model_version: Optional[str] = None,
        is_ocr: bool = False,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        data_id: Optional[str] = None,
        page_ranges: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
        no_cache: bool = False,
        verbose: bool = False
    ) -> ParseResult:
        """
        Parse a local PDF file using MinerU.

        This method:
        1. Gets upload URL from MinerU
        2. Uploads the file
        3. Polls for parsing completion
        4. Downloads and extracts results

        Args:
            file_path: Path to the local PDF file
            model_version: Model version (pipeline, vlm, MinerU-HTML)
            is_ocr: Enable OCR functionality
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code
            data_id: Business data ID for tracking
            page_ranges: Page range string (e.g., "1-10,15-20")
            extra_formats: Additional output formats
            verbose: Print progress messages

        Returns:
            ParseResult with extracted content

        Raises:
            APIError: For API-level errors
            TaskTimeoutError: If task times out
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if verbose:
            print(f"Parsing local file: {file_path}")
            print(f"File size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")

        # Check file size (MinerU limit is 200MB)
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        if file_size_mb > 200:
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=[f"File too large ({file_size_mb:.2f} MB), MinerU limit is 200MB"]
            )

        # Get upload URL
        files_batch = [{
            "name": file_path.name,
            "data_id": data_id or file_path.stem
        }]

        batch_data = self.client.get_batch_upload_urls(
            files=files_batch,
            model_version=model_version or self.model_version,
            enable_formula=enable_formula,
            enable_table=enable_table,
            language=language,
            extra_formats=extra_formats,
            no_cache=no_cache
        )

        batch_id = batch_data["data"]["batch_id"]
        upload_urls = batch_data["data"]["file_urls"]

        if verbose:
            print(f"Upload URLs received: {batch_id}")

        # Upload file
        if not upload_urls:
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=["No upload URLs received from MinerU"]
            )

        if verbose:
            print(f"Uploading file...")

        upload_success = self.client.upload_file(upload_urls[0], file_path)

        if not upload_success:
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=["Failed to upload file to MinerU"]
            )

        if verbose:
            print(f"File uploaded, waiting for parsing...")

        # Poll for batch completion
        try:
            batch_result = self.client.poll_batch(
                batch_id=batch_id,
                timeout=self.timeout,
                verbose=verbose
            )
        except Exception as e:
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=[f"Batch parsing failed: {str(e)}"]
            )

        # Get result from batch
        extract_results = batch_result.get("extract_result", [])

        if not extract_results:
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=["No extraction results in batch response"]
            )

        result = extract_results[0]

        if result.get("state") != "done":
            err_msg = result.get("err_msg", "Unknown error")
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=[f"Parse task failed: {err_msg}"]
            )

        # Download and extract result
        zip_url = result.get("full_zip_url")

        if not zip_url:
            return ParseResult(
                success=False,
                file_path=file_path,
                total_pages=0,
                pages=[],
                full_text="",
                errors=["No download URL in result"]
            )

        if verbose:
            print(f"Downloading results from: {zip_url}")

        # Download to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                result_dir = self.client.download_result(zip_url, Path(temp_dir))

                # Parse results from directory
                parsed_data = self._parse_result_from_directory(result_dir, file_path)

                if verbose:
                    print(f"✓ Parsed {parsed_data.total_pages} pages")

                return parsed_data

            except Exception as e:
                return ParseResult(
                    success=False,
                    file_path=file_path,
                    total_pages=0,
                    pages=[],
                    full_text="",
                    errors=[f"Failed to download/extract result: {str(e)}"]
                )

    def parse_url(
        self,
        url: str,
        model_version: Optional[str] = None,
        is_ocr: bool = False,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        data_id: Optional[str] = None,
        page_ranges: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
        no_cache: bool = False,
        verbose: bool = False
    ) -> ParseResult:
        """
        Parse a PDF from URL using MinerU.

        Args:
            url: URL to the PDF file
            model_version: Model version (pipeline, vlm, MinerU-HTML)
            is_ocr: Enable OCR functionality
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code
            data_id: Business data ID for tracking
            page_ranges: Page range string (e.g., "1-10,15-20")
            extra_formats: Additional output formats
            verbose: Print progress messages

        Returns:
            ParseResult with extracted content
        """
        if verbose:
            print(f"Parsing URL: {url}")

        try:
            # Submit task and poll for completion
            status = self.client.parse_from_url(
                url=url,
                model_version=model_version or self.model_version,
                is_ocr=is_ocr,
                enable_formula=enable_formula,
                enable_table=enable_table,
                language=language,
                data_id=data_id,
                page_ranges=page_ranges,
                extra_formats=extra_formats,
                no_cache=no_cache,
                timeout=self.timeout,
                verbose=verbose
            )
        except Exception as e:
            return ParseResult(
                success=False,
                file_path=url,
                total_pages=0,
                pages=[],
                full_text="",
                errors=[f"Parse task failed: {str(e)}"]
            )

        if status.get("state") != "done":
            err_msg = status.get("err_msg", "Unknown error")
            return ParseResult(
                success=False,
                file_path=url,
                total_pages=0,
                pages=[],
                full_text="",
                errors=[f"Parse task failed: {err_msg}"]
            )

        # Download and extract result
        zip_url = status.get("full_zip_url")

        if not zip_url:
            return ParseResult(
                success=False,
                file_path=url,
                total_pages=0,
                pages=[],
                full_text="",
                errors=["No download URL in result"]
            )

        if verbose:
            print(f"Downloading results from: {zip_url}")

        # Download to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                result_dir = self.client.download_result(zip_url, Path(temp_dir))

                # Parse results from directory
                parsed_data = self._parse_result_from_directory(result_dir, url)

                if verbose:
                    print(f"✓ Parsed {parsed_data.total_pages} pages")

                return parsed_data

            except Exception as e:
                return ParseResult(
                    success=False,
                    file_path=url,
                    total_pages=0,
                    pages=[],
                    full_text="",
                    errors=[f"Failed to download/extract result: {str(e)}"]
                )

    def _create_page_windows(
        self,
        total_pages: int,
        window_size: int = 5,
        overlap_pages: int = 1
    ) -> List[Tuple[int, int]]:
        """
        Create sliding windows of page ranges with overlap.

        For example, with total_pages=12, window_size=5, overlap_pages=1:
        - Window 1: 1-5
        - Window 2: 5-10  (overlaps window 1 at page 5)
        - Window 3: 10-12

        Args:
            total_pages: Total number of pages
            window_size: Number of pages per window
            overlap_pages: Number of overlapping pages between windows

        Returns:
            List of (start_page, end_page) tuples (1-indexed)
        """
        if total_pages == 0:
            return []

        if window_size <= 0:
            window_size = 5

        # If overlap is same as window_size or larger, set to window_size - 1
        if overlap_pages >= window_size:
            overlap_pages = window_size - 1

        windows = []
        start_page = 1

        while start_page <= total_pages:
            end_page = min(start_page + window_size - 1, total_pages)

            # Check if this window reaches the end of the document
            if end_page == total_pages:
                # This window contains the last page, no need to create more windows
                windows.append((start_page, end_page))
                break

            # Ensure we have at least the overlap pages in the next window
            if start_page > 1:
                # Check if this window would overlap with the previous one
                prev_start = windows[-1][0]
                prev_end = windows[-1][1]
                # For proper overlap, this window should start before prev_end
                if start_page >= prev_end:
                    # Create smaller overlapping window
                    start_page = prev_end  # Start where previous ended

            windows.append((start_page, end_page))

            # Move to next window step (window size minus overlap)
            step_size = window_size - overlap_pages
            if step_size <= 0:
                step_size = 1

            start_page = end_page - overlap_pages + 1

        logger.info(f"Created {len(windows)} windows for {total_pages} pages "
                    f"(window_size={window_size}, overlap={overlap_pages})")

        return windows

    def _parse_window(
        self,
        source: Union[str, Path],
        start_page: int,
        end_page: int,
        is_url: bool = False,
        **kwargs
    ) -> ParseResult:
        """
        Parse a specific window of pages.

        Args:
            source: File path or URL
            start_page: Starting page number (1-indexed, inclusive)
            end_page: Ending page number (1-indexed, inclusive)
            is_url: Whether source is a URL
            **kwargs: Additional parsing options

        Returns:
            ParseResult for the window
        """
        page_ranges = f"{start_page}-{end_page}"
        verbose = kwargs.get("verbose", False)

        if verbose:
            logger.info(f"Parsing window: pages {page_ranges}")

        try:
            if is_url:
                result = self.parse_url(
                    url=str(source),
                    page_ranges=page_ranges,
                    **kwargs
                )
            else:
                result = self.parse_file(
                    file_path=Path(source),
                    page_ranges=page_ranges,
                    **kwargs
                )
            return result
        except Exception as e:
            return ParseResult(
                success=False,
                file_path=source,
                total_pages=0,
                pages=[],
                full_text="",
                errors=[f"Failed to parse window {page_ranges}: {str(e)}"]
            )

    def _merge_window_results(
        self,
        window_results: List[ParseResult],
        total_pages: int,
        window_size: int = 5,
        overlap_pages: int = 1
    ) -> ParseResult:
        """
        Merge results from overlapping windows.

        The merge strategy:
        1. For the first window, keep all pages
        2. For subsequent windows, skip the overlapping pages
        3. Handle page numbering to maintain continuity

        Args:
            window_results: List of ParseResult from each window
            total_pages: Expected total number of pages
            window_size: Window size used for parsing
            overlap_pages: Number of overlapping pages

        Returns:
            Merged ParseResult
        """
        if not window_results:
            return ParseResult(
                success=False,
                file_path="multiple_windows",
                total_pages=0,
                pages=[],
                full_text="",
                errors=["No window results to merge"]
            )

        # Collect all pages and track which ones to keep
        all_pages = []
        all_errors = []
        merged_pages = []
        merged_full_text = ""

        # Track last page number we've added
        last_added_page = 0

        for window_idx, result in enumerate(window_results):
            if not result.success:
                all_errors.extend(result.errors)
                logger.warning(f"Window {window_idx + 1} failed, skipping")
                continue

            for page in result.pages:
                original_page_num = page.page_number

                # For the first window, always include all pages
                if window_idx == 0:
                    merged_pages.append(page)
                    last_added_page = max(last_added_page, original_page_num)
                else:
                    # For subsequent windows, skip pages we've already added
                    # The first 'overlap_pages' pages should overlap with previous window
                    if original_page_num > last_added_page:
                        # This is a new page, add it
                        merged_pages.append(page)
                        last_added_page = original_page_num
                    elif original_page_num == last_added_page:
                        # This is the boundary page, adjust its page number
                        if not any(p.page_number == original_page_num for p in merged_pages):
                            merged_pages.append(page)
                            last_added_page = original_page_num
                    # Skip overlapping pages that were already added

        # Reorder pages by original page number
        merged_pages.sort(key=lambda p: p.page_number)

        # Renumber pages to be sequential
        for idx, page in enumerate(merged_pages):
            # Store original page number in metadata
            if "original_page_number" not in page.metadata:
                page.metadata["original_page_number"] = page.page_number
            page.page_number = idx + 1

        # Construct full text
        merged_full_text = "\n\n".join([p.text for p in merged_pages])

        # Determine final file path from source
        file_path = window_results[0].file_path if window_results else "unknown"

        # Check if we got all expected pages
        success = len(merged_pages) > 0
        if len(merged_pages) < total_pages:
            all_errors.append(
                f"Expected {total_pages} pages but got {len(merged_pages)} after merging"
            )
            success = False

        logger.info(f"Merged {len(window_results)} windows into {len(merged_pages)} pages")

        return ParseResult(
            success=success,
            file_path=file_path,
            total_pages=len(merged_pages),
            pages=merged_pages,
            full_text=merged_full_text,
            metadata={
                "extractor": "mineru",
                "model_version": self.model_version,
                "window_size": window_size,
                "overlap_pages": overlap_pages,
                "num_windows": len(window_results),
                "original_total_pages": total_pages,
                "parsed_windows": len([r for r in window_results if r.success])
            },
            errors=all_errors
        )

    def parse_with_sliding_window(
        self,
        source: Union[str, Path],
        is_url: bool = False,
        window_size: int = 5,
        overlap_pages: int = 1,
        dry_run: bool = False,
        force_total_pages: Optional[int] = None,
        **kwargs
    ) -> ParseResult:
        """
        Parse a PDF using sliding window approach with overlapping pages.

        This method is useful for large PDFs or when you want to ensure context
        is preserved across page boundaries for better parsing quality.

        Args:
            source: File path or URL
            is_url: Whether source is a URL
            window_size: Number of pages per window (default: 5)
            overlap_pages: Number of overlapping pages between windows (default: 1)
            dry_run: If True, only show window plan without parsing
            force_total_pages: Force total page count (useful for URL parsing)
            **kwargs: Additional parsing options passed to parse_file/parse_url

        Returns:
            Merged ParseResult from all windows

        Example:
            # Parse local file with default 5-page windows
            result = extractor.parse_with_sliding_window("/path/to/document.pdf")

            # Parse with custom window settings
            result = extractor.parse_with_sliding_window(
                "/path/to/document.pdf",
                window_size=10,
                overlap_pages=2,
                verbose=True
            )

            # Parse URL with sliding windows
            result = extractor.parse_with_sliding_window(
                "https://example.com/document.pdf",
                is_url=True,
                window_size=5,
                verbose=True
            )
        """
        verbose = kwargs.get("verbose", False)

        logger.info(f"Starting sliding window parse: window_size={window_size}, "
                   f"overlap_pages={overlap_pages}")

        # Step 1: Determine total number of pages
        # For URLs or when forced, use the provided total_pages
        if force_total_pages:
            total_pages = force_total_pages
        else:
            # Parse the first page to get total page count
            if verbose:
                logger.info("Determining total page count...")
            first_result = self._parse_window(source, 1, 1, is_url=is_url, **kwargs)
            if not first_result.success:
                return ParseResult(
                    success=False,
                    file_path=source,
                    total_pages=0,
                    pages=[],
                    full_text="",
                    errors=["Failed to parse first page to determine page count"]
                )
            # MinerU may not provide total page count in result
            # Use the result's total_pages or the number of pages found
            total_pages = first_result.total_pages or len(first_result.pages)
            if total_pages == 0:
                return ParseResult(
                    success=False,
                    file_path=source,
                    total_pages=0,
                    pages=[],
                    full_text="",
                    errors=["Could not determine total page count"]
                )

        if verbose:
            logger.info(f"Total pages: {total_pages}")

        # Step 2: Create windows
        windows = self._create_page_windows(total_pages, window_size, overlap_pages)

        if not windows:
            return ParseResult(
                success=False,
                file_path=source,
                total_pages=0,
                pages=[],
                full_text="",
                errors=["Failed to create page windows"]
            )

        if verbose:
            logger.info(f"Window plan:")
            for idx, (start, end) in enumerate(windows):
                logger.info(f"  Window {idx + 1}: Pages {start}-{end} ({end - start + 1} pages)")

        # Dry run: just show the plan
        if dry_run:
            return ParseResult(
                success=True,
                file_path=source,
                total_pages=total_pages,
                pages=[],
                full_text="",  # No actual text in dry run
                metadata={
                    "extractor": "mineru_dry_run",
                    "window_size": window_size,
                    "overlap_pages": overlap_pages,
                    "num_windows": len(windows),
                    "windows": windows,
                    "dry_run": True
                },
                errors=[]
            )

        # Step 3: Parse each window
        window_results = []
        parse_errors = []

        for idx, (start, end) in enumerate(windows):
            if verbose:
                logger.info(f"\n--- Parsing Window {idx + 1}/{len(windows)} (Pages {start}-{end}) ---")

            window_result = self._parse_window(
                source, start, end, is_url=is_url, **kwargs
            )
            window_results.append(window_result)

            if not window_result.success:
                parse_errors.extend(window_result.errors)
                logger.warning(f"Window {idx + 1} failed: {window_result.errors}")

        # Step 4: Merge results
        if verbose:
            logger.info("\n--- Merging window results ---")

        merged_result = self._merge_window_results(
            window_results,
            total_pages,
            window_size,
            overlap_pages
        )

        # Add any parse errors
        merged_result.errors.extend(parse_errors)

        if verbose:
            if merged_result.success:
                logger.info(f"✓ Successfully merged {len(merged_result.pages)} pages")
            else:
                logger.warning(f"⚠ Merge completed with {len(merged_result.errors)} errors")

        return merged_result

    def parse_file_with_window(
        self,
        file_path: Union[str, Path],
        window_size: int = 5,
        overlap_pages: int = 1,
        **kwargs
    ) -> ParseResult:
        """
        Parse a local PDF file using sliding window approach.

        Convenience wrapper for parse_with_sliding_window with is_url=False.

        Args:
            file_path: Path to the local PDF file
            window_size: Number of pages per window (default: 5)
            overlap_pages: Number of overlapping pages (default: 1)
            **kwargs: Additional parsing options

        Returns:
            Merged ParseResult from all windows
        """
        return self.parse_with_sliding_window(
            file_path,
            is_url=False,
            window_size=window_size,
            overlap_pages=overlap_pages,
            **kwargs
        )

    def parse_url_with_window(
        self,
        url: str,
        window_size: int = 5,
        overlap_pages: int = 1,
        force_total_pages: Optional[int] = None,
        **kwargs
    ) -> ParseResult:
        """
        Parse a PDF from URL using sliding window approach.

        Convenience wrapper for parse_with_sliding_window with is_url=True.

        Args:
            url: URL to the PDF file
            window_size: Number of pages per window (default: 5)
            overlap_pages: Number of overlapping pages (default: 1)
            force_total_pages: Force total page count (optional)
            **kwargs: Additional parsing options

        Returns:
            Merged ParseResult from all windows
        """
        return self.parse_with_sliding_window(
            url,
            is_url=True,
            window_size=window_size,
            overlap_pages=overlap_pages,
            force_total_pages=force_total_pages,
            **kwargs
        )
