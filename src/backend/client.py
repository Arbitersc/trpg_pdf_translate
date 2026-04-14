"""
SiliconFlow API Client for LLM operations with streaming support
"""

from openai import OpenAI
import os
import re
from typing import List, Dict, Optional, Any, Iterator, Tuple
from pathlib import Path
import time
from functools import wraps

# Import shared configuration loader
from .config_loader import load_environment_config

# Load environment variables using shared loader
load_environment_config()


def retry_on_error(max_retries: int = 3, timeout_seconds: int = 60):
    """
    Decorator for retrying function calls on timeout or other errors

    Args:
        max_retries: Maximum number of retry attempts
        timeout_seconds: Timeout for each attempt
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    # Check if it's a timeout-related error
                    error_msg = str(e).lower()
                    is_timeout = 'timeout' in error_msg or 'timed out' in error_msg

                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}")
                        if is_timeout:
                            print(f"Timeout error - retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"All {max_retries + 1} attempts failed")
                        raise last_error
        return wrapper
    return decorator


class SiliconFlowClient:
    """Client for SiliconFlow API with streaming support"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize SiliconFlow client

        Args:
            api_key: API key (reads from SILICONFLOW_API_KEY env var if not provided)
            base_url: Base URL (reads from SILICONFLOW_BASE_URL env var if not provided)
        """
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.base_url = base_url or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY must be provided")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60.0  # Set a longer timeout for streaming
        )

    @staticmethod
    def _execute_stream_request(client: OpenAI, model: str, messages: List[Dict[str, str]],
                                 temperature: float, max_tokens: Optional[int],
                                 top_p: float, **kwargs):
        """
        Execute a streaming request with timeout - used internally for retry logic

        Args:
            client: OpenAI client instance with timeout configured
            model: Model identifier
            messages: Message list
            temperature: Temperature setting
            max_tokens: Max tokens
            top_p: Top_p setting
            **kwargs: Additional parameters

        Returns:
            Stream object
        """
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=True,
            **kwargs
        )

    def _stream_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.7,
        stream_print: bool = False,
        enable_thinking: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat completion request with streaming (60s timeout with 3 retries)

        Args:
            model: Model identifier (e.g., "Pro/moonshotai/Kimi-K2.5")
            messages: Message list with role and content
            temperature: Response randomness (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling threshold (0-1)
            stream_print: If True, stream and print the output in real-time
            enable_thinking: If True, enable reasoning_content extraction
            **kwargs: Additional parameters

        Returns:
            Response dictionary with content, reasoning_content and metadata
        """
        # Print messages and waiting indicator before making the request
        if stream_print:
            print("\n--- User Messages ---")
            for msg in messages:
                role = msg.get('role', 'unknown').upper()
                content = msg.get('content', '')
                print(f"[{role}]: {content[:200]}{'...' if len(content) > 200 else ''}")
            print("---------------------")
            print("  [Waiting for response...] ", end='', flush=True)

        # Streaming completion with 60s timeout and 3 retries
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                stream = self._execute_stream_request(
                    self.client, model, messages,
                    temperature, max_tokens, top_p, **kwargs
                )
                break  # Success exit the retry loop
            except Exception as e:
                if attempt < max_retries:
                    error_msg = str(e).lower()
                    is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
                    wait_time = 2 ** attempt  # Exponential backoff
                    if stream_print:
                        print(f"\rRequest failed (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__} - retrying... ", end='', flush=True)
                    time.sleep(wait_time)
                else:
                    if stream_print:
                        print(f"\rAll {max_retries + 1} attempts failed. Raising exception.")
                    raise

        content_buffer = []
        reasoning_content_buffer = []
        model_name = None
        finish_reason = None
        prompt_tokens = 0
        completion_tokens = 0
        first_content_received = False
        first_reasoning_received = False

        for chunk in stream:
            if not model_name and chunk.model:
                model_name = chunk.model

            delta = chunk.choices[0].delta

            # Accumulate reasoning content if enable_thinking
            if enable_thinking and hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                # Clear the loading indicator before printing first reasoning
                if stream_print and not first_reasoning_received:
                    print("\r" + " " * 30 + "\r", end='', flush=True)
                    print("\n--- Reasoning ---", end='', flush=True)
                    first_reasoning_received = True

                reasoning_content = delta.reasoning_content
                reasoning_content_buffer.append(reasoning_content)
                completion_tokens += 1

                # Print reasoning content in real-time if enable_thinking
                if stream_print:
                    if not hasattr(delta, 'content') or not delta.content:
                        # If there's no content in this chunk, newline before reasoning
                        pass
                    print(reasoning_content, end='', flush=True)

            # Accumulate content and print immediately when received
            if hasattr(delta, 'content') and delta.content:
                # Clear the loading indicator before printing first content
                if stream_print and not first_content_received:
                    print("\r" + " " * 30 + "\r", end='', flush=True)
                    # Print reasoning section heading if reasoning exists
                    if reasoning_content_buffer:
                        print("\n--- Reasoning ---\n" + "".join(reasoning_content_buffer) + "\n--- Response ---")
                    first_content_received = True

                content = delta.content
                content_buffer.append(content)
                completion_tokens += 1  # Rough token count estimation

                # Print content in real-time as soon as it's received
                if stream_print:
                    print(content, end='', flush=True)

            # Capture finish reason
            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

            # Get usage if available (some models return this in final chunk)
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = chunk.usage
                if isinstance(usage, dict):
                    if usage.get('prompt_tokens'):
                        prompt_tokens = usage['prompt_tokens']
                    if usage.get('completion_tokens'):
                        completion_tokens = usage['completion_tokens']
                else:
                    if hasattr(usage, 'prompt_tokens') and usage.prompt_tokens:
                        prompt_tokens = usage.prompt_tokens
                    if hasattr(usage, 'completion_tokens') and usage.completion_tokens:
                        completion_tokens = usage.completion_tokens

        # Add newline if we were printing
        if stream_print and content_buffer:
            print()

        full_content = "".join(content_buffer)
        full_reasoning_content = "".join(reasoning_content_buffer) if reasoning_content_buffer else None

        result = {
            "content": full_content,
            "model": model_name or model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "finish_reason": finish_reason
        }

        # Add reasoning_content if enable_thinking and it exists
        if enable_thinking and full_reasoning_content:
            result["reasoning_content"] = full_reasoning_content

        return result

    def extract_proper_nouns(
        self,
        model: str,
        text: str,
        context: Optional[str] = None,
        stream_print: bool = False
    ) -> List[str]:
        """
        Extract proper nouns from text using streaming

        Args:
            model: Model identifier
            text: Text to analyze
            context: Additional context about the document
            stream_print: If True, stream and print the output in real-time

        Returns:
            List of extracted proper nouns
        """
        system_prompt = """You are a specialized assistant for analyzing TRPG (tabletop role-playing game) documents.

Your task is to extract ALL proper nouns from the provided text. Be thorough and extract EVERY proper noun you find.

Proper nouns include:
1. Character names, including those with titles and honorifics (e.g., "Eliana", "Mayor Eliana", "Gorum", "Achaekek", "Samo", "Nahoa")
2. Place names of ALL types: cities, towns, villages, hamlets, forests, mountains, mountain ranges, rivers, lakes, caves, lairs, regions, nations, kingdoms, continents, and all other geographical features (e.g., "Golarion", "Lands of the Linnorm Kings")
3. God, deity, divine being, and religious entity names (e.g., "Devourer")
4. Race, species, creature, and monster names: BOTH specific named individuals AND their species types - this includes ALL fantasy races and creatures like "humanoids", "leshies", "Orc", "halfling", "elf", "aasimar", "aiuvarin", "tiefling", gnome, dwarf, etc. (e.g., extract "adamantine dragon" as creature type AND "Zikritrax" as individual)
5. Organization, faction, group, society, and guild names (e.g., "Red Mantis", "Pathfinder Society")
6. Spell, ability, power, skill, feat, trait, class feature, and supernatural ability names (e.g., "Divine power", "Mythic Calling")
7. Artifact, magical item, weapon, armor, gear, equipment, and relic names (e.g., "Godsrain", "Exemplar")
8. Book, publication, work, tome, and grimoire names (e.g., "Pathfinder Godsrain", "Divine Mysteries")

IMPORTANT GUIDELINES:
- Extract names WITH titles/honorifics AND without titles/honorifics as separate entries (e.g., both "Eliana" and "Mayor Eliana")
- Extract ALL types of geographical locations: towns, cities, forests, mountains, caves, lairs, regions, nations, etc.
- Extract named creatures individually AND their species type as separate entries when both are present (e.g., "adamantine dragon" as type, "Zikritrax" as individual)
- Extract ALL deity and god names
- CRITICAL for RACES/SPECIES: Extract ALL race, species, and creature type names even if they look like common nouns. In TRPG contexts, "humanoids", "leshies", "goblins", "orcs", etc. are proper noun categories representing fantasy races and MUST be extracted.
- Do NOT miss any proper nouns
- Do NOT extract common nouns like "town", "forest", "mountain", "priest", "guards" when they appear by themselves - only extract when they are part of a named entity or represent TRPG-specific terms

Return ONLY a JSON array of strings with no explanation.

Directly output the JSON array - do not add any reasoning or extra text."""

        user_message = f"""Extract proper nouns from the following text:

{text[:3000]}

"""
        if context:
            user_message += f"\nContext: {context}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self._stream_chat_completion(model, messages, temperature=0.3, max_tokens=2000, stream_print=stream_print)
        import json
        import re
        try:
            # Try to parse JSON directly
            content = response["content"].strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback: extract items manually
            content = response["content"]
            matches = re.findall(r'"([^"]+)"', content)
            return matches

    def generate_glossary(
        self,
        model: str,
        proper_nouns: List[str],
        target_language: str = "中文",
        context: Optional[str] = None,
        stream_print: bool = False,
        existing_glossary: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Generate translation glossary for proper nouns using streaming

        Args:
            model: Model identifier
            proper_nouns: List of proper nouns to translate
            target_language: Target language
            context: Additional context about the document
            stream_print: If True, stream and print the output in real-time
            existing_glossary: Existing glossary entries to use for partial word matching

        Returns:
            Dictionary mapping original terms to translations
        """
        if not proper_nouns:
            return {}

        # Filter out terms that already exist in the glossary - do not translate them again
        terms_to_translate = proper_nouns
        if existing_glossary:
            terms_to_translate = [term for term in proper_nouns if term not in existing_glossary]

            if not terms_to_translate:
                # All terms already exist in glossary, return existing translations
                return {term: existing_glossary.get(term, term) for term in proper_nouns}

            if stream_print:
                print(f"Filtering: {len(proper_nouns)} total terms, {len(terms_to_translate)} new terms to translate")
                if len(terms_to_translate) < len(proper_nouns):
                    print(f"  Skipping {len(proper_nouns) - len(terms_to_translate)} existing terms")

        # Build partial word matching instructions if existing glossary is provided
        partial_matching_instructions = ""
        if existing_glossary:
            # Find terms that might be partial matches
            partial_matches = self._find_partial_word_matches(terms_to_translate, existing_glossary)
            if partial_matches:
                partial_matching_instructions = f"""

PARTIAL WORD MATCHING GUIDELINES:
For terms that contain words already in the glossary, maintain consistency:
"""
                for term, matches in partial_matches.items():
                    for match_term, match_translation in matches:
                        partial_matching_instructions += f"- If '{term}' contains '{match_term}' (already translated as '{match_translation}'), ensure consistency\n"

        system_prompt = f"""You are a specialized TRPG translator. Your task is to translate proper nouns to {target_language}.

For each proper noun, provide the best translation considering:
- TRPG terminology conventions
- Consistency with fantasy/role-playing literature
- Pronunciation and meaning preservation
- Cultural appropriateness
- Translation consistency for similar terms (e.g., "Fire Storm" and "Fire Bolt" should both use "火焰"){partial_matching_instructions}

Return ONLY a JSON object with original terms as keys and translations as values.
Example: {{"Gorum": "戈鲁姆", "Achaekek": "阿卡凯克"}}

Directly output the JSON object - do not add any reasoning or extra text."""

        # Build term list - no longer limited to 50 for batch translation support
        # Format alphabetically sorted terms
        sorted_nouns = sorted(terms_to_translate)
        noun_list = "\n".join(f"- {noun}" for noun in sorted_nouns)

        user_message = f"""Translate the following {len(sorted_nouns)} proper nouns:\n\n{noun_list}\n\n"""

        if context:
            user_message += f"Context: {context}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Adjust max_tokens based on number of terms
        max_tokens = min(8000, len(terms_to_translate) * 20 + 2000)
        response = self._stream_chat_completion(model, messages, temperature=0.3, max_tokens=max_tokens, stream_print=stream_print)
        import json
        try:
            content = response["content"].strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            result = json.loads(content)
            # Merge new translations with existing glossary
            merged_result = {**existing_glossary} if existing_glossary else {}
            merged_result.update(result)
            # Ensure all original terms are in result, using existing translations where available
            return {noun: merged_result.get(noun, noun) for noun in proper_nouns}
        except json.JSONDecodeError:
            # Return empty mapping on error
            return {}

    def _find_partial_word_matches(
        self,
        terms: List[str],
        existing_glossary: Dict[str, str]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        Find partial word matches between new terms and existing glossary

        For example, if existing glossary has "Bear" -> "罴",
        and new term is "Golden Bear", this will detect the match

        Args:
            terms: List of new terms to translate
            existing_glossary: Existing glossary with term->translation mapping

        Returns:
            Dictionary mapping each term to list of (matched_term, translation) tuples
        """
        import re

        partial_matches = {}

        # Create a list of existing glossary terms sorted by length (longest first)
        # to prioritize longer matches first
        existing_terms = sorted(existing_glossary.keys(), key=len, reverse=True)

        for term in terms:
            term_lower = term.lower()
            matches = []

            for existing_term in existing_terms:
                existing_term_lower = existing_term.lower()

                # Check if existing term appears as a word in the new term
                # Use word boundary matching to avoid partial matches like "bear" in "bearing"
                pattern = r'\b' + re.escape(existing_term_lower) + r'\b'
                if re.search(pattern, term_lower):
                    # Found a partial match
                    matches.append((existing_term, existing_glossary[existing_term]))

            if matches:
                partial_matches[term] = matches

        return partial_matches

    def translate_text(
        self,
        model: str,
        text: str,
        source_language: str = "English",
        target_language: str = "中文",
        glossary: Optional[Dict[str, str]] = None,
        context: Optional[str] = None,
        stream_print: bool = False,
        detected_terms: Optional[List[str]] = None,
        use_hyperlink_format: bool = False
    ) -> str:
        """
        Translate text using LLM with streaming

        Args:
            model: Model identifier
            text: Text to translate
            source_language: Source language
            target_language: Target language
            glossary: Translation glossary with term->translation mapping
            context: Additional context about the document
            stream_print: If True, stream and print the output in real-time
            detected_terms: Glossary terms detected in the current text chunk
            use_hyperlink_format: If True, format proper nouns as markdown hyperlinks

        Returns:
            Translated text
        """
        import re

        # Detect glossary terms in the text if not provided
        if glossary and detected_terms is None:
            detected_terms = self._detect_glossary_terms_in_text(text, glossary)

        # Build glossary instruction
        glossary_instruction = ""
        if glossary:
            # Include all glossary terms
            glossary_items = [f"- {orig}: {trans}" for orig, trans in glossary.items() if trans and trans != orig]
            if glossary_items:
                glossary_instruction = f"\n\nGLOSSARY - Use these translations for proper nouns:\n" + "\n".join(glossary_items)

        # Add detected terms information
        detected_terms_instruction = ""
        if detected_terms:
            detected_items = []
            for term in detected_terms:
                if term in glossary and glossary[term] != term:
                    detected_items.append(f"- {term} (use: {glossary[term]})")
            if detected_items:
                detected_terms_instruction = f"\n\nPROPER NOUNS FOUND IN THIS TEXT:\n" + "\n".join(detected_items)

        # Build hyperlink format instruction
        hyperlink_instruction = ""
        if use_hyperlink_format and glossary:
            hyperlink_instruction = """
IMPORTANT OUTPUT FORMAT: For all proper nouns from the glossary, output them in markdown hyperlink format: [Translation](Original).
Example: If "Gorum" translates to "戈鲁姆", use "[戈鲁姆](Gorum)" instead of just "戈鲁姆".
"""

        system_prompt = f"""You are a professional TRPG document translator.

Translate the provided text from {source_language} to {target_language}.
Maintain proper formatting (headings, lists, markdown structure).
Capture the epic and immersive tone typical of TRPG literature.{glossary_instruction}{detected_terms_instruction}{hyperlink_instruction}

Return only the translated text with no explanations or notes.

Directly translate - do not show any thinking process or reasoning."""

        user_message = f"""Translate the following text:\n\n{text}"""

        if context:
            user_message = f"""Context: {context}\n\n{user_message}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Stream to handle long translations without timeout
        response = self._stream_chat_completion(
            model,
            messages,
            temperature=0.4,
            max_tokens=min(4000, len(text) * 2 + 500),
            stream_print=stream_print
        )

        return response["content"]

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
        import re
        found_terms = []
        text_lower = text.lower()

        for term in glossary.keys():
            # Use word boundary matching to avoid partial matches
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                found_terms.append(term)

        return found_terms

    def update_translation_with_glossary(
        self,
        model: str,
        translated_text: str,
        glossary: Dict[str, str],
        context: Optional[str] = None,
        stream_print: bool = False
    ) -> str:
        """
        Update translated text to use glossary terms using streaming

        Args:
            model: Model identifier
            translated_text: Previously translated text
            glossary: Translation glossary with term->translation mapping
            context: Additional context about the document
            stream_print: If True, stream and print the output in real-time

        Returns:
            Updated translated text
        """
        glossary_items = [f"- {orig}: {trans}" for orig, trans in glossary.items() if trans and trans != orig]
        if not glossary_items:
            return translated_text

        glossary_text = "\n".join(glossary_items)

        system_prompt = f"""You are a TRPG translation post-processor.

Update the provided translated text to ensure consistent use of the glossary terms below.

REPLACE any alternative translations of the proper nouns with the specified translations.
MAINTAIN the overall style, flow, and formatting of the original translation.

GLOSSARY:
{glossary_text}

Return only the updated translated text.

Directly output - do not show any thinking process or reasoning."""

        user_message = f"Update this translation:\n\n{translated_text}"

        if context:
            user_message = f"Context: {context}\n\n{user_message}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self._stream_chat_completion(
            model,
            messages,
            temperature=0.2,
            max_tokens=min(4000, len(translated_text) * 2 + 500),
            stream_print=stream_print
        )

        updated_text = response["content"]

        # Post-process: Fix markdown hyperlinks (replace spaces with underscores in URLs)
        def fix_link(match):
            """Replace spaces with underscores in the link target"""
            link_text = match.group(1)  # The text inside []
            link_target = match.group(2)  # The URL/path inside ()
            fixed_target = link_target.replace(' ', '_')
            return f"[{link_text}]({fixed_target})"

        # Match markdown links: [text](target) and fix spaces in the target
        updated_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', fix_link, updated_text)

        return updated_text

    def optimize_pdf_text_formatting(
        self,
        model: str,
        extracted_text: str,
        context: Optional[str] = None,
        stream_print: bool = False,
        window_char_limit: int = 8000,
        overlap_paragraphs: int = 2
    ) -> str:
        """
        Optimize PDF extracted text formatting using LLM with sliding window

        This method analyzes and fixes common PDF text extraction issues:
        - Merging paragraphs that were incorrectly split
        - Fixing capitalization issues (proper names, sentence beginnings)
        - Removing extra whitespace
        - Fixing broken words (hyphenated line breaks)
        - Restoring proper paragraph structure

        Uses sliding window approach to handle long texts that exceed model context limits.

        Args:
            model: Model identifier
            extracted_text: Text extracted from PDF that may have formatting issues
            context: Additional context about the document (e.g., document type, content summary)
            stream_print: If True, stream and print the output in real-time
            window_char_limit: Maximum characters per window (default: 8000)
            overlap_paragraphs: Number of paragraphs to overlap between windows (default: 2)

        Returns:
            Formatting-optimized text
        """
        import re

        # Helper function to split into paragraphs
        def split_into_paragraphs(text: str) -> List[str]:
            paragraphs = re.split(r'\n\n+|(?=^#{1,6}\s)', text, flags=re.MULTILINE)
            return [p.strip() for p in paragraphs if p.strip()]

        # Helper function to create sliding windows
        def create_sliding_windows(text: str, window_char_limit: int, overlap_paragraphs: int):
            units = split_into_paragraphs(text)
            if not units:
                return []

            windows = []
            i = 0
            while i < len(units):
                window_units = []
                total_chars = 0

                for j in range(i, len(units)):
                    unit = units[j]
                    unit_len = len(unit)
                    separator_len = 2 if window_units else 0
                    if window_units:
                        total_chars += separator_len

                    if total_chars + unit_len > window_char_limit and window_units:
                        break

                    window_units.append(unit)
                    total_chars += unit_len

                if not window_units:
                    window_units = [units[i]]
                    j = i

                window_text = "\n\n".join(window_units)
                end_idx = j
                windows.append((window_text, i, end_idx))

                window_len = len(window_units)
                step_size = window_len - overlap_paragraphs
                if step_size <= 1:
                    step_size = 1

                i += step_size
                if i >= len(units):
                    break

            return windows

        # Helper function to merge windows
        def merge_windows(windows, translations, overlap_paragraphs: int) -> str:
            if len(windows) != len(translations):
                raise ValueError(f"Number of windows doesn't match translations")

            if not windows:
                return ""

            units = []

            for idx, (window_text, start, end) in enumerate(windows):
                window_units = split_into_paragraphs(translations[idx])

                for unit_idx, unit in enumerate(window_units):
                    absolute_idx = start + unit_idx
                    is_overlap = unit_idx < overlap_paragraphs and idx > 0

                    if not is_overlap or idx == len(windows) - 1:
                        while len(units) <= absolute_idx:
                            units.append(None)
                        if units[absolute_idx] is None:
                            units[absolute_idx] = unit

            units = [u for u in units if u is not None]
            return "\n\n".join(units)

        system_prompt = """You are a specialized text formatting optimizer for PDF extracted text.

Your task is to analyze and fix common PDF text extraction issues:

1. **Merge incorrectly split paragraphs**: PDF extraction often breaks paragraphs at line breaks. Rejoin sentences that clearly belong together.

2. **Fix capitalization issues**:
   - Ensure proper nouns (names, places, titles) have correct capitalization
   - Fix lowercase letters at the start of sentences
   - Maintain all-caps for emphasis/acronyms if used

3. **Remove excessive whitespace**: Remove extra blank lines and spaces, but keep logical paragraph breaks.

4. **Fix broken words**: Words split by hyphens at line breaks should be rejoined if they form valid English words.

5. **Restore proper paragraph structure**: Preserve logical paragraph breaks (between distinct topics/sections) while removing arbitrary line breaks.

IMPORTANT GUIDELINES:
- Preserve ALL the original content - do not add or remove information
- Maintain the original structure and flow of the text
- Only fix formatting issues, do not rewrite or rephrase content
- Preserve special formatting like bullet points, numbered lists, and headings marked with # or similar markers
- If the text is from a TRPG document, preserve game-specific terminology and formatting
- DO NOT modify or "correct" spelling - what may appear to be misspellings could be proper names, fantasy术语, or game-specific terms. Keep all spellings exactly as they appear in the original text.

Return only the formatted text with no explanations.

Directly output the formatted text - do not add any reasoning or extra text."""

        context_prefix = f"Context: {context}\n\n" if context else ""

        # Create sliding windows
        windows = create_sliding_windows(extracted_text, window_char_limit, overlap_paragraphs)

        if not windows:
            return extracted_text

        if stream_print:
            print(f"  Processing text in {len(windows)} windows (max {window_char_limit} chars each, {overlap_paragraphs} paragraph overlap)...")

        translations = []
        for idx, (window_text, start, end) in enumerate(windows):
            # 解析段落信息（无论是否stream_print都需要）
            paragraphs = split_into_paragraphs(window_text)

            if stream_print:
                # 显示详细的段落信息
                first_para_preview = paragraphs[0][:100] + "..." if len(paragraphs[0]) > 100 else paragraphs[0]
                last_para_preview = paragraphs[-1][:100] + "..." if len(paragraphs[-1]) > 100 else paragraphs[-1]

                print(f"    Window {idx + 1}/{len(windows)} (paragraphs {start + 1}-{end}, {len(paragraphs)} paragraphs, {len(window_text)} chars)...")
                print(f"      First paragraph: {first_para_preview}")
                print(f"      Last paragraph: {last_para_preview}")
                print(f"      Processing...", end='', flush=True)

            user_message = f"""{context_prefix}Optimize the formatting of this PDF extracted text:\n\n{window_text}"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            max_tokens = min(8000, len(window_text) * 2 + 500)

            response = self._stream_chat_completion(
                model,
                messages,
                temperature=0.1,
                max_tokens=max_tokens,
                stream_print=False  # Disable stream_print for each window to avoid confusion
            )

            translations.append(response["content"])

            if stream_print:
                print(" ✓", flush=True)
                print(f"      ✓ Optimized {len(paragraphs)} paragraphs")

        # Merge all windows
        if stream_print:
            print(f"  Merging {len(translations)} optimized windows...")

        merged_text = merge_windows(windows, translations, overlap_paragraphs)

        if stream_print:
            print(f"  ✓ Formatting optimization completed")

        return merged_text

    def align_bilingual_text(
        self,
        model: str,
        english_text: str,
        chinese_text: str,
        stream_print: bool = False,
        window_char_limit: int = 4000,
        overlap_chars: int = 500
    ) -> str:
        """
        Align English and Chinese text using LLM with sliding window approach

        This method creates a bilingual output with:
        - Headings merged as "中文 (English)"
        - Content paragraphs showing English (blockquote) then Chinese
        - Tables merged with Chinese heading and row-by-row alignment
        - Sliding window for long texts (max 4000 chars per window, 500 char overlap)

        Strategy:
        1. Extract keywords from Chinese text as anchors
        2. Find corresponding English sections based on anchors
        3. For each section, ask LLM to create bilingual output
        4. Merge all sections

        Args:
            model: Model identifier
            english_text: Original English text
            chinese_text: Translated Chinese text
            stream_print: If True, stream and print LLM output in real-time
            window_char_limit: Maximum characters per window (default: 4000)
            overlap_chars: Characters to overlap between windows (default: 500)

        Returns:
            Bilingual aligned text
        """
        import re

        # Split texts into paragraphs
        def split_paragraphs(text):
            paragraphs = re.split(r'\n\n+', text.strip())
            return [p.strip() for p in paragraphs if p.strip()]

        en_paragraphs = split_paragraphs(english_text)
        cn_paragraphs = split_paragraphs(chinese_text)

        if not en_paragraphs or not cn_paragraphs:
            return chinese_text  # Fallback to Chinese only

        # Extract keywords from Chinese text for anchoring
        def extract_keywords(text):
            # Extract proper nouns, capitalized words, numbers, markdown links
            keywords = set()
            # Markdown links [text](url)
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
            for zh, en in links:
                keywords.add(en)  # Add the English term from the link
            # Capitalized sequences (potential proper nouns)
            capitalized = re.findall(r'\b[A-Z][a-zA-Z]+\b', text)
            keywords.update(capitalized)
            # Numbers with dice notation like 2d10+4, etc.
            dice = re.findall(r'\d+d\d+\+?\d*', text)
            keywords.update(dice)
            # Words in quotes (often keywords)
            quoted = re.findall(r'"([^"]+)"', text)
            keywords.update(quoted)

            return list(keywords)[:50]  # Limit to top 50 keywords

        # Create sliding windows for long texts
        def create_windows(text, char_limit, overlap):
            if len(text) <= char_limit:
                return [(text, 0, len(text))]

            windows = []
            start = 0
            while start < len(text):
                end = min(start + char_limit, len(text))
                window_text = text[start:end]

                # Find a good break point (end of a paragraph) near the end
                if end < len(text):
                    last_paragraph_end = window_text.rfind('\n\n')
                    if last_paragraph_end > char_limit - 500:  # Don't go back too far
                        end = start + last_paragraph_end + 2
                        window_text = text[start:end]

                windows.append((window_text, start, end))

                start = end - overlap if end < len(text) else len(text)

            return windows

        system_prompt = """You are a specialized TRPG bilingual text aligner.

Your task is to create a bilingual (English/Chinese) output from the provided texts.

OUTPUT FORMAT RULES:
1. **Headings**: Merge heading lines as "中文标题 (English Title)"
   Example: ## 披甲洞穴熊 (ARMORED CAVE BEAR)

2. **Content paragraphs**: Output as blockquote for English, plain text for Chinese
   > First English paragraph.

   Corresponding Chinese paragraph.

3. **Tables/Stats**: Merge table headers and align rows
   Example:
   # [生物](creatures) 9

   [察觉](Perception) $+17$；[昏暗视觉](low-light vision)...

4. **Lists**: Align list items by position
   > English list item 1

   Chinese list item 1

5. **Markdown formatting**: Preserve all markdown formatting, links, and special notation

6. **Consistency**: Match the structure of both texts while maintaining readability

IMPORTANT:
- Don't reorder or restructure content
- Maintain the flow and logic of both texts
- Use blockquote (>) for English content
- Use plain text for Chinese content
- Keep spacing clear between English and Chinese pairs

Return only the bilingual aligned markdown with no explanations."""

        # If text is short enough, process in one go
        if len(chinese_text) <= window_char_limit:
            # Build combined prompt
            combined_message = f"""Create a bilingual alignment for these texts:

ENGLISH TEXT:
{english_text}

CHINESE TEXT:
{chinese_text}

Generate the bilingual output following the format rules."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_message}
            ]

            max_tokens = min(8000, len(chinese_text) * 3 + 1000)
            response = self._stream_chat_completion(
                model,
                messages,
                temperature=0.2,
                max_tokens=max_tokens,
                stream_print=stream_print
            )

            return response["content"]

        # Long text: use sliding window approach
        if stream_print:
            print(f"  Aligning bilingual text using sliding windows (max {window_char_limit} chars, {overlap_chars} overlap)...")

        cn_windows = create_windows(chinese_text, window_char_limit, overlap_chars)
        aligned_sections = []

        for idx, (cn_window, start, end) in enumerate(cn_windows):
            if stream_print:
                print(f"    Processing window {idx + 1}/{len(cn_windows)} (chars {start}-{end})...", end='', flush=True)

            # Find corresponding English text
            # Use keyword matching to find approximate English section
            cn_keywords = extract_keywords(cn_window)

            # Find English windows containing these keywords
            en_start = 0
            en_end = len(english_text)

            if cn_keywords:
                found_positions = []
                for keyword in cn_keywords:
                    keyword_lower = keyword.lower()
                    pos = english_text.lower().find(keyword_lower)
                    if pos >= 0:
                        found_positions.append(pos)

                if found_positions:
                    min_pos = min(found_positions)
                    max_pos = max(found_positions)

                    # Add some padding
                    pad = min(1000, min_pos)
                    en_start = max(0, min_pos - pad)
                    en_end = min(len(english_text), max_pos + window_char_limit)

            en_window = english_text[en_start:en_end]

            # Build prompt for this window
            window_message = f"""Create a bilingual alignment for this section:

ENGLISH SECTION (partial, context: chars {en_start}-{en_end}):
{en_window}

CHINESE SECTION (chars {start}-{end}):
{cn_window}

Generate the bilingual output following the format rules. Only output the aligned content for this section."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": window_message}
            ]

            max_tokens = min(8000, len(cn_window) * 3 + 1000)
            response = self._stream_chat_completion(
                model,
                messages,
                temperature=0.2,
                max_tokens=max_tokens,
                stream_print=False  # Disable stream_print for individual windows
            )

            aligned_sections.append(response["content"])

            if stream_print:
                print(" ✓", flush=True)

        # Join all sections with proper spacing
        if stream_print:
            print(f"  Merging {len(aligned_sections)} aligned sections...")

        # Merge sections, handling overlaps
        merged_result = ""
        for i, section in enumerate(aligned_sections):
            if i > 0:
                # Try to avoid duplication at boundaries
                section = section.strip()
                # Skip if it starts with a common header that was likely duplicated
                first_line = section.split('\n')[0] if '\n' in section else section
                if first_line.startswith('#') and first_line in merged_result:
                    # Skip first line if it's a duplicate heading
                    first_newline = section.find('\n')
                    if first_newline > 0:
                        section = section[first_newline + 1:].strip()

            merged_result += "\n\n" + section if merged_result else section

        if stream_print:
            print(f"  ✓ Bilingual alignment completed")

        return merged_result
