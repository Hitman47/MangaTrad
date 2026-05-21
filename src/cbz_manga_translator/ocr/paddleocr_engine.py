from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from cbz_manga_translator.core.models import SourceLang
from cbz_manga_translator.ocr.candidates import OcrCandidate, candidate_quality


class PaddleOcrEngine:
    """Optional local OCR backend using PaddleOCR when installed."""

    def __init__(self) -> None:
        self._instances: dict[str, Any] = {}

    @staticmethod
    def available() -> bool:
        try:
            import paddleocr  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def _lang_code(source_lang: SourceLang) -> str:
        return "japan" if source_lang == "ja" else "en"

    def _instance(self, source_lang: SourceLang, use_gpu: bool) -> Any:
        lang = self._lang_code(source_lang)
        key = f"{lang}|gpu={bool(use_gpu)}"
        if key not in self._instances:
            from paddleocr import PaddleOCR

            try:
                self._instances[key] = PaddleOCR(lang=lang, use_angle_cls=True, use_gpu=bool(use_gpu), show_log=False)
            except TypeError:
                # Newer PaddleOCR versions changed some constructor parameters.
                self._instances[key] = PaddleOCR(lang=lang, use_angle_cls=True)
        return self._instances[key]

    @staticmethod
    def _crop(image_path: Path, bbox: list[int], temp_dir: Path) -> Path:
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        x1, y1, x2, y2 = bbox
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        margin = max(8, int(max(bw, bh) * 0.15))
        crop = image.crop((max(0, x1 - margin), max(0, y1 - margin), min(width, x2 + margin), min(height, y2 + margin)))
        out = temp_dir / "paddle_crop.png"
        crop.save(out)
        return out

    @staticmethod
    def _extract_texts(raw_result: Any) -> tuple[str, float | None]:
        texts: list[str] = []
        confidences: list[float] = []
        pages = raw_result if isinstance(raw_result, list) else [raw_result]
        for page in pages:
            if not page:
                continue
            for item in page:
                try:
                    text = str(item[1][0])
                    conf = float(item[1][1])
                except Exception:
                    continue
                if text.strip():
                    texts.append(" ".join(text.split()))
                    confidences.append(conf)
        confidence = None if not confidences else sum(confidences) / len(confidences)
        return " ".join(texts).strip(), confidence

    def recognize_crop(
        self,
        image_path: str | Path,
        bbox: list[int],
        source_lang: SourceLang,
        *,
        use_gpu: bool,
    ) -> list[OcrCandidate]:
        if not self.available():
            return []
        with tempfile.TemporaryDirectory(prefix="cbz_manga_paddleocr_") as raw_temp:
            temp_dir = Path(raw_temp)
            try:
                crop_path = self._crop(Path(image_path), bbox, temp_dir)
                result = self._instance(source_lang, use_gpu=use_gpu).ocr(str(crop_path), cls=True)
            except Exception:
                return []
        text, confidence = self._extract_texts(result)
        if not text:
            return []
        score = candidate_quality(text, confidence, bonus=0.35)
        return [OcrCandidate("paddleocr", text, confidence, score, "optional local backend")]
