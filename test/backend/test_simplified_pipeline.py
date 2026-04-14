#!/usr/bin/env python3
"""
Test script for the new translate_pdf_to_files method

This test demonstrates the simplified workflow:
1. Input: PDF file path
2. Output: Directory path
3. Complete pipeline automatically runs and exports all files
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add src/backend directory to path
backend_dir = Path(__file__).parent.parent.parent / "src" / "backend"
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(backend_dir))

# Load environment variables from .env using config_loader
try:
    from backend.config_loader import reload_environment_config
    env_path = backend_dir / ".env"
    reload_environment_config(env_path)
except ImportError:
    print("WARNING: config_loader not found, falling back to load_dotenv")
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)

from pipeline import UnifiedTranslationPipeline


def test_translate_pdf_to_files():
    """
    Test the simplified translate_pdf_to_files method
    """
    print("=" * 80)
    print("Testing translate_pdf_to_files Method")
    print("=" * 80)
    print()

    # Check environment variables
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    model = os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")
    parser_type = os.getenv("PDF_PARSER_TYPE", "mineru")

    if not api_key:
        print("ERROR: SILICONFLOW_API_KEY not found in environment variables.")
        print("Please set it in src/backend/.env file.")
        sys.exit(1)

    print(f"Configuration:")
    print(f"  - API URL: {base_url}")
    print(f"  - Model: {model}")
    print(f"  - Parser Type: {parser_type}")
    print(f"  - API Key: {api_key[:10]}..." if len(api_key) > 10 else f"  - API Key: {api_key}")
    print(f"  - Window Size: 30 paragraphs")
    print(f"  - Overlap Ratio: 50%")
    print(f"  - Hyperlink Format: Enabled")
    print()

    # Input paths
    # The test directory structure: test/backend/ is where this script runs
    # The PDF is at test/doc/
    pdf_path = Path(__file__).parent / ".." / "doc" / "trpg_m20.pdf"
    output_dir = Path(__file__).parent / ".." / "doc" / "output" / "m20"

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found at {pdf_path}")
        sys.exit(1)

    print(f"Input: {pdf_path}")
    print(f"Output: {output_dir}")
    print()

    # Initialize pipeline
    print("-" * 80)
    print("Initializing pipeline...")
    print("-" * 80)
    pipeline = UnifiedTranslationPipeline(
        api_key=api_key,
        base_url=base_url,
        model=model,
        parser_type=parser_type
    )
    print(f"Pipeline initialized")
    print()

    # Run the complete pipeline
    try:
        output_files = pipeline.translate_pdf_to_files(
            pdf_path=str(pdf_path),
            output_dir=str(output_dir),
            source_language="English",
            target_language="中文",
            context="Mutants & Masterminds TRPG document",
            auto_extract_nouns=True,
            window_size=30,
            overlap_ratio=0.5,
            stream_print=True,
            use_hyperlink_format=True,
            optimize_formatting=True,               # Optimize PDF formatting
        )

        print()
        print("=" * 80)
        print("Test completed successfully!")
        print("=" * 80)
        print()
        print("Generated files:")
        for file_type, file_path in output_files.items():
            if type(file_path) == str and os.path.exists(file_path):
                file_size = Path(file_path).stat().st_size
                print(f"  {file_type:15s} -> {file_path} ({file_size:,} bytes)")

        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print("Test failed with error:")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_translate_pdf_to_files()
    sys.exit(exit_code)
