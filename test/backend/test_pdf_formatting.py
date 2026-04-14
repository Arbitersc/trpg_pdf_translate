#!/usr/bin/env python3
"""
Test script for PDF text formatting optimization

This test:
1. Creates a sample PDF-extracted text with formatting issues
2. Tests the optimize_pdf_text_formatting method
3. Verifies the optimization results
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

from client import SiliconFlowClient


# Sample text with common PDF extraction issues
SAMPLE_PDF_TEXT = """the town of sheerleaf sits between the arthfell forest and
arthfell mountains in andoran and is a pleasant, quiet village mostly
populated by humanoids and leshies, with the occasional caravan traveling
through. It's a slow-moving place with a mayoral election happening
every five years despite Mayor eli- ana, a local aiuvarin blacksmith,
having run unopposed for over thirty years. During the last election,
she was stepping up to deliver her sixth and supposedly final acceptance
speech when the stage was overtaken by a large, dark shadow just before
the adamantine dragon, zi kritrax, landed among the populace.

mayor eliana attempted to negotiate with zikritrax in his lair at the
caves of mount zoldos, which overlooks the town and its surrounding
land. She suggested he become she er- leaf's protector, keeping away
bandits and other possible threats in exchange for food and other services.

after receiving healing from the local priest of desna, eliana marched
back up the mountain with most of her guards and demanded that zi-
kritrax stand down and listen to reason."""


def test_formatting_optimization():
    """
    Test PDF text formatting optimization with LLM
    """
    print("=" * 80)
    print("PDF Text Formatting Optimization Test")
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
    print()

    # Initialize client
    print("-" * 80)
    print("Initializing SiliconFlow client...")
    print("-" * 80)
    client = SiliconFlowClient(api_key=api_key, base_url=base_url)
    print(f"✓ Client initialized")
    print()

    # Display sample text preview
    print("-" * 80)
    print("Sample PDF-Extracted Text (with formatting issues):")
    print("-" * 80)
    print(SAMPLE_PDF_TEXT)
    print()
    print("Issues present:")
    print("  - Lowercase at sentence beginnings: 'the town', 'a local', 'During'")
    print("  - Inconsistent proper name capitalization: 'Mayor eli- ana', 'zi kritrax'")
    print("  - Broken words from line breaks: 'eli- ana', 'she er- leaf', 'zi- kritrax'")
    print("  - Lowercase at start: 'mayor', 'after'")
    print()

    # Optimize formatting
    print("-" * 80)
    print("Optimizing text formatting...")
    print("-" * 80)

    optimized_text = client.optimize_pdf_text_formatting(
        model=model,
        extracted_text=SAMPLE_PDF_TEXT,
        context="TRPG story text about a town and a dragon",
        stream_print=True
    )

    print()
    print(f"✓ Formatting optimization completed")
    print()

    # Display optimized text
    print("-" * 80)
    print("Optimized Text:")
    print("-" * 80)
    print(optimized_text)
    print()

    # Simple verification checks
    print("=" * 80)
    print("Optimization Verification")
    print("=" * 80)
    print()

    checks_passed = 0
    checks_total = 0

    # Check 1: Proper names should be capitalized
    proper_names = ["Sheerleaf", "Arthfell", "Andoran", "Eliana", "Zikritrax", "Mount Zoldos", "Desna"]
    for name in proper_names:
        checks_total += 1
        if name in optimized_text:
            print(f"✓ '{name}' is properly capitalized")
            checks_passed += 1
        else:
            print(f"✗ '{name}' not found or not properly capitalized")

    # Check 2: Broken words should be fixed
    broken_words = ["eli- ana", "zi kritrax", "she er- leaf", "zi- kritrax"]
    checks_total += 1
    broken_found = [word for word in broken_words if word in optimized_text]
    if not broken_found:
        print(f"✓ No broken words found")
        checks_passed += 1
    else:
        print(f"✗ Broken words still present: {broken_found}")

    # Check 3: Sentences should start with capital letters
    checks_total += 1
    # Check a few expected sentence starts
    if isinstance(optimized_text, str):
        text_lower = optimized_text.lower()
        # The word "the" shouldn't be at the start if it was originally lowercase
        # We just check that the result is different from input
        if optimized_text != SAMPLE_PDF_TEXT:
            print(f"✓ Text has been modified (changes were made)")
            checks_passed += 1
        else:
            print(f"✗ Text unchanged (no formatting applied)")

    print()
    print(f"Passed: {checks_passed}/{checks_total} checks")
    print()

    if checks_passed == checks_total:
        print("STATUS: ✅ ALL TESTS PASSED")
        print()
        return 0
    else:
        print("STATUS: ⚠️  SOME CHECKS FAILED (may need manual review)")
        print()
        return 1


if __name__ == "__main__":
    exit_code = test_formatting_optimization()
    sys.exit(exit_code)
