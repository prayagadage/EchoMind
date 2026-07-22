"""Multilingual Translation Module for EchoMind.

Provides local neural machine translation into English, technical term preservation,
TranslationEvent dispatching, and independent event worker orchestration.
"""

from modules.translation.engine import TranslationEngine
from modules.translation.service import TranslationService
from modules.translation.translation_event import TranslationEvent

__all__ = [
    "TranslationEvent",
    "TranslationEngine",
    "TranslationService",
]
