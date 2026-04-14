# MinerU PDF Parser

This module provides a parser implementation using the [MinerU](https://mineru.net) API for extracting text content from PDF documents.

## Overview

MinerU is a document parsing service that uses advanced models (VLM/Pipeline) to extract structured content from PDFs including:
- Text extraction with OCR support
- Formula recognition
- Table extraction
- Multiple output formats (Markdown, JSON, DOCX, HTML, LaTeX)

## Features

- **URL-based parsing**: Parse PDFs directly from public URLs
- **Batch upload**: Upload local files for parsing
- **Asynchronous processing**: Submit tasks and poll for results
- **Multiple formats**: Get results in Markdown, JSON, DOCX, HTML, or LaTeX
- **OCR support**: Enable OCR for scanned documents
- **Page range selection**: Parse specific pages only

## API Reference

For detailed API documentation including all endpoints, parameters, and error codes, see the main documentation file:
`	doc/MinerU.md`

## Quick Start

```python
from backend.parsers.mineru.client import MinerUClient
from backend.parsers.mineru.extractor import MinerUExtractor

# Initialize the client
client = MinerUClient(
    token="your_api_token_here",
    model_version="vlm"
)

# Or use environment variables:
# MINERU_API_TOKEN=your_token_here
# MINERU_API_URL=https://mineru.net/api/v4

client = MinerUClient()

# Parse a PDF from URL
result = client.parse_from_url(
    url="https://example.com/document.pdf",
    data_id="doc_001"
)

# Wait for completion and get results
task_id = result["data"]["task_id"]
completed_task = client.poll_task(task_id, timeout=300)

# Download and parse the result
extractor = MinerUExtractor(client)
parse_result = extractor.parse_url(url="https://example.com/document.pdf")
```

## Configuration

Set the following environment variables in `src/backend/.env`:

```env
# MinerU API Configuration
MINERU_API_TOKEN=your_token_here
MINERU_API_URL=https://mineru.net/api/v4
MINERU_MODEL_VERSION=vlm
MINERU_TIMEOUT=300
MINERU_POLL_INTERVAL=5
```

## Model Versions

- **pipeline**: Traditional OCR-based pipeline (default, good for simple documents)
- **vlm**: Vision Language Model (better for complex layouts, tables, formulas)
- **MinerU-HTML**: Specialized model for HTML files

## Usage Examples

### Parse from URL

```python
from backend.parsers.mineru.extractor import MinerUExtractor

extractor = MinerUExtractor()
result = extractor.parse_url(
    url="https://example.com/document.pdf",
    page_ranges="1-10",  # Only parse pages 1-10
    is_ocr=False         # Disable OCR (faster for digital PDFs)
)

print(result.full_text)
```

### Parse Local File

```python
from pathlib import Path
from backend.parsers.mineru.extractor import MinerUExtractor

extractor = MinerUExtractor()
result = extractor.parse_file(
    file_path=Path("/path/to/document.pdf"),
    data_id="my_document"
)

print(f"Parsed {result.total_pages} pages")
for page in result.pages:
    print(f"Page {page.page_number}: {len(page.text)} characters")
```

### Batch Process Multiple Files

```python
from pathlib import Path
from backend.parsers.mineru.extractor import MinerUExtractor

extractor = MinerUExtractor()

files = list(Path("/path/to/pdf/files").glob("*.pdf"))

results = []
for file_path in files:
    result = extractor.parse_file(file_path)
    results.append(result)
    print(f"✓ Parsed {file_path.name}: {result.total_pages} pages")
```

## API Endpoints

### Single File Parsing

- **POST** `/api/v4/extract/task` - Create parsing task from URL
- **GET** `/api/v4/extract/task/{task_id}` - Get task status and results

### Batch File Upload

- **POST** `/api/v4/file-urls/batch` - Get upload URLs for local files

### Batch URL Processing

- **POST** `/api/v4/extract/task/batch` - Create batch parsing tasks from URLs
- **GET** `/api/v4/extract-results/batch/{batch_id}` - Get batch results

## Error Handling

```python
from backend.parsers.mineru.client import MinerUClient
from backend.parsers.mineru.base import APIError, TaskTimeoutError

client = MinerUClient()

try:
    result = client.parse_from_url(url="invalid_url")
except APIError as e:
    print(f"API Error: {e}")
except TaskTimeoutError:
    print("Task timed out. Try increasing the timeout value.")
```

## Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| A0202 | Token error | Check token format, ensure Bearer prefix |
| A0211 | Token expired | Get new API token from MinerU |
| -60003 | File read failed | Check file integrity |
| -60005 | File too large | File must be under 200MB |
| -60006 | Too many pages | File must be under 600 pages |
| -60012 | Task not found | Verify task_id is correct |
| -60018 | Daily limit reached | Try again tomorrow |

## Limitations

- File size: Maximum 200MB
- Page count: Maximum 600 pages
- Daily quota: 2000 priority pages/day (additional pages have lower priority)
- Upload URLs expire after 24 hours

## Output Format

Parsing results are provided as a ZIP file containing:
- `*/md/*.md` - Markdown text extraction
- `*/json/*.json` - Structured JSON data
- Optional: DOCX, HTML, LaTeX formats (if requested via `extra_formats` parameter)

## References

- Main API Documentation: `doc/MinerU.md`
- MinerU Website: https://mineru.net
- MinerU GitHub: https://github.com/opendatalab/MinerU
