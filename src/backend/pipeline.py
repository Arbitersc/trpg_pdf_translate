"""
Translation Pipeline for TRPG Documents
Handles end-to-end translation workflow including proper noun extraction,
glossary generation, translation, and post-translation updates.
"""

import json
import re
import sys
import datetime
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from difflib import SequenceMatcher

# Handle both package and direct imports
try:
    from .client import SiliconFlowClient
except ImportError:
    from backend.client import SiliconFlowClient

# Import parser interface
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
try:
    from parser_interface import parse_pdf
except ImportError:
    try:
        from backend.parser_interface import parse_pdf
    except ImportError:
        # Try to import from parent directory
        sys.path.insert(0, str(backend_dir.parent))
        from backend.parser_interface import parse_pdf

# Try to import pandas/pyarrow for parquet support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def similar(a: str, b: str) -> float:
    """
    Calculate similarity ratio between two strings using SequenceMatcher

    Args:
        a: First string
        b: Second string

    Returns:
        Similarity ratio between 0 and 1
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_similar_terms(
    term: str,
    all_terms: List[str],
    already_queued: set,
    min_similarity: float = 0.6
) -> List[str]:
    """
    Find terms similar to the given term using edit distance (similarity ratio)

    Args:
        term: The term to find similar terms for
        all_terms: List of all available terms
        already_queued: Set of terms already queued for translation
        min_similarity: Minimum similarity ratio (default: 0.6)

    Returns:
        List of similar terms that are not already queued
    """
    similar_terms = []

    for other_term in all_terms:
        if other_term == term:
            continue
        if other_term in already_queued:
            continue

        # Calculate similarity
        sim = similar(term, other_term)

        # Check if similarity meets threshold
        if sim >= min_similarity:
            similar_terms.append(other_term)

    return similar_terms


def batch_translate_terms(
    client,
    model: str,
    terms: List[str],
    target_language: str = "中文",
    context: Optional[str] = None,
    stream_print: bool = False,
    existing_glossary: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Batch translate a list of terms using the client

    Args:
        client: SiliconFlowClient instance
        model: Model identifier
        terms: List of terms to translate
        target_language: Target language
        context: Additional context
        stream_print: Whether to stream output
        existing_glossary: Existing glossary entries to avoid re-translating

    Returns:
        Dictionary mapping original terms to translations
    """
    return client.generate_glossary(
        model,
        terms,
        target_language,
        context,
        stream_print,
        existing_glossary
    )


    """
    Split text into sentences while preserving structure

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # First, split by explicit sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Filter out empty strings
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences




def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs

    Args:
        text: Text to split

    Returns:
        List of paragraphs
    """
    # Special handling for TRPG/PF2e formatting:
    # Merge lines that were artificially split (like "Description:" alone on a line)

    # Split by double newlines first to get potential paragraph groups
    para_groups = re.split(r'\n\n+', text)

    paragraphs = []
    for group in para_groups:
        lines = group.strip().split('\n')
        if not lines:
            continue

        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

            # Patterns that should be merged with next line
            should_merge = False

            # Pattern: Single word followed by colon (e.g., "Description:", "Disable:")
            if re.match(r'^[A-Za-z]+\s*:$', line) or re.match(r'^[A-Za-z]+\s+\(.*?\)\s*$', line):
                should_merge = True
            # Pattern: Hazard description line
            elif re.match(r'^[Hh]azard:', line):
                should_merge = True
            # Pattern: AC stats line sometimes split
            elif re.match(r'^AC\s+\d+;', line):
                should_merge = True

            if should_merge and next_line:
                merged_lines.append(line + " " + next_line)
                i += 2
            else:
                merged_lines.append(line)
                i += 1

        # Join merged lines with single newlines
        para = "\n".join(merged_lines)

        # Split markdown headers from their content if needed
        para_parts = re.split(r'(?=^#{1,6}\s)', para, flags=re.MULTILINE)
        for part in para_parts:
            part = part.strip()
            if part:
                paragraphs.append(part)

    return paragraphs


def create_sliding_windows(
    text: str,
    strategy: str = "paragraph",
    window_size: Optional[int] = None,
    overlap_ratio: Optional[float] = None,
    window_char_limit: int = 8000,
    overlap_paragraphs: int = 5
) -> List[Tuple[str, int, int]]:
    """
    Create sliding windows from text based on strategy

    Args:
        text: Text to split into windows
        strategy: "paragraph" or "sentence"
        window_size: Number of paragraphs/sentences per window (DEPRECATED, use window_char_limit)
        overlap_ratio: Overlap ratio (0-1) (DEPRECATED, use overlap_paragraphs)
        window_char_limit: Maximum character limit per window (default: 8000)
        overlap_paragraphs: Number of paragraphs to overlap between windows (default: 5)

    Returns:
        List of tuples (window_text, start_idx, end_idx)
    """
    if strategy == "paragraph":
        units = split_into_paragraphs(text)
    elif strategy == "sentence":
        units = split_into_sentences(text)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    if not units:
        return []

    windows = []

    # New logic: Character-limit based windowing with paragraph overlap
    i = 0
    while i < len(units):
        # Collect units until we reach character limit
        window_units = []
        total_chars = 0

        for j in range(i, len(units)):
            unit = units[j]
            unit_len = len(unit)

            # Estimate separator length
            separator_len = 2 if strategy == "paragraph" else 1
            if window_units:
                total_chars += separator_len

            if total_chars + unit_len > window_char_limit and window_units:
                # Don't add this unit if it would exceed limit (and we already have at least one)
                break

            window_units.append(unit)
            total_chars += unit_len

        if not window_units:
            # At least include the current unit even if it exceeds limit
            window_units = [units[i]]
            j = i

        # Join window units
        if strategy == "paragraph":
            window_text = "\n\n".join(window_units)
        else:
            window_text = " ".join(window_units)

        end_idx = j
        windows.append((window_text, i, end_idx))

        # Check if we've reached the end of the document
        if end_idx == len(units) - 1:
            # This window contains the last unit, no need to create more windows
            break

        # Move to next window with overlap
        # Step forward by (window_size - overlap_paragraphs) paragraphs
        window_len = len(window_units)
        step_size = window_len - overlap_paragraphs
        if step_size <= 1:
            step_size = 1  # Always move forward at least 1 unit

        i += step_size

        # Stop if we've covered all units
        if i >= len(units):
            break

    return windows


def split_text_by_strategy(
    text: str,
    strategy: str = "paragraph",
    chunk_size: int = 3,
    overlap_ratio: float = 0.0,
    window_char_limit: int = 8000,
    overlap_paragraphs: int = 2
) -> List[str]:
    """
    Unified text splitting function for proper noun extraction and translation.

    Splits text into chunks based on the specified strategy (paragraph or sentence).
    Can include overlaps to maintain context between adjacent chunks.

    Args:
        text: Text to split
        strategy: "paragraph" or "sentence"
        chunk_size: DEPRECATED: Number of paragraphs/sentences per chunk.
                   Use window_char_limit and overlap_paragraphs for new logic.
        overlap_ratio: DEPRECATED: Overlap ratio (0-1) between chunks.
                      Use window_char_limit and overlap_paragraphs for new logic.
        window_char_limit: Maximum character limit per chunk (default: 8000)
        overlap_paragraphs: Number of paragraphs to overlap between chunks (default: 2 for noun extraction)

    Returns:
        List of text chunks
    """
    if strategy == "paragraph":
        units = split_into_paragraphs(text)
    elif strategy == "sentence":
        units = split_into_sentences(text)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    if not units:
        return []

    # Use new sliding window logic by default
    windows = create_sliding_windows(
        text,
        strategy,
        window_char_limit=window_char_limit,
        overlap_paragraphs=overlap_paragraphs
    )
    return [window_text for window_text, _, _ in windows]


def merge_translations(
    windows: List[Tuple[str, int, int]],
    translations: List[str],
    strategy: str = "paragraph",
    overlap_paragraphs: int = 5,
    window_size: Optional[int] = None,
    overlap_ratio: Optional[float] = None
) -> str:
    """
    Merge translated windows into a single translation

    Args:
        windows: List of (window_text, start_idx, end_idx) tuples
        translations: List of translated texts
        strategy: "paragraph" or "sentence"
        overlap_paragraphs: Number of paragraphs overlapping between windows
        window_size: DEPRECATED, not used in new logic
        overlap_ratio: DEPRECATED, not used in new logic

    Returns:
        Merged translation text
    """
    if len(windows) != len(translations):
        raise ValueError(f"Number of windows ({len(windows)}) doesn't match translations ({len(translations)})")

    if not windows:
        return ""

    units = []

    # Parse each translation to get its units
    for idx, (window_text, start, end) in enumerate(windows):
        if strategy == "paragraph":
            window_units = split_into_paragraphs(translations[idx])
        else:
            window_units = split_into_sentences(translations[idx])

        # For each unit in this window, decide whether to include it
        for unit_idx, unit in enumerate(window_units):
            absolute_idx = start + unit_idx

            # Skip units in overlap region (except for last window)
            is_overlap = unit_idx < overlap_paragraphs and idx > 0

            # For last window, only include non-overlapping units if there are enough units
            # to avoid duplication at the end
            is_last_window = idx == len(windows) - 1

            # Calculate actual overlap for this window
            actual_overlap = min(overlap_paragraphs, len(window_units))

            if not is_overlap or (is_last_window and unit_idx >= actual_overlap):
                while len(units) <= absolute_idx:
                    units.append(None)
                if units[absolute_idx] is None:
                    units[absolute_idx] = unit

    # Join all units
    units = [u for u in units if u is not None]

    if strategy == "paragraph":
        return "\n\n".join(units)
    else:
        # Use sentence punctuation for joining
        return " ".join(units)


class TranslationPipeline:
    """Pipeline for translating TRPG documents"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        glossary_file: Optional[str] = None
    ):
        """
        Initialize translation pipeline

        Args:
            api_key: API key (reads from SILICONFLOW_API_KEY env var if not provided)
            base_url: Base URL (reads from SILICONFLOW_BASE_URL env var if not provided)
            model: Model identifier (reads from SILICONFLOW_MODEL env var if not provided)
            glossary_file: Path to glossary parquet file (default: doc/glossary/default.parquet)
        """
        import os
        self.model = model or os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")
        self.client = SiliconFlowClient(api_key, base_url)
        self.glossary_file = glossary_file or "doc/glossary/default.parquet"

    def load_glossary(self, file_path: Optional[str] = None) -> Dict[str, str]:
        """
        Load glossary from parquet file

        Args:
            file_path: Path to glossary file (uses self.glossary_file if not provided)

        Returns:
            Dictionary mapping original terms to translations
        """
        file_path = file_path or self.glossary_file

        if not PANDAS_AVAILABLE:
            print("Warning: pandas not available, cannot load glossary from parquet")
            return {}

        path = Path(file_path)
        if not path.exists():
            return {}

        try:
            df = pd.read_parquet(path)
            if "original" in df.columns and "translation" in df.columns:
                return dict(zip(df["original"], df["translation"]))
            return {}
        except Exception as e:
            print(f"Warning: Failed to load glossary from {file_path}: {e}")
            return {}

    def save_glossary(self, glossary: Dict[str, str], file_path: Optional[str] = None) -> bool:
        """
        Save glossary to parquet file

        Args:
            glossary: Dictionary mapping original terms to translations
            file_path: Path to save glossary (uses self.glossary_file if not provided)

        Returns:
            True if saved successfully, False otherwise
        """
        file_path = file_path or self.glossary_file

        if not PANDAS_AVAILABLE:
            print("Warning: pandas not available, cannot save glossary to parquet")
            return False

        if not glossary:
            return False

        try:
            path = Path(file_path)
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing glossary and merge
            existing_glossary = {}
            if path.exists():
                existing_glossary = self.load_glossary(file_path)

            # Merge glossaries (new entries override existing ones)
            merged_glossary = {**existing_glossary, **glossary}

            # Save to parquet
            df = pd.DataFrame(list(merged_glossary.items()), columns=["original", "translation"])
            df.to_parquet(path, index=False)
            return True
        except Exception as e:
            print(f"Warning: Failed to save glossary to {file_path}: {e}")
            return False

    def extract_proper_nouns_from_file(
        self,
        text: str,
        context: Optional[str] = None,
        strategy: str = "paragraph",
        chunk_size: Optional[int] = None,
        overlap_ratio: Optional[float] = None,
        window_char_limit: int = 8000,
        overlap_paragraphs: int = 2,
        stream_print: bool = False
    ) -> List[str]:
        """
        Extract proper nouns from document text using paragraph/sentence-based splitting

        Args:
            text: Document text content
            context: Additional context about the document
            strategy: "paragraph" or "sentence" for text splitting
            chunk_size: DEPRECATED, use window_char_limit instead
            overlap_ratio: DEPRECATED, use overlap_paragraphs instead
            window_char_limit: Maximum character limit per chunk (default: 8000)
            overlap_paragraphs: Number of paragraphs to overlap between chunks (default: 2)
            stream_print: If True, stream and print LLM output in real-time

        Returns:
            List of extracted proper nouns
        """
        # Use unified splitting function with new parameters
        chunks = split_text_by_strategy(text, strategy, window_char_limit=window_char_limit, overlap_paragraphs=overlap_paragraphs)

        all_nouns = set()

        for i, chunk in enumerate(chunks):
            if len(chunk) < 100:  # Skip very small chunks
                continue

            nouns = self.client.extract_proper_nouns(
                self.model,
                chunk,
                context or f"Chunk {i + 1} of {len(chunks)}",
                stream_print
            )
            all_nouns.update(nouns)

        # Remove empty strings and duplicates
        return list(filter(None, sorted(set(all_nouns))))

    def generate_glossary_from_nouns(
        self,
        proper_nouns: List[str],
        target_language: str = "中文",
        context: Optional[str] = None,
        stream_print: bool = False,
        save_glossary: bool = True
    ) -> Dict[str, str]:
        """
        Generate translation glossary from proper nouns with smart batching

        Strategy:
        1. Sort all new terms alphabetically
        2. Add terms one by one to the translation queue
        3. For each term, also add similar terms (based on edit distance) for consistency
        4. When 100+ terms are queued, translate them in a batch
        5. Repeat until all terms are translated

        Args:
            proper_nouns: List of proper nouns
            target_language: Target language for translations
            context: Additional context about the document
            stream_print: If True, stream and print the output in real-time
            save_glossary: If True, save the generated glossary to file

        Returns:
            Dictionary mapping original terms to translations
        """
        if not proper_nouns:
            return {}

        # Load existing glossary and filter out terms that already have translations
        existing_glossary = self.load_glossary()
        # Sort all new terms alphabetically and remove duplicates
        new_nouns = sorted(set([noun for noun in proper_nouns if noun and noun not in existing_glossary]))

        if existing_glossary and stream_print:
            print(f"Loaded {len(existing_glossary)} existing glossary entries")
            print(f"Filtering to {len(new_nouns)} new terms to translate")

        if not new_nouns:
            # All terms already in glossary, return existing
            return existing_glossary

        full_glossary = {**existing_glossary}
        batch_size = 100
        queue = []
        already_queued = set()

        if stream_print:
            print(f"Starting batch translation with {len(new_nouns)} terms (batch size: {batch_size})")

        while new_nouns:
            # Take the first term from alphabetically sorted list
            term = new_nouns.pop(0)

            if term in already_queued:
                continue

            # Add current term to queue
            queue.append(term)
            already_queued.add(term)

            # Find and add similar terms for consistency
            similar_terms = find_similar_terms(term, new_nouns, already_queued)
            for similar_term in similar_terms:
                queue.append(similar_term)
                already_queued.add(similar_term)
                # Also remove from new_nouns to avoid re-adding
                if similar_term in new_nouns:
                    new_nouns.remove(similar_term)

            # If queue reaches batch size, translate
            if len(queue) >= batch_size:
                if stream_print:
                    print(f"\nTranslating batch of {len(queue)} terms...")

                batch_glossary = self.client.generate_glossary(
                    self.model,
                    queue,
                    target_language,
                    context,
                    stream_print,
                    existing_glossary=full_glossary  # Pass existing glossary for partial word matching
                )

                full_glossary.update(batch_glossary)

                if stream_print and batch_glossary:
                    print(f"  ✓ Translated {len(batch_glossary)} terms")

                queue.clear()

        # Translate remaining terms in queue
        if queue:
            if stream_print:
                print(f"\nTranslating final batch of {len(queue)} terms...")

            batch_glossary = self.client.generate_glossary(
                self.model,
                queue,
                target_language,
                context,
                stream_print,
                existing_glossary=full_glossary  # Pass existing glossary for partial word matching
            )

            full_glossary.update(batch_glossary)

            if stream_print and batch_glossary:
                print(f"  ✓ Translated {len(batch_glossary)} terms")

        # Extract only new glossary entries for saving
        new_entries = {k: v for k, v in full_glossary.items() if k not in existing_glossary}

        # Save to file if enabled
        if save_glossary and new_entries:
            self.save_glossary(new_entries)
            if stream_print:
                print(f"Saved {len(new_entries)} new glossary entries to {self.glossary_file}")
        elif save_glossary:
            if stream_print:
                print(f"No new entries to save")

        return full_glossary

    def translate_document(
        self,
        text: str,
        source_language: str = "English",
        target_language: str = "中文",
        context: Optional[str] = None,
        auto_extract_nouns: bool = True,
        existing_glossary: Optional[Dict[str, str]] = None,
        use_sliding_window: bool = True,
        window_strategy: str = "paragraph",
        window_size: int = 3,
        overlap_ratio: float = 0.5,
        stream_print: bool = False
    ) -> Dict[str, Any]:
        """
        Translate document with optional proper noun extraction and glossary usage

        Args:
            text: Document text to translate
            source_language: Source language
            target_language: Target language
            context: Additional context about the document
            auto_extract_nouns: Whether to automatically extract proper nouns
            existing_glossary: Existing glossary to use instead of extracting
            use_sliding_window: Whether to use sliding window for translation
            window_strategy: "paragraph" or "sentence"
            window_size: Number of paragraphs/sentences per window
            overlap_ratio: Overlap ratio (0-1), e.g., 0.5 = 50% overlap
            stream_print: If True, stream and print LLM output in real-time

        Returns:
            Dictionary with translation results and metadata
        """
        result = {
            "original_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "model": self.model,
            "use_sliding_window": use_sliding_window,
            "window_strategy": window_strategy,
            "window_size": window_size,
            "overlap_ratio": overlap_ratio,
            "translation_errors": []
        }

        glossary = existing_glossary or {}

        # Step 1: Extract proper nouns if enabled
        if auto_extract_nouns and not existing_glossary:
            # Use smaller character limit and overlap for noun extraction to reduce computation
            proper_nouns = self.extract_proper_nouns_from_file(
                text, context, window_strategy,
                window_char_limit=8000,
                overlap_paragraphs=2
            )
            result["proper_nouns"] = proper_nouns

            # Step 2: Generate glossary
            if proper_nouns:
                glossary = self.generate_glossary_from_nouns(
                    proper_nouns,
                    target_language,
                    context,
                    stream_print
                )
                result["glossary"] = glossary
        elif existing_glossary:
            result["glossary"] = existing_glossary

        # Step 3: Translate text
        if use_sliding_window:
            translated = self._translate_with_sliding_window(
                text,
                source_language,
                target_language,
                glossary,
                context,
                window_strategy,
                stream_print,
                result
            )
        else:
            translated = self.client.translate_text(
                self.model,
                text,
                source_language,
                target_language,
                glossary,
                context,
                stream_print
            )
        result["translated_text"] = translated

        # Step 4: Update translation with glossary for consistency
        if glossary:
            result["updated_translation"] = self.client.update_translation_with_glossary(
                self.model,
                translated,
                glossary,
                context,
                stream_print
            )
        else:
            result["updated_translation"] = translated

        return result

    def _translate_with_sliding_window(
        self,
        text: str,
        source_language: str,
        target_language: str,
        glossary: Optional[Dict[str, str]],
        context: Optional[str],
        window_strategy: str,
        stream_print: bool,
        result: Dict[str, Any]
    ) -> str:
        """
        Translate text using sliding window approach with streaming

        Args:
            text: Text to translate
            source_language: Source language
            target_language: Target language
            glossary: Translation glossary
            context: Document context
            window_strategy: "paragraph" or "sentence"
            stream_print: If True, stream and print LLM output in real-time
            result: Result dictionary to store metadata

        Returns:
            Translated text
        """
        windows = create_sliding_windows(text, window_strategy, window_char_limit=8000, overlap_paragraphs=5)
        result["num_windows"] = len(windows)

        translations = []

        for idx, (window_text, start, end) in enumerate(windows):
            print(f"  Translating window {idx + 1}/{len(windows)} (units {start + 1}-{end})...")
            translation = self.client.translate_text(
                self.model,
                window_text,
                source_language,
                target_language,
                glossary,
                context,
                stream_print
            )
            translations.append(translation)
            print(f"  ✓ Window {idx + 1} translated")

        # Merge translations
        merged = merge_translations(windows, translations, window_strategy, overlap_paragraphs=5)
        return merged

    def export_output(
        self,
        result: Dict[str, Any],
        output_type: str = "markdown",
        file_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Export translation result to file

        Args:
            result: Translation result from translate_document
            output_type: Output format ("markdown", "json", "bilingual")
            file_path: Output file path (if None, returns content as string)

        Returns:
            File path if saved, or content as string
        """
        if output_type == "json":
            content = json.dumps(result, ensure_ascii=False, indent=2)
        elif output_type == "markdown":
            content = self._format_as_markdown(result)
        elif output_type == "bilingual":
            content = self._format_as_bilingual(result)
        else:
            raise ValueError(f"Unknown output type: {output_type}")

        if file_path:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return file_path
        else:
            return content

    def _format_as_markdown(self, result: Dict[str, Any]) -> str:
        """Format result as markdown"""
        output = []

        output.append(f"# 翻译结果\n")
        output.append(f"**源语言:** {result['source_language']}")
        output.append(f"**目标语言:** {result['target_language']}")
        output.append(f"**模型:** {result['model']}")
        if result.get('use_sliding_window'):
            output.append(f"**窗口策略:** {result.get('window_strategy', 'paragraph')}")
            output.append(f"**窗口数量:** {result.get('num_windows', 1)}")
        output.append("")

        if result.get("translation_errors"):
            output.append("## 翻译警告\n")
            for error in result["translation_errors"]:
                output.append(f"- {error}")
            output.append("\n")

        output.append("## 译文\n")
        output.append(result.get("updated_translation", result.get("translated_text", "")))

        return "\n".join(output)

    def _format_as_bilingual(self, result: Dict[str, Any]) -> str:
        """
        Format result as bilingual (side by side) markdown using LLM-based alignment.

        This uses the LLM to intelligently align English and Chinese text:
        - Headings merged as "中文 (English)"
        - Content paragraphs: English (blockquote) then Chinese
        - Tables merged with aligned rows
        - Sliding window for long texts (max 4000 chars, 500 char overlap)

        Args:
            result: Translation result from translate_document

        Returns:
            Bilingual aligned markdown text
        """
        output = []

        output.append("# 双语对照\n")
        output.append(f"**源语言:** {result['source_language']}")
        output.append(f"**目标语言:** {result['target_language']}")
        output.append(f"**模型:** {result['model']}")
        if result.get('use_sliding_window'):
            output.append(f"**窗口策略:** {result.get('window_strategy', 'paragraph')}")
            output.append(f"**窗口数量:** {result.get('num_windows', 1)}")
        output.append("")

        output.append("## 双语对照\n")
        output.append("")

        original_text = result.get("original_text", "")
        translation_text = result.get("updated_translation", result.get("translated_text", ""))

        if not original_text or not translation_text:
            # Fallback to translation only
            output.append(translation_text)
            return "\n".join(output)

        # Use LLM-based alignment
        try:
            aligned_text = self.client.align_bilingual_text(
                model=self.model,
                english_text=original_text,
                chinese_text=translation_text,
                stream_print=False,
                window_char_limit=4000,
                overlap_chars=500
            )
            output.append(aligned_text)
        except Exception as e:
            # Fallback to simple format if LLM alignment fails
            print(f"Warning: LLM-based alignment failed ({e}), using simple format")
            output.append("> " + original_text.replace("\n", "\n> "))
            output.append("")
            output.append(translation_text)

        return "\n".join(output)

    def update_glossary_manual(self, original_terms: str, translated_terms: str, separator: str = None) -> Dict[str, str]:
        """
        手动修改译名表，支持用户输入原文和译名列表

        Args:
            original_terms: 原文列表，支持用空格、制表符、横杠分隔
            translated_terms: 译名列表，支持用空格、制表符、横杠分隔
            separator: 自定义分隔符（如果为None则自动检测）

        Returns:
            更新后的译名表字典
        """
        # 自动检测分隔符
        if separator is None:
            # 检查是否包含制表符
            if '\t' in original_terms:
                separator = '\t'
            # 检查是否包含横杠
            elif '-' in original_terms and original_terms.count('-') > original_terms.count(' '):
                separator = '-'
            # 默认使用空格
            else:
                separator = ' '

        # 分割原文和译名
        original_list = [term.strip() for term in original_terms.split(separator) if term.strip()]
        translated_list = [term.strip() for term in translated_terms.split(separator) if term.strip()]

        if len(original_list) != len(translated_list):
            raise ValueError(f"原文和译名数量不匹配: 原文{len(original_list)}个，译名{len(translated_list)}个")

        # 加载现有译名表
        existing_glossary = self.load_glossary()

        # 更新译名表
        updated_glossary = {**existing_glossary}
        for orig, trans in zip(original_list, translated_list):
            updated_glossary[orig] = trans

        # 保存新译名表（不覆盖老文件，创建新文件）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_glossary_file = str(Path(self.glossary_file).with_suffix(f".{timestamp}.parquet"))

        if self.save_glossary(updated_glossary, new_glossary_file):
            print(f"✓ 译名表已更新并保存到: {new_glossary_file}")
            print(f"  新增/修改了 {len(original_list)} 个词条")
        else:
            print("⚠ 译名表更新失败")

        return updated_glossary

    def fix_markdown_hyperlink_spaces(self, text: str) -> str:
        """
        修复markdown超链接中的空格，将类似"[装甲洞穴熊](armored cave bear)"改为"[装甲洞穴熊](armored_cave_bear)"

        Args:
            text: 需要处理的文本

        Returns:
            处理后的文本
        """
        import re

        def replace_spaces(match):
            link_text = match.group(1)  # []中的文本
            link_target = match.group(2)  # ()中的URL/路径
            # 将空格替换为下划线
            fixed_target = link_target.replace(' ', '_')
            return f"[{link_text}]({fixed_target})"

        # 匹配markdown链接: [text](target)
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        return re.sub(pattern, replace_spaces, text)

    def retranslate_with_glossary(self, translated_file: str, glossary: Dict[str, str],
                                 output_file: str = None, bilingual_output: bool = False) -> Dict[str, Any]:
        """
        根据已有的翻译文件和译名表内容，重新替换所有超链接格式的译文内容

        Args:
            translated_file: 已翻译的文件路径
            glossary: 译名表字典
            output_file: 输出文件路径（如果为None则返回内容）
            bilingual_output: 是否生成双语文件

        Returns:
            包含处理结果的字典
        """
        # 读取翻译文件
        with open(translated_file, 'r', encoding='utf-8') as f:
            translated_text = f.read()

        # 应用译名表替换
        updated_text = self._apply_glossary_to_text(translated_text, glossary)

        # 修复超链接空格
        final_text = self.fix_markdown_hyperlink_spaces(updated_text)

        result = {
            "original_translation": translated_text,
            "updated_translation": final_text,
            "glossary_applied": glossary,
            "file_path": translated_file
        }

        # 保存或返回结果
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_text)
            result["output_file"] = output_file

            # 如果需要生成双语文件
            if bilingual_output:
                bilingual_file = output_file.replace('.md', '_bilingual.md')
                bilingual_content = self._create_simple_bilingual(translated_text, final_text)
                with open(bilingual_file, 'w', encoding='utf-8') as f:
                    f.write(bilingual_content)
                result["bilingual_file"] = bilingual_file

        return result

    def _apply_glossary_to_text(self, text: str, glossary: Dict[str, str]) -> str:
        """
        将译名表应用到文本中，替换所有匹配的术语

        Args:
            text: 需要处理的文本
            glossary: 译名表字典

        Returns:
            处理后的文本
        """
        import re

        # 按长度降序排序，确保长词优先匹配
        sorted_terms = sorted(glossary.keys(), key=len, reverse=True)

        result_text = text
        for term in sorted_terms:
            translation = glossary[term]
            # 使用单词边界匹配，避免部分匹配
            pattern = r'\b' + re.escape(term) + r'\b'
            result_text = re.sub(pattern, translation, result_text, flags=re.IGNORECASE)

        return result_text

    def _create_simple_bilingual(self, original_text: str, translated_text: str) -> str:
        """
        创建简单的双语对照文件（先输出译文，再输出原文）

        Args:
            original_text: 原文
            translated_text: 译文

        Returns:
            双语对照内容
        """
        output = []
        output.append("# 双语对照\n")
        output.append("## 译文\n")
        output.append(translated_text)
        output.append("\n## 原文\n")
        output.append("> " + original_text.replace("\n", "\n> "))
        return "\n".join(output)


class UnifiedTranslationPipeline:
    """Unified pipeline for PDF parsing and TRPG document translation"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        glossary_file: Optional[str] = None,
        parser_type: Optional[str] = "mineru"
    ):
        """
        Initialize unified translation pipeline

        Args:
            api_key: API key (reads from SILICONFLOW_API_KEY env var if not provided)
            base_url: Base URL (reads from SILICONFLOW_BASE_URL env var if not provided)
            model: Model identifier (reads from SILICONFLOW_MODEL env var if not provided)
            glossary_file: Path to glossary parquet file (default: doc/glossary/default.parquet)
            parser_type: PDF parser type (default: "mineru")
        """
        import os
        self.model = model or os.getenv("SILICONFLOW_MODEL", "Pro/moonshotai/Kimi-K2.5")
        self.client = SiliconFlowClient(api_key, base_url)
        self.glossary_file = glossary_file or "doc/glossary/default.parquet"
        self.parser_type = parser_type or os.getenv("PDF_PARSER_TYPE", "mineru")

    def parse_pdf(
        self,
        pdf_path: str,
        remove_images: bool = True,
        optimize_formatting: bool = False,
        **parse_kwargs
    ) -> Dict[str, Any]:
        """
        Parse PDF file and extract text content

        Args:
            pdf_path: Path to PDF file
            remove_images: Whether to remove markdown image links
            optimize_formatting: Whether to use LLM to optimize text formatting (merge split paragraphs, fix capitalization) (default: False)
            **parse_kwargs: Additional parsing options

        Returns:
            Dictionary with parse results including full_text and pages
        """
        try:
            parse_result = parse_pdf(
                pdf_path,
                parser_type=self.parser_type,
                remove_images=remove_images,
                **parse_kwargs
            )

            if not parse_result.success:
                raise Exception(f"PDF parsing failed: {parse_result.errors}")

            result = {
                "success": parse_result.success,
                "file_path": str(parse_result.file_path),
                "total_pages": parse_result.total_pages,
                "pages": [
                    {
                        "page_number": p.page_number,
                        "text": p.text
                    }
                    for p in parse_result.pages
                ],
                "metadata": parse_result.metadata
            }

            raw_text = parse_result.full_text
            result["raw_text"] = raw_text

            # Optimize formatting if requested
            if optimize_formatting:
                print("Optimizing PDF text formatting with LLM...")
                optimized_text = self.client.optimize_pdf_text_formatting(
                    self.model,
                    raw_text,
                    context=f"PDF document: {Path(pdf_path).name}",
                    stream_print=True
                )
                result["full_text"] = optimized_text
                result["formatting_optimized"] = True
            else:
                result["full_text"] = raw_text
                result["formatting_optimized"] = False

            return result
        except Exception as e:
            raise Exception(f"Failed to parse PDF: {e}")

    def _detect_glossary_terms_in_text(
        self,
        text: str,
        glossary: Dict[str, str]
    ) -> List[str]:
        """
        Detect which glossary terms appear in the given text.

        Args:
            text: Text to search for glossary terms
            glossary: Dictionary of proper nouns and their translations

        Returns:
            List of glossary terms found in the text
        """
        found_terms = []
        text_lower = text.lower()

        for term in glossary.keys():
            # Use word boundary matching to avoid partial matches
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                found_terms.append(term)

        return found_terms

    def translate_document_with_pdf(
        self,
        pdf_path: str,
        source_language: str = "English",
        target_language: str = "中文",
        context: Optional[str] = None,
        auto_extract_nouns: bool = True,
        existing_glossary: Optional[Dict[str, str]] = None,
        window_size: int = 30,
        overlap_ratio: float = 0.5,
        stream_print: bool = False,
        use_hyperlink_format: bool = True,
        output_dir: Optional[str] = None,
        optimize_formatting: bool = False,
        export_bilingual: bool = False
    ) -> Dict[str, Any]:
        """
        Parse PDF and translate its content with unified pipeline

        Args:
            pdf_path: Path to PDF file
            source_language: Source language
            target_language: Target language
            context: Additional context about the document
            auto_extract_nouns: Whether to automatically extract proper nouns
            existing_glossary: Existing glossary to use instead of extracting
            window_size: Number of paragraphs per window (default: 30)
            overlap_ratio: Overlap ratio (0-1) between windows
            stream_print: If True, stream and print LLM output in real-time
            use_hyperlink_format: If True, format proper nouns as markdown hyperlinks
            output_dir: If provided, will export all translation results to this directory
            optimize_formatting: Whether to use LLM to optimize PDF text formatting (default: False)
            export_bilingual: Whether to export bilingual output (default: False)

        Returns:
            Dictionary with translation results and metadata including:
            - parse_result: PDF parsing results
            - proper_nouns: Extracted proper nouns
            - glossary: Translation glossary
            - translated_text: Initial translation
            - updated_translation: Post-processed translation
            - output_files: Dictionary of saved file paths (if output_dir provided)
        """
        # Initialize output directory and file tracking
        pdf_filename = Path(pdf_path).stem
        output_path = None
        output_files = {}

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            print("=" * 80)
            print("TRPG PDF Translation Pipeline")
            print("=" * 80)
            print(f"Input PDF: {pdf_path}")
            print(f"Output Directory: {output_dir}")
            print()

        result = {
            "pdf_path": pdf_path,
            "source_language": source_language,
            "target_language": target_language,
            "model": self.model,
            "window_size": window_size,
            "overlap_ratio": overlap_ratio,
            "translation_errors": []
        }

        # Step 1: Parse PDF
        print(f"Step 1: Parsing PDF: {pdf_path}")
        parse_result = self.parse_pdf(pdf_path, optimize_formatting=optimize_formatting)
        result["parse_result"] = parse_result
        result["total_pages"] = parse_result["total_pages"]
        text = parse_result["full_text"]

        if optimize_formatting and parse_result.get("formatting_optimized"):
            print(f"✓ Parsed and formatted {len(text)} characters from {parse_result['total_pages']} pages")
        else:
            print(f"✓ Parsed {len(text)} characters from {parse_result['total_pages']} pages")

        # Export: Original text from PDF
        if output_dir and output_path:
            orig_text_path = output_path / f"{pdf_filename}_original.txt"
            with open(orig_text_path, "w", encoding="utf-8") as f:
                f.write(text)
            output_files["original_text"] = str(orig_text_path)
            print(f"  → Saved original text: {orig_text_path.name}")

        glossary = existing_glossary or {}

        # Step 2: Extract proper nouns if enabled
        if auto_extract_nouns:
            print(f"\nStep 2: Extracting proper nouns...")
            proper_nouns = self.extract_proper_nouns_from_file(
                text,
                context=context,
                strategy="paragraph",
                window_char_limit=8000,
                overlap_paragraphs=2,
                stream_print=stream_print
            )
            result["proper_nouns"] = proper_nouns
            print(f"✓ Found {len(proper_nouns)} proper nouns")

            # Export: Extracted proper nouns
            if output_dir and output_path and proper_nouns:
                nouns_path = output_path / f"{pdf_filename}_proper_nouns.txt"
                with open(nouns_path, "w", encoding="utf-8") as f:
                    f.write("Extracted Proper Nouns\n")
                    f.write("=" * 50 + "\n\n")
                    for i, noun in enumerate(proper_nouns, 1):
                        f.write(f"{i:4d}. {noun}\n")
                output_files["proper_nouns"] = str(nouns_path)
                print(f"  → Saved proper nouns: {nouns_path.name}")

            # Step 3: Generate glossary (only for new terms not in existing glossary)
            if proper_nouns:
                print(f"\nStep 3: Generating glossary...")
                glossary = self.generate_glossary_from_nouns(
                    proper_nouns,
                    target_language,
                    context,
                    stream_print,
                    save_glossary=False  # Don't save automatically when using existing glossary
                )

                # Merge with existing glossary if provided
                if existing_glossary:
                    # Only add new terms to existing glossary
                    for term, translation in glossary.items():
                        if term not in existing_glossary:
                            existing_glossary[term] = translation
                    glossary = existing_glossary
                    print(f"✓ Merged with existing glossary: {len(glossary)} total entries ({len(proper_nouns)} new terms extracted)")
                else:
                    print(f"✓ Generated {len(glossary)} glossary entries")

                result["glossary"] = glossary

                # Export: Glossary
                if output_dir and output_path and glossary:
                    glossary_path = output_path / f"{pdf_filename}_glossary.txt"
                    with open(glossary_path, "w", encoding="utf-8") as f:
                        f.write("译名表 (Glossary)\n")
                        f.write("=" * 50 + "\n\n")
                        for orig, trans in sorted(glossary.items()):
                            f.write(f"{orig:40s} → {trans}\n")
                    output_files["glossary"] = str(glossary_path)
                    print(f"  → Saved glossary: {glossary_path.name}")
        elif existing_glossary:
            result["glossary"] = existing_glossary
            print(f"\nUsing existing glossary with {len(existing_glossary)} entries")

            # Export: Existing glossary
            if output_dir and output_path:
                glossary_path = output_path / f"{pdf_filename}_glossary.txt"
                with open(glossary_path, "w", encoding="utf-8") as f:
                    f.write("译名表 (Glossary)\n")
                    f.write("=" * 50 + "\n\n")
                    for orig, trans in sorted(existing_glossary.items()):
                        f.write(f"{orig:40s} → {trans}\n")
                output_files["glossary"] = str(glossary_path)
                print(f"  → Saved glossary: {glossary_path.name}")

        # Step 4: Translate text with sliding window and glossary detection
        print(f"\nStep 4: Translating with 8000-character sliding windows, 5-paragraph overlap...")
        translated = self._translate_with_sliding_window_and_glossary(
            text,
            source_language,
            target_language,
            glossary,
            context,
            stream_print,
            use_hyperlink_format,
            result
        )
        result["translated_text"] = translated
        print(f"✓ Translation completed")

        # Export: Initial translation
        if output_dir and output_path:
            initial_trans_path = output_path / f"{pdf_filename}_translation_initial.md"
            with open(initial_trans_path, "w", encoding="utf-8") as f:
                f.write("# Initial Translation (Before Post-Processing)\n\n")
                f.write(translated)
            output_files["initial_translation"] = str(initial_trans_path)
            print(f"  → Saved initial translation: {initial_trans_path.name}")

        # Also export detected terms if any
        detected_terms = result.get('all_detected_terms', [])
        if output_dir and output_path and detected_terms:
            detected_path = output_path / f"{pdf_filename}_detected_terms.txt"
            with open(detected_path, "w", encoding="utf-8") as f:
                f.write("检测到的术语 (Detected Terms in Text)\n")
                f.write("=" * 50 + "\n\n")
                for term in sorted(detected_terms):
                    trans = glossary.get(term, term)
                    f.write(f"{term:40s} → {trans}\n")
            output_files["detected_terms"] = str(detected_path)
            print(f"  → Saved detected terms: {detected_path.name}")

        # Step 5: Update translation with glossary for consistency
        if glossary and not use_hyperlink_format:
            print(f"\nStep 5: Updating translation for glossary consistency...")
            result["updated_translation"] = self.client.update_translation_with_glossary(
                self.model,
                translated,
                glossary,
                context,
                stream_print
            )
            print(f"✓ Translation updated")
        else:
            result["updated_translation"] = translated

        # Step 6: Post-process translation - fix markdown hyperlinks
        print(f"\nStep 6: Post-processing translation - fixing markdown hyperlinks...")
        result["updated_translation"] = self.fix_markdown_hyperlink_spaces(result["updated_translation"])
        print(f"✓ Markdown hyperlinks fixed")

        # Export: Final translation results
        if output_dir and output_path:
            # Export markdown
            md_path = output_path / f"{pdf_filename}.md"
            self.export_output(result, "markdown", str(md_path))
            output_files["markdown"] = str(md_path)

            # Export JSON
            json_path = output_path / f"{pdf_filename}.json"
            self.export_output(result, "json", str(json_path))
            output_files["json"] = str(json_path)

            # Export bilingual (optional)
            if export_bilingual:
                bilingual_path = output_path / f"{pdf_filename}_bilingual.md"
                self.export_output(result, "bilingual", str(bilingual_path))
                output_files["bilingual"] = str(bilingual_path)
                print(f"  → Saved bilingual: {bilingual_path.name}")

            print(f"  → Saved final markdown: {md_path.name}")
            print(f"  → Saved JSON: {json_path.name}")

            # Display results summary
            print()
            print("-" * 80)
            print("Translation Summary")
            print("-" * 80)
            print(f"PDF: {result.get('pdf_path', 'N/A')}")
            print(f"Total Pages: {result.get('total_pages', 'N/A')}")
            print(f"Characters Parsed: {len(text)}")
            print(f"Proper Nouns Found: {len(result.get('proper_nouns', []))}")
            print(f"Glossary Entries: {len(glossary)}")
            print(f"Translation Windows: {result.get('num_windows', 'N/A')}")
            print(f"Detected Terms in Text: {len(detected_terms)}")
            print()

            # Display summary of generated files
            print("-" * 80)
            print("Generated Files")
            print("-" * 80)
            for file_type, file_path in sorted(output_files.items()):
                print(f"  [{file_type:20s}] {Path(file_path).name}")
            print()

            # Display translation preview
            print("-" * 80)
            print("Translation Preview (first 500 chars):")
            print("-" * 80)
            final_translation = result.get("updated_translation", "")
            print(final_translation[:500])
            if len(final_translation) > 500:
                print("...")
            print()

            print("=" * 80)
            print("Translation pipeline completed successfully!")
            print("=" * 80)
            print()
        else:
            print(f"\n✓ Translation pipeline completed")

        if output_dir and output_path:
            result["output_files"] = output_files

        return result

    def translate_pdf_to_files(
        self,
        pdf_path: str,
        output_dir: str,
        source_language: str = "English",
        target_language: str = "中文",
        context: Optional[str] = None,
        auto_extract_nouns: bool = True,
        existing_glossary: Optional[Dict[str, str]] = None,
        window_size: int = 30,
        overlap_ratio: float = 0.5,
        stream_print: bool = False,
        use_hyperlink_format: bool = True,
        optimize_formatting: bool = False,
        export_bilingual: bool = False
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Parse PDF, extract terms, translate, and export all output files.

        This is a convenience method that performs the entire translation workflow
        and exports all result files to the specified output directory.

        Args:
            pdf_path: Path to input PDF file
            output_dir: Directory path for output files
            source_language: Source language
            target_language: Target language
            context: Additional context about the document
            auto_extract_nouns: Whether to automatically extract proper nouns
            existing_glossary: Existing glossary to use instead of extracting
            window_size: Number of paragraphs per window (default: 30)
            overlap_ratio: Overlap ratio (0-1) between windows
            stream_print: If True, stream and print LLM output in real-time
            use_hyperlink_format: If True, format proper nouns as markdown hyperlinks
            optimize_formatting: Whether to use LLM to optimize PDF text formatting (default: False)
            export_bilingual: Whether to export bilingual output (default: False)

        Returns:
            Dictionary containing translation results and output file paths:
            - output_files: Dictionary mapping file types to their output paths
            - All other fields from translate_document_with_pdf
        """
        # Call translate_document_with_pdf with output_dir
        # Note: The header printing is handled inside translate_document_with_pdf when output_dir is provided
        result = self.translate_document_with_pdf(
            pdf_path=pdf_path,
            source_language=source_language,
            target_language=target_language,
            context=context,
            auto_extract_nouns=auto_extract_nouns,
            existing_glossary=existing_glossary,
            window_size=window_size,
            overlap_ratio=overlap_ratio,
            stream_print=stream_print,
            use_hyperlink_format=use_hyperlink_format,
            optimize_formatting=optimize_formatting,
            export_bilingual=export_bilingual,
            output_dir=output_dir
        )

        return result

    def _translate_with_sliding_window_and_glossary(
        self,
        text: str,
        source_language: str,
        target_language: str,
        glossary: Optional[Dict[str, str]],
        context: Optional[str],
        stream_print: bool,
        use_hyperlink_format: bool,
        result: Dict[str, Any]
    ) -> str:
        """
        Translate text using sliding window approach with glossary term detection

        Args:
            text: Text to translate
            source_language: Source language
            target_language: Target language
            glossary: Translation glossary
            context: Document context
            stream_print: If True, stream and print LLM output in real-time
            use_hyperlink_format: If True, format proper nouns as markdown hyperlinks
            result: Result dictionary to store metadata

        Returns:
            Translated text
        """
        windows = create_sliding_windows(text, "paragraph", window_char_limit=8000, overlap_paragraphs=5)
        result["num_windows"] = len(windows)

        translations = []
        detected_terms_list = []

        for idx, (window_text, start, end) in enumerate(windows):
            print(f"\n  Translating window {idx + 1}/{len(windows)} (paragraphs {start + 1}-{end})...")

            # Detect glossary terms in this window
            if glossary:
                detected_terms = self._detect_glossary_terms_in_text(window_text, glossary)
                detected_terms_list.extend(detected_terms)
                if detected_terms and stream_print:
                    print(f"    → Found {len(detected_terms)} glossary terms in this window")

            translation = self.client.translate_text(
                self.model,
                window_text,
                source_language,
                target_language,
                glossary,
                context,
                stream_print,
                detected_terms if glossary else None,
                use_hyperlink_format
            )
            translations.append(translation)
            print(f"  ✓ Window {idx + 1} translated")

        result["all_detected_terms"] = list(set(detected_terms_list))
        print(f"\n  Total unique glossary terms detected across text: {len(result['all_detected_terms'])}")

        # Merge translations
        merged = merge_translations(windows, translations, "paragraph", overlap_paragraphs=5)
        return merged

    def extract_proper_nouns_from_file(
        self,
        text: str,
        context: Optional[str] = None,
        strategy: str = "paragraph",
        chunk_size: Optional[int] = None,
        overlap_ratio: Optional[float] = None,
        window_char_limit: int = 8000,
        overlap_paragraphs: int = 2,
        stream_print: bool = False
    ) -> List[str]:
        """Extract proper nouns from document text using paragraph/sentence-based splitting"""
        chunks = split_text_by_strategy(text, strategy, window_char_limit=window_char_limit, overlap_paragraphs=overlap_paragraphs)
        all_nouns = set()

        for i, chunk in enumerate(chunks):
            if len(chunk) < 100:
                continue

            nouns = self.client.extract_proper_nouns(
                self.model,
                chunk,
                context or f"Chunk {i + 1} of {len(chunks)}",
                stream_print
            )
            all_nouns.update(nouns)

        return list(filter(None, sorted(set(all_nouns))))

    def generate_glossary_from_nouns(
        self,
        proper_nouns: List[str],
        target_language: str = "中文",
        context: Optional[str] = None,
        stream_print: bool = False,
        save_glossary: bool = True
    ) -> Dict[str, str]:
        """
        Generate translation glossary from proper nouns with smart batching

        Strategy:
        1. Sort all new terms alphabetically
        2. Add terms one by one to the translation queue
        3. For each term, also add similar terms (based on edit distance) for consistency
        4. When 100+ terms are queued, translate them in a batch
        5. Repeat until all terms are translated

        Args:
            proper_nouns: List of proper nouns
            target_language: Target language for translations
            context: Additional context about the document
            stream_print: If True, stream and print the output in real-time
            save_glossary: If True, save the generated glossary to file

        Returns:
            Dictionary mapping original terms to translations
        """
        if not proper_nouns:
            return {}

        existing_glossary = self._load_glossary()
        # Sort all new terms alphabetically and remove duplicates
        new_nouns = sorted(set([noun for noun in proper_nouns if noun and noun not in existing_glossary]))

        if existing_glossary and stream_print:
            print(f"Loaded {len(existing_glossary)} existing glossary entries")
            print(f"Filtering to {len(new_nouns)} new terms to translate")

        if not new_nouns:
            return existing_glossary

        full_glossary = {**existing_glossary}
        batch_size = 100
        queue = []
        already_queued = set()

        if stream_print:
            print(f"Starting batch translation with {len(new_nouns)} terms (batch size: {batch_size})")

        while new_nouns:
            # Take the first term from alphabetically sorted list
            term = new_nouns.pop(0)

            if term in already_queued:
                continue

            # Add current term to queue
            queue.append(term)
            already_queued.add(term)

            # Find and add similar terms for consistency
            similar_terms = find_similar_terms(term, new_nouns, already_queued)
            for similar_term in similar_terms:
                queue.append(similar_term)
                already_queued.add(similar_term)
                # Also remove from new_nouns to avoid re-adding
                if similar_term in new_nouns:
                    new_nouns.remove(similar_term)

            # If queue reaches batch size, translate
            if len(queue) >= batch_size:
                if stream_print:
                    print(f"\nTranslating batch of {len(queue)} terms...")

                batch_glossary = self.client.generate_glossary(
                    self.model,
                    queue,
                    target_language,
                    context,
                    stream_print,
                    existing_glossary=full_glossary  # Pass existing glossary for partial word matching
                )

                full_glossary.update(batch_glossary)

                if stream_print and batch_glossary:
                    print(f"  ✓ Translated {len(batch_glossary)} terms")

                queue.clear()

        # Translate remaining terms in queue
        if queue:
            if stream_print:
                print(f"\nTranslating final batch of {len(queue)} terms...")

            batch_glossary = self.client.generate_glossary(
                self.model,
                queue,
                target_language,
                context,
                stream_print,
                existing_glossary=full_glossary  # Pass existing glossary for partial word matching
            )

            full_glossary.update(batch_glossary)

            if stream_print and batch_glossary:
                print(f"  ✓ Translated {len(batch_glossary)} terms")

        # Extract only new glossary entries for saving
        new_entries = {k: v for k, v in full_glossary.items() if k not in existing_glossary}

        if save_glossary and new_entries:
            self._save_glossary(new_entries)
            if stream_print:
                print(f"Saved {len(new_entries)} new glossary entries to {self.glossary_file}")
        elif save_glossary:
            if stream_print:
                print(f"No new entries to save")

        return full_glossary

    def _load_glossary(self) -> Dict[str, str]:
        """Load glossary from parquet file"""
        if not PANDAS_AVAILABLE:
            return {}

        path = Path(self.glossary_file)
        if not path.exists():
            return {}

        try:
            df = pd.read_parquet(path)
            if "original" in df.columns and "translation" in df.columns:
                return dict(zip(df["original"], df["translation"]))
            return {}
        except Exception as e:
            print(f"Warning: Failed to load glossary from {self.glossary_file}: {e}")
            return {}

    def _save_glossary(self, glossary: Dict[str, str]) -> bool:
        """Save glossary to parquet file"""
        if not PANDAS_AVAILABLE or not glossary:
            return False

        try:
            path = Path(self.glossary_file)
            path.parent.mkdir(parents=True, exist_ok=True)

            existing_glossary = {}
            if path.exists():
                existing_glossary = self._load_glossary()

            merged_glossary = {**existing_glossary, **glossary}
            df = pd.DataFrame(list(merged_glossary.items()), columns=["original", "translation"])
            df.to_parquet(path, index=False)
            return True
        except Exception as e:
            print(f"Warning: Failed to save glossary to {self.glossary_file}: {e}")
            return False

    def export_output(
        self,
        result: Dict[str, Any],
        output_type: str = "markdown",
        file_path: Optional[str] = None,
        use_llm_alignment: bool = True
    ) -> Optional[str]:
        """
        Export translation result to file

        Args:
            result: Translation result from translate_document_with_pdf
            output_type: Output format ("markdown", "json", "bilingual")
            file_path: Output file path (if None, returns content as string)
            use_llm_alignment: Whether to use LLM-based alignment for bilingual output (default: True)

        Returns:
            File path if saved, or content as string
        """
        if output_type == "json":
            content = json.dumps(result, ensure_ascii=False, indent=2)
        elif output_type == "markdown":
            content = self._format_as_markdown(result)
        elif output_type == "bilingual":
            content = self._format_as_bilingual(result, use_llm_alignment)
        else:
            raise ValueError(f"Unknown output type: {output_type}")

        if file_path:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return file_path
        else:
            return content

    def _format_as_markdown(self, result: Dict[str, Any]) -> str:
        """Format result as markdown with hyperlink format info"""
        output = []

        output.append("# TRPG PDF 翻译结果\n")
        output.append(f"**源文件:** {result.get('pdf_path', 'N/A')}")
        output.append(f"**总页数:** {result.get('total_pages', 'N/A')}")
        output.append(f"**源语言:** {result['source_language']}")
        output.append(f"**目标语言:** {result['target_language']}")
        output.append(f"**模型:** {result['model']}")
        output.append(f"**窗口大小:** {result.get('window_size', 'N/A')} 段落")
        output.append(f"**窗口数量:** {result.get('num_windows', 'N/A')}")
        output.append(f"**重叠比率:** {result.get('overlap_ratio', 'N/A')}")
        output.append("")

        if result.get("translation_errors"):
            output.append("## 翻译警告\n")
            for error in result["translation_errors"]:
                output.append(f"- {error}")
            output.append("\n")

        output.append("## 译文\n")
        output.append(result.get("updated_translation", result.get("translated_text", "")))

        return "\n".join(output)


    def _format_as_bilingual(self, result: Dict[str, Any], use_llm_alignment: bool = True) -> str:
        """
        Format result as bilingual (side by side) markdown.

        Args:
            result: Translation result from translate_document_with_pdf
            use_llm_alignment: Whether to use LLM-based alignment (default: True)

        Returns:
            Bilingual aligned markdown text
        """
        output = []

        output.append("# 双语对照\n")
        output.append(f"**源文件:** {result.get('pdf_path', 'N/A')}")
        output.append(f"**总页数:** {result.get('total_pages', 'N/A')}")
        output.append(f"**源语言:** {result['source_language']}")
        output.append(f"**目标语言:** {result['target_language']}")
        output.append(f"**模型:** {result['model']}")
        output.append(f"**窗口大小:** {result.get('window_size', 'N/A')} 段落")
        output.append(f"**窗口数量:** {result.get('num_windows', 'N/A')}")
        output.append("")

        output.append("## 双语对照\n")
        output.append("")

        # Get original text from parse_result if available
        original_text = ""
        if result.get("parse_result"):
            original_text = result["parse_result"].get("full_text", "")

        translation_text = result.get("updated_translation", result.get("translated_text", ""))

        if not original_text or not translation_text:
            # Fallback to Chinese translation only
            output.append(translation_text)
            return "\n".join(output)

        # 如果没有开启大模型对齐功能，使用简单格式
        if not use_llm_alignment:
            output.append("## 译文\n")
            output.append(translation_text)
            output.append("\n## 原文\n")
            output.append("> " + original_text.replace("\n", "\n> "))
            return "\n".join(output)

        # Use LLM-based alignment
        try:
            aligned_text = self.client.align_bilingual_text(
                model=self.model,
                english_text=original_text,
                chinese_text=translation_text,
                stream_print=False,
                window_char_limit=4000,
                overlap_chars=500
            )
            output.append(aligned_text)
        except Exception as e:
            # Fallback to simple format if LLM alignment fails
            print(f"Warning: LLM-based alignment failed ({e}), using simple format")
            output.append("## 译文\n")
            output.append(translation_text)
            output.append("\n## 原文\n")
            output.append("> " + original_text.replace("\n", "\n> "))

        return "\n".join(output)

    def _save_glossary_to_file(self, glossary: Dict[str, str], file_path: str) -> bool:
        """
        保存译名表到文件

        Args:
            glossary: 译名表字典
            file_path: 文件路径

        Returns:
            True if saved successfully, False otherwise
        """
        if not PANDAS_AVAILABLE or not glossary:
            return False

        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            df = pd.DataFrame(list(glossary.items()), columns=["original", "translation"])
            df.to_parquet(path, index=False)
            return True
        except Exception as e:
            print(f"Warning: Failed to save glossary to {file_path}: {e}")
            return False

    def fix_markdown_hyperlink_spaces(self, text: str) -> str:
        """
        修复markdown超链接中的空格，将类似"[装甲洞穴熊](armored cave bear)"改为"[装甲洞穴熊](armored_cave_bear)"

        Args:
            text: 需要处理的文本

        Returns:
            处理后的文本
        """
        import re

        def replace_spaces(match):
            link_text = match.group(1)  # []中的文本
            link_target = match.group(2)  # ()中的URL/路径
            # 将空格替换为下划线
            fixed_target = link_target.replace(' ', '_')
            return f"[{link_text}]({fixed_target})"

        # 匹配markdown链接: [text](target)
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        return re.sub(pattern, replace_spaces, text)

