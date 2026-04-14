#!/usr/bin/env python3
"""
Test script for PDF text formatting optimization with long text
Tests sliding window merging functionality
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


# Long text that will be split into multiple windows
LONG_PDF_TEXT = """
the town of sheerleaf sits between the arthfell forest and
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
kritrax stand down and listen to reason. Incensed by the courage of the
villagers, the dragon launched himself from the mountain and attacked
sheerleaf. He pummeled most of she erleaf's buildings to the ground
before snatching the mayor's wife and children from their home.

zi kritrax hid them well within his caves, informing Mayor eli- ana that
if she valued their safety, and indeed the safety of all sheerleaf,
she'd ensure the town bowed to his whims and started following his orders.

the village council convened an emergency meeting to discuss the dragon's
demands. councilmember thorin, a dwarven smith and close friend of the
mayor, argued that they should seek help from the pathfinder society.
this suggestion was met with mixed reactions from the other council members,
some of whom feared the society might bring more trouble than the dragon
itself.

meanwhile, in the forests east of sheerleaf, a group of adventurers
had made camp. They had heard rumors of a dragon's lair in the mountains
and were investigating the situation unknown to the villagers. among them
was aasimar paladin valerius, who sensed something was amiss in the
region the moment they entered the town's territory.

valerius urged his companions to proceed cautiously, noting that the
unnatural silence of the forests suggested something powerful had
recently passed through. His elven companion, lyrian Shadowleaf,
drew her bow and scanned the treeline with keen eyes.

they soon encountered a group of refugees fleeing from sheerleaf. an
elderly human couple, Tomas and mara garrick, told them of the dragon's
attack and the mayor's captivity. they had managed to escape through a
hidden tunnel beneath the town's inn that dated back to the age of
lost omens.

with this information, valerius and his companions made their way toward
sheerleaf, determined to confront zi kritrax and free the hostages. as
they approached the town, they could see smoke rising from the ruined
buildings and hear the distant roar of the dragon echoing through the
mountains.
"""


def test_long_text_formatting():
    """
    Test PDF text formatting optimization with long text (sliding window)
    """
    print("=" * 80)
    print("PDF Text Formatting Optimization Test - Long Text (Sliding Window)")
    print("=" * 80)
    print()

    # Check environment variables
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    model = os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")

    if not api_key:
        print("ERROR: SILICONFLOW_API_KEY not found in environment variables.")
        sys.exit(1)

    print(f"Configuration:")
    print(f"  - API URL: {base_url}")
    print(f"  - Model: {model}")
    print(f"  - Text length: {len(LONG_PDF_TEXT)} characters")
    print()

    # Initialize client
    print("-" * 80)
    print("Initializing SiliconFlow client...")
    print("-" * 80)
    client = SiliconFlowClient(api_key=api_key, base_url=base_url)
    print(f"✓ Client initialized")
    print()

    # Optimize formatting with smaller window size to force multiple windows
    print("-" * 80)
    print("Optimizing text formatting with sliding window...")
    print("-" * 80)

    optimized_text = client.optimize_pdf_text_formatting(
        model=model,
        extracted_text=LONG_PDF_TEXT,
        context="TRPG story text about a town and a dragon",
        stream_print=True,
        window_char_limit=3000,  # Smaller window to force multiple windows
        overlap_paragraphs=1
    )

    print()
    print(f"✓ Formatting optimization completed")
    print()

    # Display optimized text preview
    print("-" * 80)
    print("Optimized Text Preview (first 500 chars):")
    print("-" * 80)
    print(optimized_text[:500])
    print("...")
    print()

    # Verification checks
    print("=" * 80)
    print("Optimization Verification")
    print("=" * 80)
    print()

    checks_passed = 0
    checks_total = 0

    # Check 1: Proper names should be capitalized
    proper_names = ["Sheerleaf", "Arthfell", "Andoran", "Eliana", "Zikritrax",
                    "Mount Zoldos", "Desna", "Thorin", "Valerius", "Lyrian",
                    "Garrick", "Lost Omens"]
    for name in proper_names:
        checks_total += 1
        if name in optimized_text:
            print(f"✓ '{name}' is properly capitalized")
            checks_passed += 1
        else:
            print(f"✗ '{name}' not found or not properly capitalized")

    # Check 2: Broken words should be fixed
    broken_words = ["eli- ana", "zi kritrax", "she er- leaf", "zi- kritrax", "she erleaf"]
    checks_total += 1
    broken_found = [word for word in broken_words if word in optimized_text]
    if not broken_found:
        print(f"✓ No broken words found")
        checks_passed += 1
    else:
        print(f"✗ Broken words still present: {broken_found}")

    # Check 3: All original content should be preserved (rough check by length)
    checks_total += 1
    # Optimized text should be similar length or slightly shorter (removing extra whitespace)
    if len(optimized_text) >= len(LONG_PDF_TEXT) * 0.8:
        print(f"✓ Content preserved (length: {len(optimized_text)} vs {len(LONG_PDF_TEXT)})")
        checks_passed += 1
    else:
        print(f"✗ Excessive content lost (length: {len(optimized_text)} vs {len(LONG_PDF_TEXT)})")

    # Check 4: Lowercase at sentence beginnings should be fixed
    checks_total += 1
    lowercase_starts = []
    sentences = optimized_text.split('. ')
    for sentence in sentences[:10]:  # Check first 10 sentences
        if sentence and sentence[0].islower():
            lowercase_starts.append(sentence[:20])
    if not lowercase_starts:
        print(f"✓ No lowercase sentence beginnings found")
        checks_passed += 1
    else:
        print(f"✗ Lowercase at sentence start: {lowercase_starts[:3]}")

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
    exit_code = test_long_text_formatting()
    sys.exit(exit_code)
