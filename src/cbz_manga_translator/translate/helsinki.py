from __future__ import annotations

# Compatibility shim for older imports. The Hugging Face/Helsinki backend has
# been removed; this name now points to the offline Argos backend.
from cbz_manga_translator.translate.argos import ArgosTranslationError, ArgosTranslator

HelsinkiTranslator = ArgosTranslator

__all__ = ["ArgosTranslationError", "ArgosTranslator", "HelsinkiTranslator"]
