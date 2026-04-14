#!/usr/bin/env python3
"""
Test script for proper noun extraction from TRPG documents

This test:
1. Tests the extract_proper_nouns method with sample TRPG text
2. Verifies various types of proper nouns are correctly identified
3. Checks that expected terms are included in extraction results
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


# Sample TRPG text for testing
SAMPLE_TEXT = """The town of Sheerleaf sits between the Arthfell Forest and Arthfell Mountains in Andoran and is a pleasant, quiet village mostly populated by humanoids and leshies, with the occasional caravan traveling through. It's a slow-moving place with a mayoral election happening every five years despite Mayor Eliana, a local aiuvarin blacksmith, having run unopposed for over thirty years. During the last election, she was stepping up to deliver her sixth and supposedly final acceptance speech when the stage was overtaken by a large, dark shadow just before the adamantine dragon, Zikritrax, landed among the populace. A few moments of awkward silence hung in the air before he used his pummeling breath weapon of stones to destroy the local meeting hall and demanded Sheerleaf's subservience.

Mayor Eliana attempted to negotiate with Zikritrax in his lair at the caves of Mount Zoldos, which overlooks the town and its surrounding land. She suggested he become Sheerleaf's protector, keeping away bandits and other possible threats in exchange for food and other services, as the town would be glad to have a powerful dragon as an ally. Zikritrax only laughed and swatted her out of his cave, demanding she bring back an entire herd of sheep for making him listen to her prattle.

After receiving healing from the local priest of Desna, Eliana marched back up the mountain with most of her guards and demanded that Zikritrax stand down and listen to reason. Incensed by the courage of the villagers, the dragon launched himself from the mountain and attacked Sheerleaf. He pummeled most of Sheerleaf's buildings to the ground before snatching the mayor's wife and children from their home. Zikritrax hid them well within his caves, informing Mayor Eliana that if she valued their safety, and indeed the safety of all of Sheerleaf, she'd ensure the town bowed to his whims and started following his orders."""


# Expected terms that should be extracted
EXPECTED_TERMS = {
    "places": ["Sheerleaf", "Arthfell Forest", "Arthfell Mountains", "Andoran", "Mount Zoldos"],
    "characters": ["Eliana", "Mayor Eliana", "Zikritrax"],
    "creatures": ["adamantine dragon"],
    "deities": ["Desna"],
    "races": ["humanoids", "leshies", "aiuvarin"],
}


def test_term_extraction():
    """
    Test proper noun extraction with sample TRPG text
    """
    print("=" * 80)
    print("TRPG Proper Noun Extraction Test")
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
    print("Sample Text Preview (first 300 chars):")
    print("-" * 80)
    print(SAMPLE_TEXT[:300] + "...")
    print()

    # Extract proper nouns
    print("-" * 80)
    print("Extracting proper nouns...")
    print("-" * 80)

    extracted_terms = client.extract_proper_nouns(
        model=model,
        text=SAMPLE_TEXT,
        stream_print=True
    )

    print()
    print(f"✓ Extraction completed")
    print(f"Total terms extracted: {len(extracted_terms)}")
    print()

    # Display extracted terms
    print("-" * 80)
    print("Extracted Terms:")
    print("-" * 80)
    for i, term in enumerate(extracted_terms, 1):
        print(f"  {i:2d}. {term}")
    print()

    # Verify expected terms
    all_expected = set()
    for category, terms in EXPECTED_TERMS.items():
        all_expected.update(terms)

    extracted_set = set(extracted_terms)
    missing_terms = all_expected - extracted_set

    print("=" * 80)
    print("Extraction Verification")
    print("=" * 80)
    print()

    print(f"Expected terms: {len(all_expected)}")
    print(f"Found terms: {len(extracted_set)}")
    print(f"Missing terms: {len(missing_terms)}")
    print()

    if missing_terms:
        print("Missing terms:")
        for term in missing_terms:
            print(f"  ✗ {term}")
        print()
    else:
        print("✓ All expected terms were extracted!")
        print()

    # Verify by category
    print("-" * 80)
    print("Verification by Category:")
    print("-" * 80)

    all_passed = True
    for category, expected in EXPECTED_TERMS.items():
        found = [term for term in expected if term in extracted_set]
        missing = [term for term in expected if term not in extracted_set]

        status = "✓" if not missing else "✗"
        print(f"\n{status} {category.capitalize()}:")
        print(f"    Expected: {len(expected)}, Found: {len(found)}, Missing: {len(missing)}")

        if found:
            print(f"    Found: {', '.join(found)}")
        if missing:
            print(f"    Missing: {', '.join(missing)}")
            all_passed = False

    print()
    print("=" * 80)

    # Additional extraction quality checks
    print("-" * 80)
    print("Additional Quality Checks:")
    print("-" * 80)

    # Check for common terms that should NOT be extracted
    common_terms_in_text = [
        "town", "forest", "mountains", "village", "caravan", "election",
        "stage", "meeting", "hall", "caves", "priest", "guards"
    ]

    incorrectly_extracted = [
        term for term in common_terms_in_text
        if term in extracted_set
    ]

    if incorrectly_extracted:
        print(f"✗ Common terms incorrectly extracted: {', '.join(incorrectly_extracted)}")
        all_passed = False
    else:
        print("✓ No common terms incorrectly extracted")

    # Check for duplicate extractions
    if len(extracted_terms) != len(set(extracted_terms)):
        duplicates = [term for term in extracted_terms if extracted_terms.count(term) > 1]
        print(f"✗ Duplicate terms found: {', '.join(set(duplicates))}")
        all_passed = False
    else:
        print("✓ No duplicate terms found")

    print()

    # Final result
    if all_passed and not missing_terms:
        print("STATUS: ✅ ALL TESTS PASSED")
        print()
        return 0
    else:
        print("STATUS: ❌ SOME TESTS FAILED")
        print()
        return 1


if __name__ == "__main__":
    exit_code = test_term_extraction()
    sys.exit(exit_code)
