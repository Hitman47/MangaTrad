from __future__ import annotations

import re
import tempfile
from pathlib import Path

from cbz_manga_translator.core.models import SourceLang
from cbz_manga_translator.ocr.candidates import OcrCandidate, candidate_quality


class TesseractOcrEngine:
    """Optional local OCR backend using the system Tesseract binary.

    This module never hard-depends on pytesseract/Tesseract. Missing binaries,
    missing language packs or runtime errors simply return no candidates.
    """

    @staticmethod
    def available() -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def _lang_code(source_lang: SourceLang) -> str:
        return "jpn+eng" if source_lang == "ja" else "eng"

    @staticmethod
    def _prepare_crop(image_path: Path, bbox: list[int], temp_dir: Path) -> list[Path]:
        from PIL import Image, ImageOps

        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        x1, y1, x2, y2 = bbox
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        margin = max(8, int(max(bw, bh) * 0.16))
        crop = image.crop((max(0, x1 - margin), max(0, y1 - margin), min(width, x2 + margin), min(height, y2 + margin)))
        variants = []
        for factor in (2, 3, 4):
            upscaled = crop.resize((crop.width * factor, crop.height * factor), Image.Resampling.LANCZOS)
            gray = ImageOps.grayscale(upscaled)
            variants.append((f"tess_x{factor}_gray", ImageOps.autocontrast(gray)))
            variants.append((f"tess_x{factor}_threshold", gray.point(lambda pixel: 255 if pixel > 168 else 0)))
        paths: list[Path] = []
        for name, variant in variants:
            out = temp_dir / f"{name}.png"
            variant.save(out)
            paths.append(out)
        return paths

    @staticmethod
    def _clean(text: str) -> str:
        cleaned = " ".join(str(text).replace("\n", " ").replace("\f", " ").split())
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        return cleaned.strip()

    def recognize_crop(self, image_path: str | Path, bbox: list[int], source_lang: SourceLang) -> list[OcrCandidate]:
        try:
            import pytesseract
        except Exception:
            return []

        image_path = Path(image_path)
        candidates: list[OcrCandidate] = []
        with tempfile.TemporaryDirectory(prefix="cbz_manga_tesseract_") as raw_temp:
            temp_dir = Path(raw_temp)
            try:
                variants = self._prepare_crop(image_path, bbox, temp_dir)
            except Exception:
                return []
            for variant_path in variants:
                for psm in (6, 7, 11):
                    try:
                        raw = pytesseract.image_to_string(
                            str(variant_path),
                            lang=self._lang_code(source_lang),
                            config=f"--oem 3 --psm {psm}",
                        )
                    except Exception:
                        continue
                    text = self._clean(raw)
                    if not text:
                        continue
                    score = candidate_quality(text, None, bonus=0.20)
                    candidates.append(OcrCandidate("tesseract", text, None, score, f"{variant_path.stem}, psm={psm}"))
        return candidates
