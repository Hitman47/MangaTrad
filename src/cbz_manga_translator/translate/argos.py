from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cbz_manga_translator.core.editing import is_translation_protected
from cbz_manga_translator.core.models import OcrBlock, SourceLang
from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation
from cbz_manga_translator.translate.builtin_glossary import BUILTIN_MANGA_GLOSSARY
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer
from cbz_manga_translator.translate.source_quality_gate import SourceQualityGate

_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_WORD_CHARS_RE = re.compile(r"[A-Za-z0-9]")
_JAPANESE_CHAR_RE = re.compile(r"[\u3041-\u309f\u30a0-\u30ff\u3400-\u9fff]")
_LOW_VALUE_JA_SYMBOL_RE = re.compile(r"^[\s@#=_~{}<>|\\/\[\]()`'\".,:;!?・…。、「」『』（）\-]+$")
_JA_NUMERIC_AMOUNT_RE = re.compile(r"[0-9０-９].*[万億円千百]")


class ArgosTranslationError(RuntimeError):
    """Raised when an offline Argos translation package is missing or unusable."""


@dataclass(slots=True)
class _TermRule:
    source: str
    target: str
    placeholder: str


@dataclass(slots=True)
class _PreparedText:
    text: str
    term_rules: list[_TermRule]
    corrected_text: str = ""
    normalized_source_text: str = ""
    override_translation_fr: str = ""

    def restore(self, translated: str) -> str:
        restored = translated
        for rule in self.term_rules:
            restored = re.sub(re.escape(rule.placeholder), rule.target, restored, flags=re.IGNORECASE)
            restored = re.sub(re.escape(rule.placeholder.lower()), rule.target, restored, flags=re.IGNORECASE)
        return _SPACE_BEFORE_PUNCT_RE.sub(r"\1", " ".join(restored.strip().split()))


class ArgosTranslator:
    """Offline Argos Translate backend.

    No Hugging Face/Transformers model is loaded here. Argos uses locally installed
    ``.argosmodel`` packages. For Japanese -> French, Argos may pivot through English
    when ``ja -> fr`` is not installed but ``ja -> en`` and ``en -> fr`` are.
    """

    TARGET_LANG = "fr"
    PIVOT_LANG = "en"

    def __init__(self) -> None:
        self._translation_cache: dict[tuple[str, str, bool], Any] = {}
        self._source_quality_gate = SourceQualityGate()

    @staticmethod
    def cuda_available() -> bool:
        """Return whether CUDA is visible for optional Argos/CTranslate2 GPU mode.

        Argos GPU support is controlled through ``ARGOS_DEVICE_TYPE`` and depends on
        the installed CTranslate2/driver stack. We use PyTorch only as a pragmatic
        CUDA visibility check because the project already depends on it for OCR.
        """
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    @staticmethod
    def _configure_device(use_gpu: bool) -> None:
        if use_gpu:
            os.environ["ARGOS_DEVICE_TYPE"] = "cuda"
        else:
            os.environ["ARGOS_DEVICE_TYPE"] = "cpu"
        try:
            import argostranslate.settings as argos_settings

            # Avoid implicit Stanza downloads at translation time. MiniSBD ships
            # with/cacheable local models and keeps MangaTrad's batch workflow
            # local after the initial dependency/model setup.
            argos_settings.chunk_type = argos_settings.ChunkType.MINISBD
            argos_settings.device = "cuda" if use_gpu else "cpu"
        except Exception:
            pass
        ArgosTranslator._clear_argos_language_cache()

    @staticmethod
    def _clear_argos_language_cache() -> None:
        try:
            import argostranslate.translate as argos_translate

            cache_clear = getattr(argos_translate.get_installed_languages, "cache_clear", None)
            if callable(cache_clear):
                cache_clear()
            installed_translates = getattr(argos_translate, "installed_translates", None)
            if isinstance(installed_translates, list):
                installed_translates.clear()
        except Exception:
            return

    @staticmethod
    def _is_cuda_out_of_memory(exc: Exception) -> bool:
        message = str(exc).lower()
        return "cuda" in message and ("out of memory" in message or "memoryallocation" in message)

    @staticmethod
    def _clear_cuda_cache() -> None:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            return

    @staticmethod
    def _argostranslate_modules() -> tuple[Any, Any]:
        try:
            import argostranslate.package as argos_package
            import argostranslate.translate as argos_translate
        except Exception as exc:  # pragma: no cover - depends on optional package installation
            raise ArgosTranslationError(
                "Argos Translate n'est pas installé. Installe-le avec `pip install argostranslate`, "
                "puis installe les modèles .argosmodel nécessaires."
            ) from exc
        return argos_package, argos_translate

    @staticmethod
    def install_package_file(path: str | Path) -> None:
        package_path = Path(path)
        if not package_path.exists():
            raise ArgosTranslationError(f"Package Argos introuvable: {package_path}")
        if package_path.suffix.lower() != ".argosmodel":
            raise ArgosTranslationError(f"Fichier .argosmodel attendu: {package_path}")
        argos_package, _ = ArgosTranslator._argostranslate_modules()
        argos_package.install_from_path(str(package_path))

    @staticmethod
    def available_packages() -> list[Any]:
        """Return Argos package-index entries, updating the local index first.

        This contacts Argos' package index, not Hugging Face. It is used only by
        the explicit model-management CLI, never silently during translation.
        """
        argos_package, _ = ArgosTranslator._argostranslate_modules()
        argos_package.update_package_index()
        return list(argos_package.get_available_packages())

    @staticmethod
    def install_package_from_index(from_code: str, to_code: str) -> bool:
        """Download and install one Argos package pair from the Argos index.

        Returns False when the requested pair is not present in Argos' index.
        """
        normalized_from = from_code.strip().lower()
        normalized_to = to_code.strip().lower()
        for package in ArgosTranslator.available_packages():
            if str(getattr(package, "from_code", "")).lower() == normalized_from and str(getattr(package, "to_code", "")).lower() == normalized_to:
                package_path = package.download()
                argos_package, _ = ArgosTranslator._argostranslate_modules()
                argos_package.install_from_path(package_path)
                return True
        return False

    @classmethod
    def bootstrap_basic_packages(cls) -> list[tuple[str, str, bool]]:
        """Install the minimal local pairs for EN→FR and JP→FR via pivot.

        Argos' public index commonly exposes ja→en and en→fr, while ja→fr may
        be absent. We still try ja→fr, but ja→en + en→fr is sufficient for the
        app's Japanese pivot path.
        """
        requested = [("en", "fr"), ("ja", "en"), ("ja", "fr")]
        results: list[tuple[str, str, bool]] = []
        for from_code, to_code in requested:
            installed = cls.install_package_from_index(from_code, to_code)
            results.append((from_code, to_code, installed))
        return results

    @staticmethod
    def installed_pairs() -> list[tuple[str, str]]:
        """Return Argos translation pairs usable by the current installation.

        Argos does not expose a stable public ``language.translations`` attribute
        across versions. The reliable API is ``source.get_translation(target)``.
        We therefore probe each installed language pair. This also reports pairs
        that Argos can satisfy through its own translation object resolution.
        """
        ArgosTranslator._configure_device(use_gpu=False)
        _, argos_translate = ArgosTranslator._argostranslate_modules()
        languages = list(argos_translate.get_installed_languages())
        pairs: set[tuple[str, str]] = set()
        for source in languages:
            source_code = str(getattr(source, "code", ""))
            if not source_code:
                continue
            for target in languages:
                target_code = str(getattr(target, "code", ""))
                if not target_code or source_code == target_code:
                    continue
                try:
                    translation = source.get_translation(target)
                except Exception:
                    translation = None
                if translation is not None:
                    pairs.add((source_code, target_code))
        return sorted(pairs)

    @classmethod
    def can_translate_to_french(cls, source_lang: SourceLang) -> tuple[bool, str]:
        """Return whether the local Argos installation can translate source_lang -> fr."""
        pairs = set(cls.installed_pairs())
        if (source_lang, cls.TARGET_LANG) in pairs:
            return True, f"{source_lang}->fr direct installé"
        if source_lang != cls.PIVOT_LANG and (source_lang, cls.PIVOT_LANG) in pairs and (cls.PIVOT_LANG, cls.TARGET_LANG) in pairs:
            return True, f"{source_lang}->{cls.PIVOT_LANG}->fr via pivot installé"
        if source_lang == cls.PIVOT_LANG and (cls.PIVOT_LANG, cls.TARGET_LANG) in pairs:
            return True, "en->fr installé"
        installed = ", ".join(f"{src}->{dst}" for src, dst in sorted(pairs)) or "aucune paire"
        return False, f"modèle manquant pour {source_lang}->fr; installés: {installed}"

    @classmethod
    def local_translation_status(cls) -> list[tuple[str, bool, str]]:
        """Return required local model status for the GUI/runtime diagnostic."""
        statuses: list[tuple[str, bool, str]] = []
        for source_lang in ("en", "ja"):
            ok, detail = cls.can_translate_to_french(source_lang)  # type: ignore[arg-type]
            statuses.append((f"Argos {source_lang}->fr", ok, detail))
        return statuses

    @staticmethod
    def _translation_between(from_code: str, to_code: str) -> Any | None:
        _, argos_translate = ArgosTranslator._argostranslate_modules()
        languages = {str(language.code): language for language in argos_translate.get_installed_languages()}
        source = languages.get(from_code)
        target = languages.get(to_code)
        if source is None or target is None:
            return None
        try:
            return source.get_translation(target)
        except Exception:
            return None

    def _translation_chain(self, source_lang: SourceLang, *, use_gpu: bool) -> list[Any]:
        self._configure_device(use_gpu)
        cache_key = (source_lang, self.TARGET_LANG, bool(use_gpu))
        cached = self._translation_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        direct = self._translation_between(source_lang, self.TARGET_LANG)
        if direct is not None:
            chain = [direct]
            self._translation_cache[cache_key] = tuple(chain)
            return chain

        if source_lang != self.PIVOT_LANG:
            first = self._translation_between(source_lang, self.PIVOT_LANG)
            second = self._translation_between(self.PIVOT_LANG, self.TARGET_LANG)
            if first is not None and second is not None:
                chain = [first, second]
                self._translation_cache[cache_key] = tuple(chain)
                return chain

        installed = ", ".join(f"{src}->{dst}" for src, dst in self.installed_pairs()) or "aucune paire installée"
        if source_lang == "ja":
            required = "ja->fr direct, ou ja->en + en->fr"
        else:
            required = f"{source_lang}->fr"
        raise ArgosTranslationError(
            f"Aucun modèle Argos local utilisable pour {source_lang}->fr. "
            f"Installe un package .argosmodel pour {required}. Paires installées: {installed}."
        )

    def preload(self, source_lang: SourceLang, *, use_gpu: bool = False) -> None:
        self._translation_chain(source_lang, use_gpu=use_gpu)

    @staticmethod
    def _raw_user_entries(raw_terms: str | None) -> list[tuple[str, str]]:
        if not raw_terms:
            return []
        entries = [entry.strip() for entry in re.split(r"[,;\n]", raw_terms) if entry.strip()]
        parsed: list[tuple[str, str]] = []
        for entry in entries:
            if "=>" in entry:
                source, target = entry.split("=>", 1)
            elif "=" in entry:
                source, target = entry.split("=", 1)
            else:
                source, target = entry, entry
            source = source.strip()
            target = target.strip()
            if source and target:
                parsed.append((source, target))
        return parsed

    @classmethod
    def _parse_term_rules(cls, raw_terms: str | None, *, use_builtin_glossary: bool = True) -> list[_TermRule]:
        entries: list[tuple[str, str]] = []
        if use_builtin_glossary:
            entries.extend(BUILTIN_MANGA_GLOSSARY)
        entries.extend(cls._raw_user_entries(raw_terms))

        deduped: dict[str, tuple[str, str]] = {}
        for source, target in entries:
            deduped[source.casefold()] = (source, target)

        rules: list[_TermRule] = []
        for index, (source, target) in enumerate(deduped.values()):
            rules.append(_TermRule(source=source, target=target, placeholder=f"MKTERM{index:03d}TOKEN"))
        return sorted(rules, key=lambda rule: len(rule.source), reverse=True)

    @staticmethod
    def _is_latin_word_like(value: str) -> bool:
        return bool(value and all(_WORD_CHARS_RE.fullmatch(char) for char in value if char.strip()))

    @classmethod
    def _term_pattern(cls, term: str) -> re.Pattern[str]:
        escaped = re.escape(term)
        if cls._is_latin_word_like(term):
            return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", flags=re.IGNORECASE)
        return re.compile(escaped, flags=re.IGNORECASE)

    @classmethod
    def _apply_term_placeholders(cls, text: str, raw_terms: str | None, *, use_builtin_glossary: bool = True) -> _PreparedText:
        rules = cls._parse_term_rules(raw_terms, use_builtin_glossary=use_builtin_glossary)
        prepared = text
        used_rules: list[_TermRule] = []
        for rule in rules:
            pattern = cls._term_pattern(rule.source)
            prepared, count = pattern.subn(rule.placeholder, prepared)
            if count:
                used_rules.append(rule)
        return _PreparedText(text=prepared, term_rules=used_rules)

    @classmethod
    def _prepare_source_text(
        cls,
        text: str,
        source_lang: SourceLang,
        *,
        raw_terms: str | None = None,
        normalize_english: bool = True,
        use_builtin_glossary: bool = True,
    ) -> _PreparedText:
        if source_lang == "en":
            cleaned_text = normalize_ocr_text_for_translation(text)
            dialogue = EnglishDialogueNormalizer.prepare(cleaned_text, normalize_english=normalize_english)
            prepared = cls._apply_term_placeholders(dialogue.normalized_text, raw_terms, use_builtin_glossary=use_builtin_glossary)
            prepared.corrected_text = dialogue.corrected_text
            prepared.normalized_source_text = dialogue.normalized_text
            prepared.override_translation_fr = dialogue.override_translation_fr
            return prepared
        normalized = " ".join(text.strip().split())
        prepared = cls._apply_term_placeholders(normalized, raw_terms, use_builtin_glossary=use_builtin_glossary)
        prepared.corrected_text = normalized
        prepared.normalized_source_text = normalized
        return prepared

    @staticmethod
    def _translate_with_chain(text: str, chain: list[Any]) -> str:
        translated = text
        for translation in chain:
            translated = translation.translate(translated)
        return str(translated).strip()

    def translate_texts(
        self,
        texts: list[str],
        source_lang: SourceLang,
        max_new_tokens: int = 256,
        *,
        use_gpu: bool = False,
        raw_terms: str | None = None,
        normalize_english: bool = True,
        use_builtin_glossary: bool = True,
    ) -> list[str]:
        del max_new_tokens  # Argos does not use token generation limits.
        prepared_texts = [
            self._prepare_source_text(
                text,
                source_lang,
                raw_terms=raw_terms,
                normalize_english=normalize_english,
                use_builtin_glossary=use_builtin_glossary,
            )
            for text in texts
            if text.strip()
        ]
        if not prepared_texts:
            return []

        results: list[str] = [""] * len(prepared_texts)
        model_indices: list[int] = []
        for index, prepared in enumerate(prepared_texts):
            if prepared.override_translation_fr:
                results[index] = prepared.override_translation_fr
            else:
                model_indices.append(index)

        chain: list[Any] | None = None
        active_gpu = use_gpu
        for index in model_indices:
            if chain is None:
                chain = self._translation_chain(source_lang, use_gpu=active_gpu)
            prepared = prepared_texts[index]
            try:
                results[index] = prepared.restore(self._translate_with_chain(prepared.text, chain))
            except Exception as exc:
                if not self._is_cuda_out_of_memory(exc):
                    raise
                self._clear_cuda_cache()
                active_gpu = False
                self._translation_cache.pop((source_lang, self.TARGET_LANG, True), None)
                self._translation_cache.pop((source_lang, self.TARGET_LANG, False), None)
                chain = self._translation_chain(source_lang, use_gpu=False)
                try:
                    results[index] = prepared.restore(self._translate_with_chain(prepared.text, chain))
                except Exception as retry_exc:
                    if not self._is_cuda_out_of_memory(retry_exc):
                        raise
                    results[index] = prepared.restore(prepared.text)
        return results

    @staticmethod
    def _block_source_text(block: OcrBlock) -> str:
        return (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text).strip()

    @staticmethod
    def _append_quality_warnings(block: OcrBlock, warnings: list[str]) -> None:
        for warning in warnings:
            if warning not in block.quality_warnings:
                block.quality_warnings.append(warning)

    @staticmethod
    def _should_skip_ja_translation(block: OcrBlock, source_text: str) -> bool:
        compact = "".join(source_text.split())
        if not compact:
            return True
        japanese_chars = len(_JAPANESE_CHAR_RE.findall(compact))
        confidence = block.confidence
        if _LOW_VALUE_JA_SYMBOL_RE.fullmatch(compact):
            return True
        if japanese_chars <= 5 and not _JA_NUMERIC_AMOUNT_RE.search(compact):
            return True
        if confidence is not None and confidence < 0.35:
            return True
        if confidence is not None and confidence < 0.65 and japanese_chars <= 5:
            return True
        if confidence is not None and confidence < 0.60 and japanese_chars <= 3:
            return True
        if japanese_chars <= 1 and len(compact) <= 3:
            return True
        return False

    @staticmethod
    def _preflight_review_note(categories: list[str]) -> str:
        category_set = set(categories)
        if category_set & {"fused_bubble", "sfx_mixed"}:
            return "[fusion] source incertaine: bulle/SFX probablement fusionne, verifier la zone"
        if category_set & {"zone_too_small", "split_bubble", "visual_edge"}:
            return "[zone] source incertaine: bbox/crop probablement a corriger avant traduction"
        return "[preflight] source incertaine: relire zone/ponctuation avant traduction"

    @classmethod
    def _prepare_block_text(
        cls,
        block: OcrBlock,
        source_lang: SourceLang,
        *,
        raw_terms: str | None = None,
        normalize_english: bool = True,
        use_builtin_glossary: bool = True,
    ) -> _PreparedText:
        source_text = cls._block_source_text(block)
        should_recompute_generated_source = (
            source_lang == "en"
            and block.manual_status in {"unchecked", "review"}
            and bool(block.normalized_source_text.strip())
        )
        if block.normalized_source_text.strip() and not should_recompute_generated_source:
            prepared = cls._apply_term_placeholders(
                block.normalized_source_text,
                raw_terms,
                use_builtin_glossary=use_builtin_glossary,
            )
            prepared.corrected_text = block.ocr_corrected_text or block.ocr_text
            prepared.normalized_source_text = block.normalized_source_text
            if source_lang == "en":
                prepared.override_translation_fr = EnglishDialogueNormalizer.translation_override(block.normalized_source_text)
            return prepared
        if should_recompute_generated_source:
            source_text = block.ocr_text.strip() or block.ocr_corrected_text.strip()
        return cls._prepare_source_text(
            source_text,
            source_lang,
            raw_terms=raw_terms,
            normalize_english=normalize_english,
            use_builtin_glossary=use_builtin_glossary,
        )

    def translate_blocks(
        self,
        blocks: list[OcrBlock],
        source_lang: SourceLang,
        *,
        use_gpu: bool = False,
        raw_terms: str | None = None,
        normalize_english: bool = True,
        use_builtin_glossary: bool = True,
        force: bool = False,
    ) -> list[OcrBlock]:
        targets: list[OcrBlock] = []
        for block in blocks:
            source_text = self._block_source_text(block)
            if not source_text or (not force and is_translation_protected(block)):
                continue
            if source_lang == "ja" and not force and self._should_skip_ja_translation(block, source_text):
                block.raw_translation_fr = ""
                block.translation_fr = ""
                note = "fragment japonais non traduit automatiquement: OCR faible/court"
                if note not in block.quality_warnings:
                    block.quality_warnings.append(note)
                continue
            targets.append(block)
        prepared_texts = [
            self._prepare_block_text(
                block,
                source_lang,
                raw_terms=raw_terms,
                normalize_english=normalize_english,
                use_builtin_glossary=use_builtin_glossary,
            )
            for block in targets
        ]
        if not prepared_texts:
            return blocks

        chain: list[Any] | None = None
        active_gpu = use_gpu
        for block, prepared in zip(targets, prepared_texts, strict=True):
            gate = self._source_quality_gate.evaluate(
                block,
                source_lang,
                raw_source_text=block.ocr_text,
                normalized_source_text=prepared.normalized_source_text,
            )
            self._append_quality_warnings(block, gate.warnings)
            if not gate.should_translate and not prepared.override_translation_fr:
                block.ocr_corrected_text = prepared.corrected_text
                block.normalized_source_text = prepared.normalized_source_text
                block.raw_translation_fr = ""
                block.translation_fr = ""
                if block.manual_status == "unchecked":
                    block.manual_status = "review"
                if not block.review_notes.strip():
                    block.review_notes = self._preflight_review_note(gate.categories)
                continue
            if prepared.override_translation_fr:
                restored_raw = prepared.override_translation_fr
            else:
                if chain is None:
                    chain = self._translation_chain(source_lang, use_gpu=active_gpu)
                try:
                    restored_raw = prepared.restore(self._translate_with_chain(prepared.text, chain))
                except Exception as exc:
                    if not self._is_cuda_out_of_memory(exc):
                        raise
                    self._clear_cuda_cache()
                    active_gpu = False
                    self._translation_cache.pop((source_lang, self.TARGET_LANG, True), None)
                    self._translation_cache.pop((source_lang, self.TARGET_LANG, False), None)
                    chain = self._translation_chain(source_lang, use_gpu=False)
                    try:
                        restored_raw = prepared.restore(self._translate_with_chain(prepared.text, chain))
                    except Exception as retry_exc:
                        if not self._is_cuda_out_of_memory(retry_exc):
                            raise
                        restored_raw = prepared.restore(prepared.text)
                        block.quality_warnings.append("Argos CUDA OOM: traduction source conservée, à revoir")
            block.ocr_corrected_text = prepared.corrected_text
            block.normalized_source_text = prepared.normalized_source_text
            block.raw_translation_fr = restored_raw
            block.translation_fr = prepared.override_translation_fr or restored_raw
            if block.manual_status == "review":
                block.manual_status = "edited"
        return blocks
