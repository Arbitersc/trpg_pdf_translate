# Frontend CLI Documentation

## Overview

The Frontend CLI (`src/frontend/cli/`) provides an interactive command-line interface for the TRPG PDF Translator. It manages user interactions, workflow orchestration, configuration, and communicates directly with backend modules through Python imports.

---

## Directory Structure

```
src/frontend/cli/
├── __init__.py
├── main.py          # CLI entry point
├── interactive.py   # Interactive menu system
├── config.py        # Configuration management
├── utils.py         # Utility functions
└── workflow.py      # Workflow orchestration & backend integration
```

---

## Module Descriptions

### main.py

**Purpose**: CLI entry point and top-level control flow

**Key Functions**:
- `main()` - Entry point that determines mode (interactive/command-line)
- `run_interactive_mode()` - Runs the interactive menu loop
- `run_command_line_mode()` - Placeholder for future command-line mode

**Flow**:
```
main()
  ├─ Interactive mode (default)
  │   └─ main() → show_main_menu() → run_selected_workflow()
  └─ Command-line mode (planned)
```

---

### interactive.py

**Purpose**: Interactive menu system and user interface

**Key Features**:

1. **Main Menu** (`show_main_menu()`):
   - 1. 📄 PDF解析 - Extract PDF text content
   - 2. 🌐 翻译管道 - Complete translation pipeline
   - 3. 📚 术语表管理 - Extract and manage proper nouns
   - 4. 🔄 双语对齐 - Align bilingual text
   - 5. ⚙️ 配置管理 - Configure API and parameters
   - 6. ℹ️ 帮助信息 - Help information
   - 7. 🚪 退出 - Exit

2. **Workflow Functions**:
   - `run_pdf_parse_workflow()` - PDF parsing with options
   - `run_translation_workflow()` - Full translation pipeline
   - `run_glossary_workflow()` - Glossary management submenu
   - `run_alignment_workflow()` - Bilingual text alignment
   - `run_config_workflow()` - Configuration management

3. **Glossary Operations** (`run_glossary_workflow()`):
   - Extract proper nouns from PDF
   - Generate translation glossary
   - Update existing glossary
   - View glossary content
   - Export glossary to various formats (JSON, Markdown, TSV)

4. **Configuration Operations** (`run_config_workflow()`):
   - Set API keys (SiliconFlow, OpenAI, Ollama)
   - Configure model parameters
   - Configure parser options (MinerU)
   - View/edit configuration files
   - Reset, import, export configurations

**Execution Pattern**:
```python
if choice == "1":
    run_pdf_parse_workflow()
elif choice == "2":
    run_translation_workflow()
# ... etc
```

---

### config.py

**Purpose**: Centralized configuration management

**Key Class**: `ConfigManager`

**Configuration Storage**:
- `~/.trpg_pdf_translator/config.json` - Main configuration
- `~/.trpg_pdf_translator/.env` - Environment variables (API keys)

**Default Configuration Structure**:
```json
{
  "api": {
    "provider": "siliconflow",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Pro/moonshotai/Kimi-K2.5",
    "timeout": 300
  },
  "parser": {
    "type": "mineru",
    "timeout": 300,
    "poll_interval": 5
  },
  "translation": {
    "default_source_language": "English",
    "default_target_language": "中文",
    "window_size": 30,
    "overlap_ratio": 0.5
  },
  "output": {
    "default_format": "markdown",
    "create_backup": true,
    "timestamp_files": true
  }
}
```

**Key Methods**:
- `get(key, default)` - Get nested config value with dot notation
- `set(key, value)` - Set nested config value with auto-save
- `set_api_key(provider, key)` - Securely store API keys in .env
- `load_config()` - Load and merge with defaults
- `save_config()` - Persist to config.json
- `validate_config()` - Validate current config
- `import_config(path, merge)` - Import from JSON/.env
- `export_config(path)` - Export to JSON/.env
- `show_config_status()` - Display current status

---

### utils.py

**Purpose**: Shared utility functions used across modules

**Categories**:

1. **Display Functions**:
   - `clear_screen()` - Clear terminal
   - `print_banner()` - Show ASCII art banner
   - `print_header(title)` - Formatted header
   - `print_progress(current/total, desc)` - Progress bar
   - `print_success/error/warning/info(message)` - Styled messages

2. **User Input Functions**:
   - `get_user_choice(prompt, valid_choices)` - Validated choice input
   - `get_yes_no(prompt, default)` - Boolean input
   - `get_file/path(prompt, must_exist)` - Validated file/directory input

3. **Format Functions**:
   - `format_file_size(bytes)` - Human-readable size
   - `format_time_duration(seconds)` - Human-readable time
   - `sanitize_filename(filename)` - Safe filename for filesystem

4. **System Functions**:
   - `validate_api_key_format(key)` - Basic API key validation
   - `create_backup_file(filepath)` - Create timestamped backup
   - `check_disk_space(path, required_mb)` - Disk space check
   - `confirm_action(prompt, dangerous)` - Action confirmation
   - `wait_with_spinner(duration, message)` - Animated spinner

---

### workflow.py

**Purpose**: Workflow orchestration and backend integration

**Architecture Pattern**: Direct Python imports (NOT HTTP API calls)

```
Frontend CLI  ──┐
               │  Python Module Import
               │
Backend       <--┘
  - parser_interface.py
  - client.py (SiliconFlowClient)
  - pipeline.py
```

**Key Components**:

1. **WorkflowManager Class** (`src/frontend/cli/workflow.py:58-247`):
   ```python
   class WorkflowManager:
       def add_step(step_func, description, active_form)  # Add workflow step
       def set_context/get_context(key)                   # Store/share data
       def run() -> bool                                  # Execute all steps
   ```

2. **Backend Integration Functions**:

   | Function | Backend Module | Purpose |
   |----------|---------------|---------|
   | `parse_pdf()` | `parser_interface` | Extract text from PDF |
   | `parse_pdf_with_window()` | `parser_interface` | Sliding window parsing |
   | `SiliconFlowClient()` | `client.py` | LLM API client |
   | `split_text_by_strategy()` | `pipeline.py` | Text chunking |

3. **Workflow Functions**:

   - `validate_pdf_source(source)` - Validate file/URL
   - `parse_pdf_with_options(source, options)` - Parse with options
   - `parse_pdf_for_translation(source)` - Parse for translation
   - `extract_proper_nouns_from_pdf(text, api_key, model)` - LLM extraction
   - `generate_translation_glossary(config, nouns)` - Create glossary
   - `split_text_into_chunks(text, window_size)` - Text segmentation
   - `translate_text_with_glossary(text, glossary, ...)` - Translate with glossary
   - `post_process_translation(text, glossary)` - Post-processing
   - `save_result_to_file(content, path, format)` - File output

4. **Workflow Creators**:

   - `create_pdf_parse_workflow(source, options)` - PDF parsing workflow
   - `create_translation_workflow(source, config, options)` - Full translation

**Translation Pipeline Example**:
```python
1. parse_pdf_for_translation()  # Extract text
2. extract_proper_nouns_from_pdf()  # Identify proper nouns
3. generate_translation_glossary()  # Create term translations
4. translate_text_with_glossary()  # Translate with glossary
5. post_process_translation()  # Finalize
6. save_result_to_file()  # Export
```

---

## Data Flow Diagram

```
User Input
    ↓
[interactive.py] Menu System
    ↓
[workflow.py] WorkflowManager
    ├─ Context Storage (set/get_context)
    └─ Step Functions
        ↓
Direct Python Module Imports
    ↓
[backend/)
    ├─ parser_interface.py → parse_pdf()
    ├─ client.py → SiliconFlowClient
    └─ pipeline.py → split_text_by_strategy()
        ↓
Result
    ↓
[utils.py] Formatted Output
    ↓
User Display
```

---

## Configuration Sharing

**Shared Configuration Files** (backend & frontend):
```bash
~/.trpg_pdf_translator/
├── config.json    # Structured settings
└── .env           # API keys & secrets
```

**Environment Variables**:
- `SILICONFLOW_API_KEY` - Translation API key
- `SILICONFLOW_BASE_URL` - API endpoint
- `SILICONFLOW_MODEL` - LLM model name
- `MINERU_API_TOKEN` - PDF parser API token
- `MINERU_API_URL` - Parser API URL

---

## Error Handling Strategy

1. **Import Fallback** (`workflow.py:26-56`):
   ```python
   try:
       from src.backend.parser_interface import parse_pdf
   except ImportError:
       from backend.parser_interface import parse_pdf
   ```

2. **Availability Flags**:
   - `_parser_available` - Check if parser interface is accessible
   - `_siliconflow_available` - Check if LLM client is accessible
   - `_pipeline_available` - Check if pipeline functions are accessible

3. **Workflow Step Errors** (`WorkflowManager.run()`):
   - Try-catch each step
   - Offer retry/skip/abort options
   - Continue with remaining steps if skipped

---

## Key Design Patterns

1. **Module-Based Architecture**: No HTTP APIs, direct Python imports
2. **Context-Based Workflow**: `WorkflowManager` uses context dict to pass data between steps
3. **Configuration Hierarchy**: Defaults → User config → Runtime overrides
4. **Graceful Degradation**: Check module availability; warn if missing
5. **Interactive First UI**: Menu-driven interface for user-friendliness

---

## Entry Point Command

```bash
python -m src.frontend.cli.main
```

Or direct:
```bash
python src/frontend/cli/main.py
```

## Core Files

| File | Description |
|------|-------------|

| cli/config.py | Configuration Manager for TRPG PDF Translator CLI This module handles configuration management including API keys, model settings, and parser options. |
| cli/interactive.py | Interactive CLI Interface for TRPG PDF Translator This module provides the interactive menu system for the CLI. |
| cli/main.py | Defines 3 function(s) |
| cli/workflow.py | Workflow Manager for TRPG PDF Translator CLI This module provides workflow management for multi-step operations. |
