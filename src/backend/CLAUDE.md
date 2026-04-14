# Backend Documentation

## Overview

The backend module provides the core functionality for the TRPG PDF Translator project, including:
- PDF parsing with support for multiple parser backends (currently MinerU)
- LLM integration for translation using SiliconFlow API
- End-to-end translation pipeline with proper noun extraction, glossary generation, and bilingual alignment

## Architecture

```
src/backend/
├── client.py              # SiliconFlow LLM API client
├── parser_interface.py    # PDF parser factory and interface
├── pipeline.py            # Translation pipeline orchestration
├── parsers/
│   ├── base.py           # Abstract parser base classes
│   └── mineru/           # MinerU parser implementation
│       ├── client.py     # MinerU API client
│       └── extractor.py  # MinerU PDF extractor
├── requirements.txt      # Python dependencies
└── .env.example         # Environment configuration template
```

## Core Components

### 1. SiliconFlow LLM Client (`client.py`)

**Purpose**: Provides streaming LLM API integration for translation operations.

**Key Features**:
- Streaming chat completion with real-time output
- Automatic retry with exponential backoff (max 3 retries, 60s timeout)
- Support for reasoning/chain-of-thought extraction (`enable_thinking`)
- Progressive JSON parsing with regex fallback

**Main Methods**:
- `_stream_chat_completion()`: Core streaming completion with retry logic
- `extract_proper_nouns()`: Extract TRPG-specific proper nouns from text
- `generate_glossary()`: Generate translation glossary for proper nouns (batch translation)
- `translate_text()`: Translate text with glossary support and hyperlink formatting
- `update_translation_with_glossary()`: Post-process translations for glossary consistency
- `optimize_pdf_text_formatting()`: Fix PDF extraction issues with sliding window
- `align_bilingual_text()`: Create bilingual English/Chinese output with sliding window

**Configuration** (via environment variables):
- `SILICONFLOW_API_KEY`: API authentication key
- `SILICONFLOW_BASE_URL`: API base URL (default: https://api.siliconflow.cn/v1)
- `SILICONFLOW_MODEL`: Model identifier (default: Pro/moonshotai/Kimi-K2.5)

### 2. PDF Parser Interface (`parser_interface.py`)

**Purpose**: Factory pattern for accessing different PDF parsers.

**Key Classes**:
- `ParserFactory`: Factory for creating parser instances
  - `create_parser()`: Create parser by type
  - `register_parser()`: Register new parser types
  - `get_available_parsers()`: List available parsers

**Convenience Functions**:
- `get_default_parser_config()`: Load config from environment
- `create_parser()`: Create parser with env-based configuration
- `parse_pdf()`: Parse from auto-detected source (file or URL)
- `parse_pdf_file()`: Parse local file
- `parse_pdf_url()`: Parse from URL
- `parse_pdf_with_window()`: Parse with sliding window

**Post-Processing**:
- `_remove_markdown_images()`: Remove markdown image links
- `_postprocess_result()`: Apply post-processing to ParseResult

**Configuration** (via environment variables):
- `PDF_PARSER_TYPE`: Parser type (default: mineru)
- `MINERU_API_TOKEN`: MinerU API token
- `MINERU_API_URL`: API URL (default: https://mineru.net/api/v4)
- `MINERU_MODEL_VERSION`: Model version (default: vlm)
- `MINERU_TIMEOUT`: Timeout in seconds (default: 300)
- `MINERU_POLL_INTERVAL`: Poll interval in seconds (default: 5)

### 3. PDF Parser Base (`parsers/base.py`)

**Purpose**: Abstract base classes defining the parser interface.

**Key Classes**:
- `PageResult`: Data class for single page results
  - `page_number`: Page index (1-indexed)
  - `text`: Extracted text content
  - `images`: List of image paths/descriptions
  - `tables`: Table data
  - `metadata`: Page-level metadata

- `ParseResult`: Data class for complete document results
  - `success`: Success status
  - `file_path`: Source file path or URL
  - `total_pages`: Number of pages
  - `pages`: List of PageResult objects
  - `full_text`: Concatenated text from all pages
  - `metadata`: Document-level metadata
  - `errors`: List of errors encountered

- `PDFParserBase`: Abstract parser interface
  - `parse_file(file_path)`: Parse local file (abstract)
  - `parse_url(url)`: Parse from URL (abstract)
  - `parse(source)`: Auto-detect file vs URL
  - `parse_file_with_window()`: Parse with sliding window
  - `parse_url_with_window()`: Parse URL with sliding window

**Exceptions**:
- `ParserError`: Base exception
- `FileFormatError`: Unsupported file format
- `APIError`: API communication failure
- `TaskTimeoutError`: Task timeout

### 4. MinerU Client (`parsers/mineru/client.py`)

**Purpose**: Handles MinerU API communication for PDF parsing tasks.

**Key Methods**:
- `create_task_from_url()`: Create parsing task from URL
- `get_task_status()`: Query task status
- `poll_task()`: Poll until completion or timeout
- `download_result()`: Download and extract ZIP result
- `parse_from_url()`: Complete URL-based workflow
- `get_batch_upload_urls()`: Get pre-signed upload URLs
- `upload_file()`: Upload file to pre-signed URL
- `create_batch_task_from_urls()`: Create batch task
- `get_batch_results()`: Get batch results
- `poll_batch()`: Poll batch until completion

**Error Handling**:
- Comprehensive error code mapping (`ERROR_CODES`)
- Detailed error messages for all failure scenarios
- Task states: done, pending, running, failed, converting, waiting-file

**Configuration**:
- `api_url`: API base URL
- `model_version`: Model version (pipeline, vlm, MinerU-HTML)
- `timeout`: Default timeout (300s)
- `poll_interval`: Poll interval (5s)
- `MAX_RETRY_ATTEMPTS`: 3

### 5. MinerU Extractor (`parsers/mineru/extractor.py`)

**Purpose**: PDF parser implementation using MinerU API with sliding window support.

**Key Features**:
- Both URL and local file parsing
- Sliding window parsing with page overlap for context preservation
- Automatic page splitting from full.md or individual markdown files
- Merged result handling with overlap removal

**Key Methods**:
- `parse_file()`: Parse local PDF with upload → parse → download workflow
- `parse_url()`: Parse PDF from URL
- `_parse_result_from_directory()`: Parse downloaded results
- `_create_page_windows()`: Create sliding window page ranges
- `_parse_window()`: Parse specific page range
- `_merge_window_results()`: Merge overlapping window results
- `parse_with_sliding_window()`: Parse with configurable windows
- `parse_file_with_window()`: Convenience wrapper for files
- `parse_url_with_window()`: Convenience wrapper for URLs

**Sliding Window Algorithm**:
- Configurable window size (default: 5 pages)
- Configurable overlap (default: 1 page)
- Pages are split at window boundaries
- Merge strategy skips overlapping pages while preserving continuity
- Dry-run mode available for testing window plans

### 6. Translation Pipeline (`pipeline.py`)

**Purpose**: End-to-end translation workflow orchestration.

**Key Features**:
- Proper noun extraction with TRPG-specific patterns
- Glossary generation with batch translation
- Incremental translation with sliding window
- Bilingual text alignment
- Export to multiple formats (Markdown, JSON, Parquet)

**Configuration Options** (from `__init__.py`):
- `chunk_size`: Characters per translation chunk (default: 4000)
- `overlap`: Overlap between chunks for context (default: 200)
- `window_size`: Pages per format optimization window (default: 5)
- `overlap_paragraphs`: Paragraph overlap for formatting (default: 2)

**Environment Variables**:
- `SILICONFLOW_API_KEY`: LLM API key
- `SILICONFLOW_BASE_URL`: LLM API URL
- `SILICONFLOW_MODEL`: LLM model
- `PDF_PARSER_TYPE`: Parser type
- `MINERU_API_TOKEN`: MinerU token
- `MINERU_API_URL`: MinerU API URL

## Data Flow

### PDF Parsing Flow
```
Source (File/URL)
  ↓
ParserInterface (factory)
  ↓
MinerUExtractor
  ↓
MinerUClient (API communication)
  └─→ Upload/Submit Task
  └─→ Poll for Completion
  └─→ Download Result
  └─→ Extract ZIP
  ↓
ParseResult (pages + full_text)
```

### Translation Flow
```
ParseResult (extracted text)
  ↓
Pipeline
  ├─→ Extract Proper Nouns
  ├─→ Generate Glossary
  ├─→ Optimize Formatting (if enabled)
  ├─→ Translate Text (by chunks)
  ├─→ Update with Glossary
  └─→ Align Bilingual (if enabled)
  ↓
Export (Markdown, JSON, Parquet)
```

## Dependencies

See `requirements.txt`:
- `openai>=1.0.0`: OpenAI SDK for LLM API
- `python-dotenv>=1.0.0`: Environment variable loading
- `httpx>=0.27.0`: Async HTTP client
- `pydantic>=2.0.0`: Data validation
- `pandas>=2.0.0` (optional): Data export to Parquet
- `pyarrow>=10.0.0` (optional): Parquet file format support

## Configuration

Create a `.env` file in the project root or `~/.trpg_pdf_translator/.env`:

```bash
# SiliconFlow LLM Configuration
SILICONFLOW_API_KEY=your_api_key_here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Pro/moonshotai/Kimi-K2.5

# PDF Parser Configuration
PDF_PARSER_TYPE=mineru

# MinerU Configuration
MINERU_API_TOKEN=your_mineru_token_here
MINERU_API_URL=https://mineru.net/api/v4
MINERU_MODEL_VERSION=vlm
MINERU_TIMEOUT=300
MINERU_POLL_INTERVAL=5
```

## Usage Examples

### Parse a PDF
```python
from backend.parser_interface import parse_pdf

# Parse with default settings
result = parse_pdf("document.pdf", remove_images=True, verbose=True)
print(result.full_text)
```

### Parse with sliding windows
```python
from backend.parser_interface import parse_pdf_with_window

result = parse_pdf_with_window(
    "large_document.pdf",
    window_size=10,
    overlap_pages=2,
    verbose=True
)
```

### Translate with pipeline
```python
from backend.pipeline import TRPGTranslationPipeline

# Initialize pipeline
pipeline = TRPGTranslationPipeline()

# Parse and translate
result = pipeline.process_document(
    "document.pdf",
    target_language="中文",
    export_bilingual=True,
    optimize_formatting=True
)

# Export results
result.export_markdown("output.md")
result.export_json("output.json")
```

## Key Design Patterns

1. **Factory Pattern**: `ParserFactory` for parser instantiation
2. **Abstract Base Class**: `PDFParserBase` for parser interface
3. **Sliding Window**: Used in translation, formatting optimization, and PDF parsing for handling large texts
4. **Retry with Exponential Backoff**: Used in LLM API calls for resilience
5. **Streaming**: Real-time output from LLM for better UX
6. **Data Classes**: Structured data representation with `@dataclass`
