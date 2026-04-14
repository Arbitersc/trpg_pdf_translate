"""
MinerU API Client

Handles communication with the MinerU API for PDF parsing tasks.
"""

import time
import os
import zipfile
import io
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Load .env from both current directory and user config directory
load_dotenv()  # Load from current directory
user_env_path = Path.home() / ".trpg_pdf_translator" / ".env"
if user_env_path.exists():
    load_dotenv(dotenv_path=user_env_path, override=True)

from ..base import APIError, TaskTimeoutError


class MinerUClient:
    """
    Client for MinerU API operations.

    Handles task creation, status polling, and result downloading.
    """

    # Default configuration
    DEFAULT_API_URL = "https://mineru.net/api/v4"
    DEFAULT_MODEL_VERSION = "vlm"
    DEFAULT_TIMEOUT = 300  # seconds
    DEFAULT_POLL_INTERVAL = 5  # seconds
    MAX_RETRY_ATTEMPTS = 3

    # Error code mapping
    ERROR_CODES = {
        "A0202": "Token error - check token format or get new token",
        "A0211": "Token expired - get new API token",
        "-500": "Parameter error - check request format and Content-Type",
        "-10001": "Service error - please try again later",
        "-10002": "Invalid parameters - check request format",
        "-60001": "Failed to generate upload URL - try again later",
        "-60002": "Failed to detect file type - check file extension",
        "-60003": "File read failed - check file integrity",
        "-60004": "Empty file - upload a valid file",
        "-60005": "File size exceeds limit (max 200MB)",
        "-60006": "Too many pages (max 600 pages)",
        "-60007": "Model service unavailable - try again later",
        "-60008": "File read timeout - check URL accessibility",
        "-60009": "Task queue full - try again later",
        "-60010": "Parsing failed - try again later",
        "-60011": "Failed to access uploaded file - ensure upload completed",
        "-60012": "Task not found - check task_id",
        "-60013": "No permission to access this task",
        "-60014": "Cannot delete running task",
        "-60015": "File conversion failed - try converting manually to PDF",
        "-60016": "File format conversion failed",
        "-60017": "Max retry attempts reached - try again after model update",
        "-60018": "Daily parsing limit reached - try again tomorrow",
        "-60019": "HTML parsing quota exceeded - try again tomorrow",
        "-60020": "File split failed - try again later",
        "-60021": "Failed to read page count - try again later",
        "-60022": "Webpage read failed - network issue or rate limiting",
    }

    # Task states
    TASK_STATES = {
        "done": "Completed",
        "pending": "Queued",
        "running": "Processing",
        "failed": "Failed",
        "converting": "Converting",
        "waiting-file": "Waiting for file upload"
    }

    def __init__(
        self,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
        model_version: Optional[str] = None,
        timeout: Optional[int] = None,
        poll_interval: Optional[int] = None
    ):
        """
        Initialize MinerU client.

        Args:
            token: API token (reads from MINERU_API_TOKEN env var if not provided)
            api_url: API base URL (reads from MINERU_API_URL env var if not provided)
            model_version: Default model version (reads from MINERU_MODEL_VERSION env var)
            timeout: Default timeout in seconds (reads from MINERU_TIMEOUT env var)
            poll_interval: Default poll interval in seconds (reads from MINERU_POLL_INTERVAL env var)
        """
        self.token = token or os.getenv("MINERU_API_TOKEN")
        self.api_url = (api_url or os.getenv("MINERU_API_URL") or self.DEFAULT_API_URL).rstrip("/")
        self.model_version = model_version or os.getenv("MINERU_MODEL_VERSION", self.DEFAULT_MODEL_VERSION)
        self.timeout = timeout or int(os.getenv("MINERU_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        self.poll_interval = poll_interval or int(os.getenv("MINERU_POLL_INTERVAL", str(self.DEFAULT_POLL_INTERVAL)))

        if not self.token:
            raise ValueError("MINERU_API_TOKEN must be provided either as parameter or environment variable")

        # HTTP client for API requests
        self._client = httpx.Client(timeout=60.0)

    def _get_headers(self) -> Dict[str, str]:
        """Get default request headers."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*"
        }

    def _check_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Check API response and handle errors.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response data

        Raises:
            APIError: For API-level errors
        """
        data = response.json()

        if response.status_code != 200 or data.get("code") != 0:
            error_code = str(data.get("code", "unknown"))
            error_msg = data.get("msg", "Unknown error")

            # Get detailed error message
            detailed_msg = self.ERROR_CODES.get(error_code, error_msg)
            raise APIError(f"API Error ({error_code}): {detailed_msg}")

        return data

    def create_task_from_url(
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
        cache_tolerance: int = 900,
        callback: Optional[str] = None,
        seed: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a parsing task from a URL.

        Args:
            url: URL to the PDF file
            model_version: Model version (pipeline, vlm, MinerU-HTML)
            is_ocr: Enable OCR functionality
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code (default: ch)
            data_id: Business data ID for tracking
            page_ranges: Page range string (e.g., "1-10,15-20")
            extra_formats: Additional output formats (docx, html, latex)
            no_cache: Bypass cache
            cache_tolerance: Cache tolerance in seconds
            callback: Callback URL for async notification
            seed: Random string for callback signature

        Returns:
            Response data with task_id

        Raises:
            APIError: For API-level errors
        """
        endpoint = f"{self.api_url}/extract/task"

        data = {
            "url": url,
            "model_version": model_version or self.model_version,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language,
            "no_cache": no_cache,
            "cache_tolerance": cache_tolerance
        }

        if data_id:
            data["data_id"] = data_id
        if page_ranges:
            data["page_ranges"] = page_ranges
        if extra_formats:
            data["extra_formats"] = extra_formats
        if callback:
            data["callback"] = callback
        if seed:
            data["seed"] = seed

        response = self._client.post(endpoint, headers=self._get_headers(), json=data)
        return self._check_response(response)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status by task_id.

        Args:
            task_id: Task ID returned by create_task_from_url

        Returns:
            Task status data

        Raises:
            APIError: For API-level errors
        """
        endpoint = f"{self.api_url}/extract/task/{task_id}"
        response = self._client.get(endpoint, headers=self._get_headers())
        return self._check_response(response)

    def poll_task(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        poll_interval: Optional[int] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Poll task until completion or timeout.

        Args:
            task_id: Task ID to poll
            timeout: Maximum wait time in seconds (uses default if not specified)
            poll_interval: Poll interval in seconds (uses default if not specified)
            verbose: Print progress messages

        Returns:
            Completed task data

        Raises:
            TaskTimeoutError: If task doesn't complete within timeout
            APIError: For API-level errors
        """
        timeout = timeout or self.timeout
        poll_interval = poll_interval or self.poll_interval
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                raise TaskTimeoutError(
                    f"Task {task_id} did not complete within {timeout} seconds"
                )

            task_data = self.get_task_status(task_id)
            status = task_data["data"]

            state = status.get("state", "unknown")

            if verbose:
                if state == "running":
                    progress = status.get("extract_progress", {})
                    extracted = progress.get("extracted_pages", 0)
                    total = progress.get("total_pages", 0)
                    print(f"  Progress: {extracted}/{total} pages (elapsed: {int(elapsed)}s)")
                else:
                    state_name = self.TASK_STATES.get(state, state)
                    print(f"  Status: {state_name} (elapsed: {int(elapsed)}s)")

            if state == "done":
                return status

            if state == "failed":
                err_msg = status.get("err_msg", "Unknown error")
                raise APIError(f"Task {task_id} failed: {err_msg}")

            time.sleep(poll_interval)

    def download_result(
        self,
        zip_url: str,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Download and extract result ZIP file.

        Args:
            zip_url: URL to the result ZIP file
            output_dir: Output directory (uses temp dir if not specified)

        Returns:
            Path to the extracted directory

        Raises:
            APIError: For download/extraction errors
        """
        if output_dir is None:
            import tempfile
            output_dir = Path(tempfile.mkdtemp())

        # Download ZIP file
        response = self._client.get(zip_url)
        if response.status_code != 200:
            raise APIError(f"Failed to download result from {zip_url}")

        # Extract ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(output_dir)

        return output_dir

    def parse_from_url(
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
        timeout: Optional[int] = None,
        poll_interval: Optional[int] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Parse a PDF from URL - complete workflow.

        Args:
            url: URL to the PDF file
            model_version: Model version (pipeline, vlm, MinerU-HTML)
            is_ocr: Enable OCR functionality
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code
            data_id: Business data ID for tracking
            page_ranges: Page range string
            extra_formats: Additional output formats
            timeout: Maximum wait time in seconds
            poll_interval: Poll interval in seconds
            verbose: Print progress messages

        Returns:
            Parsed task result with full_zip_url

        Raises:
            APIError: For API-level errors
            TaskTimeoutError: If task times out
        """
        if verbose:
            print(f"Creating parsing task for: {url}")

        # Create task
        task_data = self.create_task_from_url(
            url=url,
            model_version=model_version,
            is_ocr=is_ocr,
            enable_formula=enable_formula,
            enable_table=enable_table,
            language=language,
            data_id=data_id,
            page_ranges=page_ranges,
            extra_formats=extra_formats,
            no_cache=no_cache
        )

        task_id = task_data["data"]["task_id"]
        if verbose:
            print(f"Task created: {task_id}")

        # Poll for completion
        status = self.poll_task(
            task_id=task_id,
            timeout=timeout,
            poll_interval=poll_interval,
            verbose=verbose
        )

        if verbose:
            print(f"Task completed: {task_id}")

        return status

    def get_batch_upload_urls(
        self,
        files: List[Dict[str, Any]],
        model_version: Optional[str] = None,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        extra_formats: Optional[List[str]] = None,
        no_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get upload URLs for batch file upload.

        Args:
            files: List of file descriptors with 'name' and optional 'data_id', 'is_ocr', 'page_ranges'
            model_version: Model version to use
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code
            extra_formats: Additional output formats
            no_cache: Bypass cache for results

        Returns:
            Response with batch_id and upload URLs

        Raises:
            APIError: For API-level errors
        """
        endpoint = f"{self.api_url}/file-urls/batch"

        data = {
            "files": files,
            "model_version": model_version or self.model_version,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language,
            "no_cache": no_cache
        }

        if extra_formats:
            data["extra_formats"] = extra_formats

        response = self._client.post(endpoint, headers=self._get_headers(), json=data)
        return self._check_response(response)

    def upload_file(self, upload_url: str, file_path: Path) -> bool:
        """
        Upload a file to the given URL.

        Args:
            upload_url: Presigned upload URL
            file_path: Local file path to upload

        Returns:
            True if upload was successful

        Raises:
            APIError: For upload errors
        """
        with open(file_path, "rb") as f:
            # Use PUT request with file data, with longer timeout for large files
            response = httpx.put(upload_url, content=f.read(), timeout=300.0)

        return response.status_code == 200

    def create_batch_task_from_urls(
        self,
        files: List[Dict[str, Any]],
        model_version: Optional[str] = None,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        extra_formats: Optional[List[str]] = None,
        no_cache: bool = False,
        cache_tolerance: int = 900
    ) -> Dict[str, Any]:
        """
        Create batch parsing tasks from URLs.

        Args:
            files: List of file descriptors with 'url' and optional 'data_id', 'is_ocr', 'page_ranges'
            model_version: Model version to use
            enable_formula: Enable formula recognition
            enable_table: Enable table recognition
            language: Document language code
            extra_formats: Additional output formats
            no_cache: Bypass cache
            cache_tolerance: Cache tolerance in seconds

        Returns:
            Response with batch_id

        Raises:
            APIError: For API-level errors
        """
        endpoint = f"{self.api_url}/extract/task/batch"

        data = {
            "files": files,
            "model_version": model_version or self.model_version,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language,
            "no_cache": no_cache,
            "cache_tolerance": cache_tolerance
        }

        if extra_formats:
            data["extra_formats"] = extra_formats

        response = self._client.post(endpoint, headers=self._get_headers(), json=data)
        return self._check_response(response)

    def get_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """
        Get results for a batch task.

        Args:
            batch_id: Batch ID to query

        Returns:
            Batch results with extract_result for each file

        Raises:
            APIError: For API-level errors
        """
        endpoint = f"{self.api_url}/extract-results/batch/{batch_id}"
        response = self._client.get(endpoint, headers=self._get_headers())
        return self._check_response(response)

    def poll_batch(
        self,
        batch_id: str,
        timeout: Optional[int] = None,
        poll_interval: Optional[int] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Poll batch task until all files are complete or timeout.

        Args:
            batch_id: Batch ID to poll
            timeout: Maximum wait time in seconds
            poll_interval: Poll interval in seconds
            verbose: Print progress messages

        Returns:
            Completed batch results

        Raises:
            TaskTimeoutError: If batch doesn't complete within timeout
            APIError: For API-level errors
        """
        timeout = timeout or self.timeout
        poll_interval = poll_interval or self.poll_interval
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                raise TaskTimeoutError(
                    f"Batch {batch_id} did not complete within {timeout} seconds"
                )

            batch_data = self.get_batch_results(batch_id)
            results = batch_data["data"].get("extract_result", [])

            # Check if all files are complete
            all_done = all(r.get("state") == "done" for r in results)
            any_failed = any(r.get("state") == "failed" for r in results)

            if verbose:
                completed = sum(1 for r in results if r.get("state") == "done")
                total = len(results)
                print(f"  Batch progress: {completed}/{total} files (elapsed: {int(elapsed)}s)")

            if all_done:
                return batch_data["data"]

            if any_failed:
                failed = [r for r in results if r.get("state") == "failed"]
                raise APIError(
                    f"Batch {batch_id} failed: {failed[0].get('err_msg', 'Unknown error')}"
                )

            time.sleep(poll_interval)

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
