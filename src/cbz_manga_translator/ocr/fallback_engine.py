from __future__ import annotations

import re
import tempfile
from pathlib import Path

from cbz_manga_translator.core.models import OcrBlock, SourceLang
from cbz_manga_translator.ocr.candidates import OcrCandidate, bad_ocr_tokens, candidate_quality, word_tokens
from cbz_manga_translator.ocr.easyocr_engine import EasyOcrEngine
from cbz_manga_translator.ocr.incomplete import is_probably_fused_source, is_probably_incomplete_source, zone_issue_categories
from cbz_manga_translator.ocr.paddleocr_engine import PaddleOcrEngine
from cbz_manga_translator.ocr.punctuation import (
    apply_punctuation_hints,
    detect_visual_punctuation_hints,
    infer_textual_punctuation_hints,
)
from cbz_manga_translator.ocr.tesseract_engine import TesseractOcrEngine
from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation

_COMMON_OCR_CORRECTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[IiLl]nhook\b", re.IGNORECASE), "unhook"),
    (re.compile(r"\b[IiLl]hook\b", re.IGNORECASE), "unhook"),
    (re.compile(r"\b[Tt][Oo0]id\b", re.IGNORECASE), "told"),
    (re.compile(r"\b[Tt][Oo0]1d\b", re.IGNORECASE), "told"),
    (re.compile(r"\b[Rr]e[Ss]pecl\b", re.IGNORECASE), "respect"),
    (re.compile(r"\b[Rr]e[Pp]ect\b", re.IGNORECASE), "respect"),
    (re.compile(r"\b[Gg]ramrna\b", re.IGNORECASE), "gramma"),
    (re.compile(r"\b[Ll][Oo0]{2,}ky\b", re.IGNORECASE), "looky"),
    (re.compile(r"\b[Ll][Oo0][Oo0]kv\b", re.IGNORECASE), "looky"),
    (re.compile(r"\b[Ll][Oo0][Oo0]k[yv]\b", re.IGNORECASE), "looky"),
    (re.compile(r"\b[Dd][Oo0][Nn]'?T\b"), "DON'T"),
    (re.compile(r"\bI[’']?[IiLl]l\b", re.IGNORECASE), "I'll"),
]



class OcrFallbackEngine:
    """Local OCR fallback coordinator.

    EasyOCR remains the primary detector because it already gives useful bboxes.
    This engine re-reads those bboxes with additional local strategies and optional
    OCR backends. Optional engines are deliberately lazy and non-fatal: if Tesseract
    or PaddleOCR is not installed, the fallback still runs with local corrections
    and EasyOCR crop variants.
    """

    def __init__(
        self,
        easyocr_engine: EasyOcrEngine | None = None,
        *,
        tesseract_engine: TesseractOcrEngine | None = None,
        paddle_engine: PaddleOcrEngine | None = None,
    ) -> None:
        self.easyocr_engine = easyocr_engine or EasyOcrEngine()
        self.tesseract_engine = tesseract_engine or TesseractOcrEngine()
        self.paddle_engine = paddle_engine or PaddleOcrEngine()

    @staticmethod
    def is_optional_backend_available(name: str) -> bool:
        normalized = name.strip().lower()
        if normalized == "tesseract":
            return TesseractOcrEngine.available()
        if normalized == "paddleocr":
            return PaddleOcrEngine.available()
        return False

    @staticmethod
    def apply_common_ocr_corrections(text: str) -> str:
        corrected = normalize_ocr_text_for_translation(text)
        for pattern, replacement in _COMMON_OCR_CORRECTIONS:
            corrected = pattern.sub(replacement, corrected)
        corrected = normalize_ocr_text_for_translation(corrected)
        return " ".join(corrected.split())

    @staticmethod
    def candidate_quality(text: str, confidence: float | None = None, *, bonus: float = 0.0) -> float:
        return candidate_quality(text, confidence, bonus=bonus)

    @classmethod
    def _is_suspect(cls, block: OcrBlock, min_confidence: float) -> bool:
        if block.manual_status in {"validated", "ignored"}:
            return False
        text = " ".join(block.ocr_text.split())
        if not text:
            return True
        if block.quality_warnings:
            return True
        if is_probably_incomplete_source(text) or is_probably_fused_source(text):
            return True
        if block.confidence is not None and block.confidence < max(0.72, min_confidence):
            return True
        lower_words = {word.lower().strip("'") for word in word_tokens(text)}
        if lower_words & bad_ocr_tokens():
            return True
        if ";" in text and len(word_tokens(text)) <= 4:
            return True
        return False

    @staticmethod
    def _dedupe_candidates(candidates: list[OcrCandidate]) -> list[OcrCandidate]:
        best_by_text: dict[str, OcrCandidate] = {}
        for candidate in candidates:
            text_key = " ".join(candidate.text.casefold().split())
            if not text_key:
                continue
            current = best_by_text.get(text_key)
            if current is None or candidate.score > current.score:
                best_by_text[text_key] = candidate
        return sorted(best_by_text.values(), key=lambda item: item.score, reverse=True)

    @staticmethod
    def _rerank_candidates_for_block(block: OcrBlock, candidates: list[OcrCandidate]) -> list[OcrCandidate]:
        current_words = word_tokens(block.ocr_text)
        current_count = max(1, len(current_words))
        current_categories = set(zone_issue_categories(block.ocr_text))
        for candidate in candidates:
            candidate_words = word_tokens(candidate.text)
            candidate_count = len(candidate_words)
            if not candidate_count:
                continue
            extra_words = max(0, candidate_count - current_count)
            allowed_extra = max(3, int(current_count * 0.45))
            if extra_words > allowed_extra:
                candidate.score -= min(8.0, (extra_words - allowed_extra) * 0.85)
                candidate.note = f"{candidate.note}; penalite expansion large".strip("; ")
            if candidate_count / current_count > 1.75:
                candidate.score -= 2.2
                candidate.note = f"{candidate.note}; probable crop trop large".strip("; ")
            candidate_categories = set(zone_issue_categories(candidate.text))
            if "sfx_mixed" in candidate_categories and "sfx_mixed" not in current_categories:
                candidate.score -= 2.8
                candidate.note = f"{candidate.note}; SFX melange probable".strip("; ")
            if "fused_bubble" in candidate_categories and "fused_bubble" not in current_categories:
                candidate.score -= 1.8
                candidate.note = f"{candidate.note}; fusion probable".strip("; ")
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    @staticmethod
    def _normalize_words(text: str) -> list[str]:
        return [word.lower().strip("'") for word in word_tokens(normalize_ocr_text_for_translation(text))]

    @staticmethod
    def _has_inserted_noise(current_words: list[str], candidate_words: list[str]) -> bool:
        if not current_words or not candidate_words:
            return True
        cursor = 0
        extras_before_match = 0
        extras_between_matches = 0
        matched = 0
        for word in candidate_words:
            if cursor < len(current_words) and word == current_words[cursor]:
                cursor += 1
                matched += 1
                continue
            if matched == 0:
                extras_before_match += 1
            elif cursor < len(current_words):
                extras_between_matches += 1
        if cursor < max(1, int(len(current_words) * 0.75)):
            return True
        return extras_before_match > 0 or extras_between_matches > 0

    @classmethod
    def _is_auto_replacement_safe(cls, block: OcrBlock, candidate: OcrCandidate) -> bool:
        current = normalize_ocr_text_for_translation(block.ocr_text)
        proposed = normalize_ocr_text_for_translation(candidate.text)
        if not current or not proposed or current == proposed:
            return False
        current_words = cls._normalize_words(current)
        candidate_words = cls._normalize_words(proposed)
        if not current_words or not candidate_words:
            return False
        if candidate.engine == "ocr-corrections":
            return abs(len(candidate_words) - len(current_words)) <= 1
        if cls._has_inserted_noise(current_words, candidate_words):
            return False
        extra_words = max(0, len(candidate_words) - len(current_words))
        if extra_words > max(3, int(len(current_words) * 0.45)):
            return False
        single_letter_noise = [
            word for word in candidate_words
            if len(word) == 1 and word not in {"a", "i"} and word not in current_words
        ]
        if single_letter_noise:
            return False
        if re.search(r"(^|[\s])(?:\d+|[(){}\[\]<>_|\\]+)(?=\s|$)", proposed):
            return False
        return True

    def _easyocr_crop_candidates(
        self,
        image_path: Path,
        block: OcrBlock,
        source_lang: SourceLang,
        *,
        use_gpu: bool,
        min_confidence: float,
    ) -> list[OcrCandidate]:
        candidates: list[OcrCandidate] = []
        try:
            reader = self.easyocr_engine._reader(source_lang, use_gpu=use_gpu)  # noqa: SLF001 - internal reuse inside OCR package
        except Exception as exc:
            return [OcrCandidate("easyocr-crop", "", None, -999.0, f"reader unavailable: {exc}")]
        with tempfile.TemporaryDirectory(prefix="cbz_manga_ocr_fallback_") as raw_temp:
            temp_dir = Path(raw_temp)
            try:
                variant_paths = self.easyocr_engine._crop_variants(image_path, block.bbox, temp_dir)  # noqa: SLF001
            except Exception as exc:
                return [OcrCandidate("easyocr-crop", "", None, -999.0, f"crop failed: {exc}")]
            for variant_path in variant_paths:
                for paragraph in (False, True):
                    try:
                        raw_results = reader.readtext(str(variant_path), detail=1, paragraph=paragraph)
                    except Exception as exc:
                        candidates.append(OcrCandidate("easyocr-crop", "", None, -999.0, f"{variant_path.name}: {exc}"))
                        continue
                    text, confidence = self.easyocr_engine._join_crop_results(raw_results, source_lang)  # noqa: SLF001
                    text = self.apply_common_ocr_corrections(text)
                    if self.easyocr_engine._looks_like_noise(text, confidence, min_confidence):  # noqa: SLF001
                        continue
                    score = self.candidate_quality(text, confidence, bonus=0.12 if paragraph else 0.0)
                    note = f"{variant_path.stem}; paragraph={paragraph}"
                    candidates.append(OcrCandidate("easyocr-crop", text, confidence, score, note))
        return candidates

    def collect_candidates(
        self,
        image_path: str | Path,
        block: OcrBlock,
        source_lang: SourceLang,
        *,
        use_gpu: bool,
        min_confidence: float,
        include_optional_engines: bool = True,
    ) -> list[OcrCandidate]:
        image_path = Path(image_path)
        candidates = [
            OcrCandidate(
                engine="current",
                text=block.ocr_text,
                confidence=block.confidence,
                score=self.candidate_quality(block.ocr_text, block.confidence),
                note="OCR actuel",
            )
        ]

        corrected = self.apply_common_ocr_corrections(block.ocr_text)
        if corrected and corrected != block.ocr_text:
            candidates.append(
                OcrCandidate(
                    engine="ocr-corrections",
                    text=corrected,
                    confidence=block.confidence,
                    score=self.candidate_quality(corrected, block.confidence, bonus=0.95),
                    note="corrections locales d'erreurs OCR fréquentes",
                )
            )

        if source_lang == "en":
            punctuation_hints = detect_visual_punctuation_hints(image_path, block)
            punctuation_hints.extend(infer_textual_punctuation_hints(corrected or block.ocr_text))
            punctuated = apply_punctuation_hints(corrected or block.ocr_text, punctuation_hints)
            if punctuated and punctuated != (corrected or block.ocr_text):
                hint_note = ", ".join(f"{hint.mark} {hint.confidence:.2f}" for hint in punctuation_hints)
                candidates.append(
                    OcrCandidate(
                        engine="punctuation-detector",
                        text=punctuated,
                        confidence=block.confidence,
                        score=self.candidate_quality(punctuated, block.confidence, bonus=0.80),
                        note=f"ponctuation visuelle: {hint_note}",
                    )
                )

        candidates.extend(
            self._easyocr_crop_candidates(
                image_path,
                block,
                source_lang,
                use_gpu=use_gpu,
                min_confidence=min_confidence,
            )
        )

        if include_optional_engines:
            for candidate in self.tesseract_engine.recognize_crop(image_path, block.bbox, source_lang):
                candidates.append(candidate)
            for candidate in self.paddle_engine.recognize_crop(image_path, block.bbox, source_lang, use_gpu=use_gpu):
                candidates.append(candidate)

        return self._rerank_candidates_for_block(block, self._dedupe_candidates(candidates))

    def improve_blocks(
        self,
        image_path: str | Path,
        blocks: list[OcrBlock],
        source_lang: SourceLang,
        *,
        use_gpu: bool = False,
        min_confidence: float = 0.20,
        only_suspect: bool = True,
        include_optional_engines: bool = True,
        min_score_gain: float = 0.45,
    ) -> tuple[list[OcrBlock], int]:
        changed = 0
        for block in blocks:
            if only_suspect and not self._is_suspect(block, min_confidence):
                continue
            if block.manual_status in {"validated", "ignored"}:
                continue
            candidates = self.collect_candidates(
                image_path,
                block,
                source_lang,
                use_gpu=use_gpu,
                min_confidence=min_confidence,
                include_optional_engines=include_optional_engines,
            )
            block.ocr_alternatives = [candidate.to_dict() for candidate in candidates[:8]]
            if not candidates:
                continue
            current_score = self.candidate_quality(block.ocr_text, block.confidence)
            best = next((candidate for candidate in candidates if self._is_auto_replacement_safe(block, candidate)), None)
            if best is None:
                continue
            if best.text and best.text != block.ocr_text and best.score >= current_score + min_score_gain:
                old_text = block.ocr_text
                block.ocr_text = best.text
                block.confidence = best.confidence
                block.ocr_corrected_text = ""
                block.normalized_source_text = ""
                block.raw_translation_fr = ""
                block.translation_fr = ""
                if block.manual_status == "unchecked":
                    block.manual_status = "edited"
                warning = f"OCR fallback: {best.engine} a remplacé '{old_text}' par '{best.text}'"
                if warning not in block.quality_warnings:
                    block.quality_warnings.append(warning)
                changed += 1
        return blocks, changed
