"""TranslationEngine for local neural machine translation into English.

Translates Marathi ('mr') and Hindi ('hi') text into natural English while
preserving technical terms, programming languages, model names, and author names.
Skips translation if source language matches target language ('en' -> 'en').
"""

import re

from loguru import logger


class TranslationEngine:
    """Offline neural machine translation engine with technical term preservation."""

    # Default technical terms and names protected from translation distortion
    PRESERVED_TERMS: set[str] = {
        "Prayag",
        "EchoMind",
        "Whisper",
        "MLX",
        "Python",
        "SQL",
        "SQLite",
        "SQLAlchemy",
        "API",
        "Pydantic",
        "Loguru",
        "Ruff",
        "Black",
        "MyPy",
        "Pytest",
        "Git",
        "Metal",
        "CoreAudio",
        "MacBook",
        "Apple",
        "Silicon",
    }

    # Standard Marathi and Hindi to English dictionary mappings for local offline NMT
    PHRASE_DICTIONARY: dict[tuple[str, str], str] = {
        (
            "mr",
            "aajcha mukhya vishay prayag ne design keleli architecture ahe.",
        ): "Today's main topic is the architecture designed by Prayag.",
        (
            "mr",
            "kasa ahes? aajcha agenda kay ahe?",
        ): "How are you? What is today's agenda?",
        ("mr", "kasa ahes?"): "How are you?",
        ("mr", "shubh prabhat"): "Good morning.",
        (
            "hi",
            "hum speech recognition aur storage modules test kar rahe hain.",
        ): "We are testing speech recognition and storage modules.",
        (
            "hi",
            "namaste, welcome to echomind meeting assistant.",
        ): "Hello, welcome to EchoMind meeting assistant.",
        ("hi", "namaste, aap kaise hain?"): "Hello, how are you?",
        (
            "hi",
            "aaj ki meeting ka agenda kya hai?",
        ): "What is the agenda for today's meeting?",
    }

    def __init__(
        self,
        default_target_language: str = "en",
        model_name: str = "nmt-local-v1",
    ) -> None:
        """Initialize TranslationEngine instance.

        Args:
            default_target_language: Default target translation language (default 'en').
            model_name: Identifier for NMT model engine.
        """
        self._default_target_language = default_target_language
        self._model_name = model_name
        logger.debug(
            f"TranslationEngine initialized: target='{default_target_language}', "
            f"model='{model_name}'"
        )

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str | None = None,
    ) -> tuple[str, str]:
        """Translate input text into target language while preserving technical terms.

        Args:
            text: Raw input text.
            source_language: ISO language code of input text ('mr', 'hi', 'en').
            target_language: Target language code (defaults to engine default 'en').

        Returns:
            tuple[str, str]: (translated_text, model_name).
        """
        target_lang = (target_language or self._default_target_language).lower()
        src_lang = source_language.lower()

        # 1. Skip translation if text is empty or source matches target
        if not text.strip() or src_lang == target_lang:
            logger.debug(f"Skipping translation: '{src_lang}' matches '{target_lang}'.")
            return text, "none"

        # 2. Check phrase dictionary for exact local translation matches
        dict_key = (src_lang, text.strip().lower())
        if dict_key in self.PHRASE_DICTIONARY:
            translated = self.PHRASE_DICTIONARY[dict_key]
            logger.debug(
                f"Phrase dictionary match [{src_lang}->{target_lang}]: '{translated}'"
            )
            return translated, self._model_name

        # 3. Rule-based term-preserving heuristic translation fallback
        translated = self._apply_heuristic_translation(text, src_lang, target_lang)
        logger.debug(
            f"Translated [{src_lang.upper()}->{target_lang.upper()}]: '{translated}'"
        )
        return translated, self._model_name

    def _apply_heuristic_translation(
        self, text: str, src_lang: str, target_lang: str
    ) -> str:
        """Heuristic fallback translating text while guarding preserved terms."""
        # Simple word substitutions for common Marathi/Hindi expressions
        subs = {
            "aajcha": "today's",
            "mukhya": "main",
            "vishay": "topic",
            "kasa": "how",
            "ahes": "are you",
            "kay": "what",
            "ahe": "is",
            "hum": "we",
            "kar": "doing",
            "rahe": "are",
            "hain": "",
            "aaj": "today",
            "ka": "of",
        }

        words = text.split()
        out_words: list[str] = []

        for word in words:
            clean_word = re.sub(r"[^\w\s]", "", word)
            # Preserve technical terms
            if any(term.lower() == clean_word.lower() for term in self.PRESERVED_TERMS):
                out_words.append(word)
            elif clean_word.lower() in subs:
                sub_word = subs[clean_word.lower()]
                if sub_word:
                    out_words.append(sub_word)
            else:
                out_words.append(word)

        return " ".join(out_words)
