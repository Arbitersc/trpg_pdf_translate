## src/ Directory Structure

| Directory | Description | Contents |
|-----------|-------------|----------|
| backend/ | Backend API and services | pipeline module, Package initialization, config_loader module; Python dependencies; Environment configuration template; 1 subdirectories |
| frontend/ | Frontend UI components | Package initialization; Environment configuration template; 1 subdirectories |

## Notes

Both backend and frontend directories are currently empty and awaiting implementation.

## Core Files

| File | Description |
|------|-------------|

| backend/client.py | SiliconFlow API Client for LLM operations with streaming support. |
| backend/pipeline.py | Translation Pipeline for TRPG Documents Handles end-to-end translation workflow including proper noun extraction, glossary generation, translation, and post-translation updates. |
