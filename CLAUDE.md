# CLAUDE.md

## Project Overview

TRPG PDF Translator - A project for translating tabletop role-playing game (TRPG) PDFs and text documents using large language models. The project includes both a translation pipeline and a PDF online reader.

## Planned Architecture (Phase 1)

### Backend (Python + Flask)
- PDF parsing API interface for document text extraction
- Universal LLM API configuration supporting OpenAI, Ollama, and other major platforms
- Intelligent translation workflow:
  - Automatic extraction of proper nouns from documents
  - Automatic generation of glossary/translation tables
  - Text translation using LLMs
  - Post-translation updates based on glossary
  - Export results in mono-lingual or bilingual formats
  - Export to Markdown, PDF, and other formats

### Frontend (Vue + React + Vite + PDF.js)
- PDF online reader with frontend-backend separation architecture

## How To Work: Task Execution Plan

For every development task:

1. **Analyze existing code** - Review the current codebase structure and understand relevant components
2. **Document task plan** - Write task information and modification plan to `.claude/task.md`
3. **Implement changes** - Modify or write code step by step according to the modification plan
4. **Run tests** - Execute user-specified test items. If not specified, create corresponding test items in the `test/` directory and execute them

## Project Structure

| Directory | Description | Contents |
|-----------|-------------|----------|
| doc/ | Documentation and test data | 1 subdirectories |
| src/ | Src directory | 2 subdirectories |
| test/ | Test files and test data | 3 subdirectories |

## Notes

- ALL test file must put in the `test/` directory

## Core Files

| File | Description |
|------|-------------|

| test/test_bilingual_alignment.py | Defines 1 function(s) |
