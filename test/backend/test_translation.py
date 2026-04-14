#!/usr/bin/env python3
"""
Test script for TRPG translation pipeline with LLM model using streaming
Tests the following functionalities:
- Automatic proper noun extraction
- Automatic glossary generation
- Text translation using LLM with 50% overlapping sliding windows
- Post-translation updates based on glossary
- Streaming requests to avoid timeout on long outputs
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add src directory to path
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(src_dir / "backend"))

# Load environment variables from .env using config_loader
try:
    from backend.config_loader import reload_environment_config
    env_path = src_dir / "backend" / ".env"
    reload_environment_config(env_path)
except ImportError:
    print("WARNING: config_loader not found, falling back to load_dotenv")
    env_path = src_dir / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)

from backend.pipeline import TranslationPipeline


def test_translation_pipeline():
    """
    Test the complete translation pipeline:
    1. Extract proper nouns from document
    2. Generate glossary/translation table
    3. Translate text using LLM with 50% overlapping sliding windows (streaming)
    4. Update translation based on glossary
    """
    print("=" * 80)
    print("TRPG Translation Pipeline Test (Streaming Mode)")
    print("=" * 80)
    print()

    # Check environment variables
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    model = os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")

    if not api_key:
        print("ERROR: SILICONFLOW_API_KEY not found in environment variables.")
        print("Please set it in src/backend/.env file.")
        sys.exit(1)

    print(f"Configuration:")
    print(f"  - API URL: {base_url}")
    print(f"  - Model: {model}")
    print(f"  - API Key: {api_key[:10]}..." if len(api_key) > 10 else f"  - API Key: {api_key}")
    print(f"  - Request Mode: Streaming (avoids timeout on long outputs)")
    print(f"  - Sliding Window Overlap: 50%")
    print(f"  - Thinking Mode: Disabled (faster response)")
    print()

    # Test document path
    test_doc_path = Path(__file__).parent.parent / "doc" / "trpg_pf2.md"

    if not test_doc_path.exists():
        print(f"ERROR: Test document not found at {test_doc_path}")
        sys.exit(1)

    with open(test_doc_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    print(f"Loaded test document: {test_doc_path}")
    print(f"Document length: {len(original_text)} characters")
    print()
    print(f"Preview (first 200 chars):")
    print(f"  {original_text[:200]}...")
    print()

    # Initialize pipeline
    print("-" * 80)
    print("Initializing translation pipeline...")
    print("-" * 80)
    pipeline = TranslationPipeline(
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    print(f"Pipeline initialized with model: {pipeline.model}")
    print()

    # Test with the first portion of the document
    test_text = original_text[:3000]
    print(f"Testing with {len(test_text)} characters (first {len(test_text)} of document)")
    print()

    # ========================================
    # Step 1: Extract proper nouns
    # ========================================
    print("-" * 80)
    print("Step 1: Extracting proper nouns from document...")
    print("-" * 80)
    proper_nouns = pipeline.extract_proper_nouns_from_file(
        test_text,
        context="Pathfinder War of Immortals - TRPG rulebook",
        stream_print=True  # Enable streaming print output
    )
    print(f"✓ Found {len(proper_nouns)} proper nouns")
    print()
    print("First 15 proper nouns:")
    for i, noun in enumerate(proper_nouns[:15], 1):
        print(f"  {i:2d}. {noun}")
    if len(proper_nouns) > 15:
        print(f"  ... and {len(proper_nouns) - 15} more")
    print()

    # ========================================
    # Step 2: Generate glossary
    # ========================================
    print("-" * 80)
    print("Step 2: Generating glossary/translation table...")
    print("-" * 80)
    glossary = pipeline.generate_glossary_from_nouns(
        proper_nouns,
        target_language="中文",
        context="Pathfinder War of Immortals - TRPG rulebook"
    )
    print(f"✓ Generated {len(glossary)} glossary entries")
    print()
    print("Glossary (English → 中文):")
    for i, (orig, trans) in enumerate(list(glossary.items())[:15], 1):
        print(f"  {i:2d}. {orig:30s} → {trans}")
    if len(glossary) > 15:
        print(f"  ... and {len(glossary) - 15} more")
    print()

    # ========================================
    # Step 3: Translate text with sliding window (streaming)
    # ========================================
    print("-" * 80)
    print("Step 3: Translating text using LLM with 50% overlapping sliding windows...")
    print("(Streaming enabled - no timeout on long outputs)")
    print("-" * 80)
    result = pipeline.translate_document(
        test_text,
        source_language="English",
        target_language="中文",
        context="Pathfinder War of Immortals - TRPG rulebook",
        auto_extract_nouns=False,  # Already extracted above
        existing_glossary=glossary,
        use_sliding_window=True,    # Enable sliding window
        window_strategy="paragraph", # Split by paragraphs
        window_size=3,               # 3 paragraphs per window
        overlap_ratio=0.5,           # 50% overlap
        stream_print=True            # Enable streaming print output
    )
    print("✓ Translation completed")
    print()
    print("Translation details:")
    print(f"  - Source language: {result['source_language']}")
    print(f"  - Target language: {result['target_language']}")
    print(f"  - Model: {result['model']}")
    print(f"  - Sliding window: {'Enabled' if result['use_sliding_window'] else 'Disabled'}")
    print(f"  - Window strategy: {result.get('window_strategy', 'N/A')}")
    print(f"  - Number of windows: {result.get('num_windows', 'N/A')}")
    print(f"  - Window size: {result.get('window_size', 'N/A')} paragraphs")
    print(f"  - Overlap ratio: {result.get('overlap_ratio', 'N/A')}")
    print()

    if result.get("translation_errors"):
        print("⚠ Translation warnings:")
        for error in result["translation_errors"]:
            print(f"  - {error}")
        print()

    # ========================================
    # Step 4: Display results
    # ========================================
    print("-" * 80)
    print("Translation Result:")
    print("-" * 80)
    print(result.get("updated_translation", result.get("translated_text", "")))
    print()

    # ========================================
    # Step 5: Export results
    # ========================================
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("-" * 80)
    print("Step 5: Exporting results...")
    print("-" * 80)

    # Export markdown
    md_path = output_dir / "translation_test.md"
    pipeline.export_output(result, "markdown", str(md_path))
    print(f"✓ Saved markdown: {md_path}")

    # Export JSON
    json_path = output_dir / "translation_test.json"
    pipeline.export_output(result, "json", str(json_path))
    print(f"✓ Saved JSON: {json_path}")

    # Export bilingual
    bilingual_path = output_dir / "translation_bilingual.md"
    pipeline.export_output(result, "bilingual", str(bilingual_path))
    print(f"✓ Saved bilingual: {bilingual_path}")

    # Export glossary separately
    glossary_path = output_dir / "glossary.txt"
    with open(glossary_path, "w", encoding="utf-8") as f:
        f.write("译名表 (Glossary)\n")
        f.write("=" * 50 + "\n\n")
        for orig, trans in sorted(glossary.items()):
            f.write(f"{orig:40s} → {trans}\n")
    print(f"✓ Saved glossary: {glossary_path}")
    print()

    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)


def test_full_document_translation():
    """
    Test translating the full document with auto noun extraction and sliding window
    """
    print("\n" + "=" * 80)
    print("Full Document Translation Test (Auto Noun Extraction + Sliding Window)")
    print("=" * 80)
    print()

    # Load environment variables
    env_path = src_dir / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Test document path
    test_doc_path = Path(__file__).parent.parent / "doc" / "trpg_pf2.md"

    if not test_doc_path.exists():
        print(f"ERROR: Test document not found at {test_doc_path}")
        sys.exit(1)

    with open(test_doc_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    # Initialize pipeline
    model = os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")
    print(f"Testing with model: {model}")
    print(f"Document length: {len(original_text)} characters")
    print()

    pipeline = TranslationPipeline(model=model)

    # Translate with auto noun extraction and sliding window
    print("Translating with automatic noun extraction and sliding window enabled...")
    result = pipeline.translate_document(
        original_text,
        source_language="English",
        target_language="中文",
        context="Pathfinder War of Immortals - TRPG rulebook",
        auto_extract_nouns=True,
        use_sliding_window=True,
        window_strategy="paragraph",
        window_size=3,
        overlap_ratio=0.5,
        stream_print=True  # Enable streaming print output
    )
    print("✓ Translation completed")
    print()

    # Extract statistics
    proper_nouns = result.get("proper_nouns", [])
    glossary = result.get("glossary", {})

    print("Statistics:")
    print(f"  - Proper nouns found: {len(proper_nouns)}")
    print(f"  - Glossary entries: {len(glossary)}")
    print(f"  - Number of translation windows: {result.get('num_windows', 'N/A')}")
    print()

    # Export results
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    full_md_path = output_dir / "full_translation.md"
    pipeline.export_output(result, "markdown", str(full_md_path))
    print(f"✓ Saved full translation: {full_md_path}")

    full_bilingual_path = output_dir / "full_bilingual.md"
    pipeline.export_output(result, "bilingual", str(full_bilingual_path))
    print(f"✓ Saved full bilingual: {full_bilingual_path}")
    print()

    print("=" * 80)
    print("Full document test completed!")
    print("=" * 80)


def test_proper_noun_extraction():
    """
    Test proper noun extraction only using streaming
    """
    print("\n" + "=" * 80)
    print("Proper Noun Extraction Test (Streaming Mode)")
    print("=" * 80)
    print()

    # Load environment variables
    env_path = src_dir / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Test document path
    test_doc_path = Path(__file__).parent.parent / "doc" / "trpg_pf2.md"

    if not test_doc_path.exists():
        print(f"ERROR: Test document not found at {test_doc_path}")
        sys.exit(1)

    with open(test_doc_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    # Initialize pipeline
    model = os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")
    pipeline = TranslationPipeline(model=model)

    print(f"Model: {model}")
    print(f"Request mode: Streaming (avoids timeout on long outputs)")
    print(f"Document length: {len(original_text)} characters")
    print()

    # Extract proper nouns
    print(f"Extracting proper nouns from full document ({len(original_text)} characters)...")
    proper_nouns = pipeline.extract_proper_nouns_from_file(
        original_text,
        context="Pathfinder War of Immortals - TRPG rulebook",
        stream_print=True  # Enable streaming print output
    )
    print(f"✓ Found {len(proper_nouns)} proper nouns")
    print()
    print("All proper nouns:")
    for i, noun in enumerate(proper_nouns, 1):
        print(f"  {i:2d}. {noun}")
    print()

    print("=" * 80)
    print("Proper noun extraction test completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Run proper noun extraction test
    test_proper_noun_extraction()

    # Run basic pipeline test with sliding window
    test_translation_pipeline()

    # Uncomment to run full document test (may take longer)
    # test_full_document_translation()
