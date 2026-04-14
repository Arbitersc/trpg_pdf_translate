#!/usr/bin/env python3
"""
Test script for Unified Translation Pipeline with PDF parsing

This test demonstrates the unified workflow:
1. Parse PDF using parser_interface
2. Extract proper nouns automatically
3. Generate glossary/translation table
4. Translate text with 30-paragraph sliding windows
5. Detect glossary terms in text chunks before translation
6. Format proper nouns as markdown hyperlinks: [Translation](Original)
7. Export final translated result
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


def test_unified_pdf_translation():
    """
    Test the unified PDF translation pipeline:

    1. Parse PDF file
    2. Extract proper nouns
    3. Generate glossary
    4. Translate with 30-paragraph windows
    5. Detect glossary terms in each window
    6. Format proper nouns as markdown hyperlinks
    7. Export results
    """
    print("=" * 80)
    print("Unified TRPG PDF Translation Pipeline Test")
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
    print(f"  - Sliding Window Size: 30 paragraphs")
    print(f"  - Glossary Detection: Enabled")
    print(f"  - Hyperlink Format: Enabled ([Translation](Original))")
    print()

    # Test PDF path
    test_pdf_path = Path(__file__).parent.parent / "doc" / "trpg_pf2.pdf"

    if not test_pdf_path.exists():
        print(f"ERROR: Test PDF not found at {test_pdf_path}")
        sys.exit(1)

    print(f"Test PDF: {test_pdf_path}")
    print()

    # Initialize unified pipeline
    print("-" * 80)
    print("Initializing unified translation pipeline...")
    print("-" * 80)
    pipeline = UnifiedTranslationPipeline(
        api_key=api_key,
        base_url=base_url,
        model=model,
        parser_type=parser_type
    )
    print(f"Pipeline initialized with model: {pipeline.model}")
    print(f"Parser type: {pipeline.parser_type}")
    print()

    # Translate PDF with unified pipeline
    print("=" * 80)
    print("Starting PDF Translation Pipeline")
    print("=" * 80)
    print()

    result = pipeline.translate_document_with_pdf(
        pdf_path=str(test_pdf_path),
        source_language="English",
        target_language="中文",
        context="Pathfinder TRPG document",
        auto_extract_nouns=True,
        window_size=30,                      # 30 paragraphs per window as requested
        overlap_ratio=0.5,                   # 50% overlap
        stream_print=True,                   # Enable streaming print
        use_hyperlink_format=True            # Format as [Translation](Original)
    )

    # Display results summary
    print()
    print("=" * 80)
    print("Translation Summary")
    print("=" * 80)
    print(f"PDF: {result.get('pdf_path', 'N/A')}")
    print(f"Total Pages: {result.get('total_pages', 'N/A')}")
    print(f"Characters Parsed: {result.get('parse_result', {}).get('full_text', '').__len__()}")
    print(f"Proper Nouns Found: {len(result.get('proper_nouns', []))}")
    print(f"Glossary Entries: {len(result.get('glossary', {}))}")
    print(f"Translation Windows: {result.get('num_windows', 'N/A')}")
    print(f"Detected Terms in Text: {len(result.get('all_detected_terms', []))}")
    print()

    if result.get("translation_errors"):
        print("Translation Warnings:")
        for error in result["translation_errors"]:
            print(f"  - {error}")
        print()

    # Display sample of glossary
    print("Glossary Sample (first 20 entries):")
    glossary = result.get('glossary', {})
    for i, (orig, trans) in enumerate(list(glossary.items())[:20], 1):
        print(f"  {i:2d}. {orig:30s} → {trans}")
    if len(glossary) > 20:
        print(f"  ... and {len(glossary) - 20} more")
    print()

    # Display detected terms sample
    detected_terms = result.get('all_detected_terms', [])
    if detected_terms:
        print("Detected Terms in Text Sample (first 10):")
        for i, term in enumerate(detected_terms[:10], 1):
            trans = glossary.get(term, term)
            print(f"  {i:2d}. {term:30s} → {trans}")
        if len(detected_terms) > 10:
            print(f"  ... and {len(detected_terms) - 10} more")
        print()

    # Display translation preview
    print("-" * 80)
    print("Translation Preview (first 500 chars):")
    print("-" * 80)
    translation = result.get("updated_translation", "")
    print(translation[:500])
    if len(translation) > 500:
        print("...")
    print()

    # Export results
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("-" * 80)
    print("Exporting results...")
    print("-" * 80)

    # Export markdown
    md_path = output_dir / "unified_translation.md"
    pipeline.export_output(result, "markdown", str(md_path))
    print(f"✓ Saved markdown: {md_path}")

    # Export JSON
    json_path = output_dir / "unified_translation.json"
    pipeline.export_output(result, "json", str(json_path))
    print(f"✓ Saved JSON: {json_path}")

    # Export bilingual
    bilingual_path = output_dir / "unified_bilingual.md"
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

    # Export detected terms
    detected_path = output_dir / "detected_terms.txt"
    with open(detected_path, "w", encoding="utf-8") as f:
        f.write("检测到的术语 (Detected Terms in Text)\n")
        f.write("=" * 50 + "\n\n")
        for term in sorted(detected_terms):
            trans = glossary.get(term, term)
            f.write(f"{term:40s} → {trans}\n")
    print(f"✓ Saved detected terms: {detected_path}")
    print()

    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    print(f"Output directory: {output_dir}")
    print()
    print("Generated files:")
    print(f"  - {md_path.name} (Main translation with metadata)")
    print(f"  - {json_path.name} (Full data in JSON format)")
    print(f"  - {bilingual_path.name} (Bilingual comparison)")
    print(f"  - {glossary_path.name} (Glossary/translation table)")
    print(f"  - {detected_path.name} (Detected terms in text)")


if __name__ == "__main__":
    test_unified_pdf_translation()
