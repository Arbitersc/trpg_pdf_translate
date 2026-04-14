#!/usr/bin/env python3
"""
Test script for translating Pathfinder 2nd Edition PDF using existing glossary

This test:
1. Loads existing glossary from pf2_glossary.parquet
2. Parses PDF using parser_interface
3. Translates text with 30-paragraph sliding windows using the existing glossary
4. Detects glossary terms in text chunks before translation
5. Formats proper nouns as markdown hyperlinks: [Translation](Original)
6. Export final translated result to test/doc/output/pf2/
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


from pipeline import UnifiedTranslationPipeline
try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas is required to load parquet glossary files")
    print("Please install it with: pip install pandas pyarrow")
    sys.exit(1)


def load_pf2_glossary(glossary_path: str) -> dict:
    """
    Load Pathfinder 2nd Edition glossary from parquet file

    Args:
        glossary_path: Path to the parquet glossary file

    Returns:
        Dictionary mapping original terms to translations
    """
    try:
        df = pd.read_parquet(glossary_path)
        # Filter out any rows with None values
        df = df.dropna()
        return dict(zip(df["original"], df["translation"]))
    except Exception as e:
        print(f"ERROR: Failed to load glossary from {glossary_path}: {e}")
        return {}


def test_pf2_translation_with_glossary():
    """
    Test PF2 PDF translation using existing glossary:

    1. Parse PDF file
    2. Load existing PF2 glossary
    3. Translate with 30-paragraph windows using the loaded glossary
    4. Detect glossary terms in each window
    5. Format proper nouns as markdown hyperlinks
    6. Export results
    """
    print("=" * 80)
    print("Pathfinder 2nd Edition PDF Translation with Existing Glossary")
    print("=" * 80)
    print()

    # Load environment variables from .env using config_loader
    env_path = backend_dir / ".env"
    print(env_path, env_path.exists())

    # Import config_loader to use reload_environment_config
    try:
        from backend.config_loader import reload_environment_config
    except ImportError:
        print("WARNING: config_loader not found, falling back to load_dotenv")
        from dotenv import load_dotenv
        if env_path.exists():
            load_dotenv(env_path)
    else:
        # Use reload_environment_config to ensure correct configuration is loaded
        reload_environment_config(env_path)

    print("Loaded model:", os.getenv("SILICONFLOW_MODEL", "Not found"))

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
    print(f"  - Auto Extract Nouns: Disabled (using existing glossary)")
    print()

    # Test PDF and glossary paths
    test_pdf_path = Path(__file__).parent.parent / "doc" / "PZO14004E.pdf"
    glossary_path = Path(__file__).parent.parent.parent / "doc" / "glossary" / "pf2_glossary.parquet"
    output_dir = Path(__file__).parent.parent / "doc" / "output" / "pf2"

    if not test_pdf_path.exists():
        print(f"ERROR: Test PDF not found at {test_pdf_path}")
        sys.exit(1)

    if not glossary_path.exists():
        print(f"ERROR: Glossary not found at {glossary_path}")
        sys.exit(1)

    print(f"Test PDF: {test_pdf_path}")
    print(f"Glossary File: {glossary_path}")
    print(f"Output Directory: {output_dir}")
    print()

    # Load existing glossary
    print("-" * 80)
    print("Loading existing glossary...")
    print("-" * 80)
    pf2_glossary = load_pf2_glossary(str(glossary_path))
    print(f"✓ Loaded {len(pf2_glossary)} glossary entries")
    print()

    # Display glossary sample
    print("Glossary Sample (first 20 entries):")
    for i, (orig, trans) in enumerate(list(pf2_glossary.items())[:20], 1):
        print(f"  {i:2d}. {orig:30s} → {trans}")
    if len(pf2_glossary) > 20:
        print(f"  ... and {len(pf2_glossary) - 20} more")
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

    # Translate PDF with unified pipeline using existing glossary
    print("=" * 80)
    print("Starting PDF Translation Pipeline")
    print("=" * 80)
    print()

    result = pipeline.translate_document_with_pdf(
        pdf_path=str(test_pdf_path),
        source_language="English",
        target_language="中文",
        context="Pathfinder 2nd Edition Core Rulebook",
        auto_extract_nouns=True,               # Disable auto-extraction, use existing glossary
        existing_glossary=pf2_glossary,         # Use the loaded PF2 glossary
        window_size=30,                          # 30 paragraphs per window as requested
        overlap_ratio=0.5,                       # 50% overlap
        stream_print=True,                       # Enable streaming print
        use_hyperlink_format=True,               # Format as [Translation](Original)
        output_dir=str(output_dir),              # Export to output directory
        optimize_formatting=True,               # Optimize PDF formatting
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
    print(f"Glossary Entries Used: {len(result.get('glossary', {}))}")
    print(f"Translation Windows: {result.get('num_windows', 'N/A')}")
    print(f"Detected Terms in Text: {len(result.get('all_detected_terms', []))}")
    print()

    if result.get("translation_errors"):
        print("Translation Warnings:")
        for error in result["translation_errors"]:
            print(f"  - {error}")
        print()

    # Display detected terms sample
    detected_terms = result.get('all_detected_terms', [])
    glossary = result.get('glossary', {})
    if detected_terms:
        print("Detected Terms in Text Sample (first 20):")
        for i, term in enumerate(detected_terms[:20], 1):
            trans = glossary.get(term, term)
            print(f"  {i:2d}. {term:30s} → {trans}")
        if len(detected_terms) > 20:
            print(f"  ... and {len(detected_terms) - 20} more")
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

    # Export results (will be done automatically by output_dir parameter, but we can also export explicitly)
    print("-" * 80)
    print("Exporting additional results...")
    print("-" * 80)

    # Export detected terms
    detected_path = output_dir / "detected_terms.txt"
    with open(detected_path, "w", encoding="utf-8") as f:
        f.write("检测到的术语 (Detected Terms in Text)\\n")
        f.write("=" * 50 + "\\n\\n")
        for term in sorted(detected_terms):
            trans = glossary.get(term, term)
            f.write(f"{term:40s} → {trans}\\n")
    print(f"✓ Saved detected terms: {detected_path}")
    print()

    # Display output files
    output_files = result.get('output_files', {})

    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    print(f"Output directory: {output_dir}")

    print()
    print("Generated files:")
    for file_type, file_path in output_files.items():
        print(f"  - {Path(file_path).name} ({file_type})")
    if detected_path:
        print(f"  - {detected_path.name} (Detected terms in text)")


if __name__ == "__main__":
    test_pf2_translation_with_glossary()
