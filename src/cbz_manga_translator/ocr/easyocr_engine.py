from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from cbz_manga_translator.core.models import OcrBlock, SourceLang
from cbz_manga_translator.ocr.candidates import candidate_quality
from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation

_TEXT_CHAR_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9ぁ-んァ-ン一-龯々ー]")
_LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿぁ-んァ-ン一-龯々]")
_NOISE_ONLY_RE = re.compile(r"^[0-9\s<>{}\[\]().,;:!?/\\|_+*=~`'\"-]+$")


class EasyOcrEngine:
    """Free OCR backend using EasyOCR.

    EasyOCR returns polygons, text and confidence. We normalize polygons into
    rectangular bboxes now so the project cache can later drive bubble overlays
    and replacement.

    The engine deliberately keeps two V1 post-processing steps configurable:
    noise filtering and line grouping. They are imperfect, but they improve the
    useful dialogue output compared with translating every OCR fragment alone.
    """

    def __init__(self) -> None:
        self._readers: dict[str, Any] = {}

    @staticmethod
    def cuda_available() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    @staticmethod
    def resolved_gpu(use_gpu: bool) -> bool:
        return bool(use_gpu and EasyOcrEngine.cuda_available())

    @staticmethod
    def _languages_for(source_lang: SourceLang) -> list[str]:
        if source_lang == "ja":
            # English is compatible with every EasyOCR language and helps with SFX/Latin names.
            return ["ja", "en"]
        return ["en"]

    def _reader(self, source_lang: SourceLang, use_gpu: bool) -> Any:
        resolved_gpu = self.resolved_gpu(use_gpu)
        key = f"{'+'.join(self._languages_for(source_lang))}|gpu={resolved_gpu}"
        if key not in self._readers:
            import easyocr  # lazy import: keeps tests and CLI inspection light

            self._readers[key] = easyocr.Reader(self._languages_for(source_lang), gpu=resolved_gpu)
        return self._readers[key]

    @staticmethod
    def _polygon_to_bbox(polygon: list[list[float]]) -> list[int]:
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]

    @staticmethod
    def _bbox_union(blocks: list[OcrBlock]) -> list[int]:
        return [
            min(block.bbox[0] for block in blocks),
            min(block.bbox[1] for block in blocks),
            max(block.bbox[2] for block in blocks),
            max(block.bbox[3] for block in blocks),
        ]

    @staticmethod
    def _bbox_width(bbox: list[int]) -> int:
        return max(1, bbox[2] - bbox[0])

    @staticmethod
    def _bbox_height(bbox: list[int]) -> int:
        return max(1, bbox[3] - bbox[1])

    @staticmethod
    def _bbox_center(bbox: list[int]) -> tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    @staticmethod
    def _x_overlap_ratio(a: list[int], b: list[int]) -> float:
        overlap = max(0, min(a[2], b[2]) - max(a[0], b[0]))
        return overlap / max(1, min(EasyOcrEngine._bbox_width(a), EasyOcrEngine._bbox_width(b)))

    @staticmethod
    def _vertical_gap(a: list[int], b: list[int]) -> int:
        if a[3] < b[1]:
            return b[1] - a[3]
        if b[3] < a[1]:
            return a[1] - b[3]
        return 0

    @staticmethod
    def _looks_like_noise(text: str, confidence: float | None, min_confidence: float) -> bool:
        compact = " ".join(str(text).strip().split())
        if not compact:
            return True
        if confidence is not None and confidence < min_confidence:
            return True
        if len(compact) <= 1:
            return True
        if _NOISE_ONLY_RE.fullmatch(compact):
            return True
        text_chars = _TEXT_CHAR_RE.findall(compact)
        letters = _LETTER_RE.findall(compact)
        if not text_chars or not letters:
            return True
        # Very short low-confidence fragments are usually OCR noise on screentone/artifacts.
        if confidence is not None and confidence < 0.55 and len(letters) <= 2:
            return True
        return False

    @staticmethod
    def _line_sort_key(block: OcrBlock, source_lang: SourceLang) -> tuple[float, float]:
        cx, cy = EasyOcrEngine._bbox_center(block.bbox)
        # English text inside localized editions generally reads left-to-right.
        # Japanese manga page order is right-to-left, but OCR fragments inside a
        # vertical block are still spatial; x-desc is a better default for V1.
        return (cy, -cx if source_lang == "ja" else cx)

    @staticmethod
    def _can_merge(group: list[OcrBlock], block: OcrBlock) -> bool:
        group_bbox = EasyOcrEngine._bbox_union(group)
        bbox = block.bbox
        avg_line_height = sum(EasyOcrEngine._bbox_height(item.bbox) for item in group + [block]) / (len(group) + 1)
        gap = EasyOcrEngine._vertical_gap(group_bbox, bbox)
        if gap > max(34, avg_line_height * 1.45):
            return False

        overlap_ratio = EasyOcrEngine._x_overlap_ratio(group_bbox, bbox)
        group_cx, _ = EasyOcrEngine._bbox_center(group_bbox)
        block_cx, _ = EasyOcrEngine._bbox_center(bbox)
        center_dx = abs(group_cx - block_cx)
        width_allowance = max(EasyOcrEngine._bbox_width(group_bbox), EasyOcrEngine._bbox_width(bbox)) * 0.85

        if overlap_ratio >= 0.18:
            return True
        return center_dx <= max(45, width_allowance)

    @staticmethod
    def _join_texts(lines: list[OcrBlock], source_lang: SourceLang) -> str:
        ordered = sorted(lines, key=lambda item: EasyOcrEngine._line_sort_key(item, source_lang))
        texts = [" ".join(item.ocr_text.strip().split()) for item in ordered if item.ocr_text.strip()]
        if source_lang == "ja":
            # No hard spaces for mostly Japanese text; keep spaces when Latin fragments are present.
            joined = "".join(texts)
            if re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", joined):
                joined = " ".join(texts)
            return joined
        return " ".join(texts)

    @classmethod
    def _merge_related_lines(cls, blocks: list[OcrBlock], source_lang: SourceLang) -> list[OcrBlock]:
        if not blocks:
            return []
        groups: list[list[OcrBlock]] = []
        for block in sorted(blocks, key=lambda item: cls._line_sort_key(item, source_lang)):
            best_group: list[OcrBlock] | None = None
            for group in groups:
                if cls._can_merge(group, block):
                    best_group = group
                    break
            if best_group is None:
                groups.append([block])
            else:
                best_group.append(block)

        merged: list[OcrBlock] = []
        for order, group in enumerate(sorted(groups, key=lambda items: cls._line_sort_key(items[0], source_lang))):
            ordered_group = sorted(group, key=lambda item: cls._line_sort_key(item, source_lang))
            confidence_values = [item.confidence for item in ordered_group if item.confidence is not None]
            confidence = None if not confidence_values else sum(confidence_values) / len(confidence_values)
            merged.append(
                OcrBlock(
                    id=ordered_group[0].id,
                    bbox=cls._bbox_union(ordered_group),
                    source_lang=source_lang,
                    ocr_text=cls._join_texts(ordered_group, source_lang),
                    confidence=confidence,
                    reading_order=order,
                )
            )
        return merged

    def _postprocess_results(
        self,
        raw_results: list[Any],
        source_lang: SourceLang,
        page_index: int,
        min_confidence: float,
        merge_lines: bool,
        filter_noise: bool,
    ) -> list[OcrBlock]:
        blocks: list[OcrBlock] = []
        for raw_order, item in enumerate(raw_results):
            polygon, text, confidence = item
            clean_text = normalize_ocr_text_for_translation(str(text))
            confidence_value = float(confidence) if confidence is not None else None
            if filter_noise and self._looks_like_noise(clean_text, confidence_value, min_confidence):
                continue
            blocks.append(
                OcrBlock(
                    id=f"p{page_index:04d}_b{raw_order:04d}",
                    bbox=self._polygon_to_bbox(polygon),
                    source_lang=source_lang,
                    ocr_text=clean_text,
                    confidence=confidence_value,
                    reading_order=raw_order,
                )
            )
        if merge_lines:
            return self._merge_related_lines(blocks, source_lang)
        for order, block in enumerate(sorted(blocks, key=lambda item: self._line_sort_key(item, source_lang))):
            block.reading_order = order
        return blocks


    @staticmethod
    def _candidate_quality(text: str, confidence: float | None) -> float:
        return candidate_quality(text, confidence)

    @staticmethod
    def _join_crop_results(results: list[Any], source_lang: SourceLang) -> tuple[str, float | None]:
        temp_blocks: list[OcrBlock] = []
        for index, item in enumerate(results):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            polygon = item[0]
            text = item[1]
            confidence = item[2] if len(item) > 2 else None
            clean_text = normalize_ocr_text_for_translation(str(text))
            if not clean_text:
                continue
            try:
                bbox = EasyOcrEngine._polygon_to_bbox(polygon)
            except Exception:
                bbox = [0, 0, 1, 1]
            temp_blocks.append(
                OcrBlock(
                    id=f"crop_{index}",
                    bbox=bbox,
                    source_lang=source_lang,
                    ocr_text=clean_text,
                    confidence=float(confidence) if confidence is not None else None,
                    reading_order=index,
                )
            )
        if not temp_blocks:
            return "", None
        ordered = sorted(temp_blocks, key=lambda item: EasyOcrEngine._line_sort_key(item, source_lang))
        text = EasyOcrEngine._join_texts(ordered, source_lang)
        confidences = [block.confidence for block in ordered if block.confidence is not None]
        confidence = None if not confidences else sum(confidences) / len(confidences)
        return text, confidence

    @staticmethod
    def _crop_variants(image_path: Path, bbox: list[int], temp_dir: Path) -> list[Path]:
        from PIL import Image, ImageFilter, ImageOps

        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        x1, y1, x2, y2 = bbox
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        margin = max(8, int(max(bw, bh) * 0.18))
        crop_box = (
            max(0, x1 - margin),
            max(0, y1 - margin),
            min(width, x2 + margin),
            min(height, y2 + margin),
        )
        crop = image.crop(crop_box)

        def padded(img: Image.Image, pad: int) -> Image.Image:
            return ImageOps.expand(img, border=pad, fill="white")

        variants: list[tuple[str, Image.Image]] = [("crop", crop), ("crop_pad", padded(crop, max(8, margin // 2)))]
        for factor in (2, 3, 4):
            base = padded(crop, max(8, margin // 2)).resize(
                (max(1, crop.width * factor), max(1, crop.height * factor)),
                Image.Resampling.LANCZOS,
            )
            variants.append((f"x{factor}", base))
            gray = ImageOps.grayscale(base)
            autocontrast = ImageOps.autocontrast(gray)
            variants.append((f"x{factor}_gray", autocontrast))
            variants.append((f"x{factor}_sharp", autocontrast.filter(ImageFilter.UnsharpMask(radius=1.2, percent=170, threshold=3))))
            variants.append((f"x{factor}_median", autocontrast.filter(ImageFilter.MedianFilter(size=3))))
            for threshold in (145, 170, 195):
                thresholded = autocontrast.point(lambda pixel, threshold=threshold: 255 if pixel > threshold else 0)
                variants.append((f"x{factor}_threshold_{threshold}", thresholded))

        paths: list[Path] = []
        seen: set[bytes] = set()
        for index, (name, variant) in enumerate(variants):
            out = temp_dir / f"ocr_variant_{index:02d}_{name}.png"
            signature = variant.resize((min(12, variant.width), min(12, variant.height))).tobytes()
            if signature in seen:
                continue
            seen.add(signature)
            variant.save(out)
            paths.append(out)
        return paths

    def _refine_blocks_from_crops(
        self,
        image_path: Path,
        blocks: list[OcrBlock],
        source_lang: SourceLang,
        *,
        use_gpu: bool,
        min_confidence: float,
        filter_noise: bool,
    ) -> list[OcrBlock]:
        if not blocks:
            return blocks
        reader = self._reader(source_lang, use_gpu=use_gpu)
        with tempfile.TemporaryDirectory(prefix="cbz_manga_ocr_variants_") as raw_temp:
            temp_dir = Path(raw_temp)
            for block in blocks:
                current_score = self._candidate_quality(block.ocr_text, block.confidence)
                best_text = block.ocr_text
                best_confidence = block.confidence
                best_score = current_score
                try:
                    variant_paths = self._crop_variants(Path(image_path), block.bbox, temp_dir)
                except Exception:
                    continue
                for variant_path in variant_paths:
                    try:
                        raw_results = reader.readtext(str(variant_path), detail=1, paragraph=False)
                    except Exception:
                        continue
                    candidate_text, candidate_confidence = self._join_crop_results(raw_results, source_lang)
                    if filter_noise and self._looks_like_noise(candidate_text, candidate_confidence, min_confidence):
                        continue
                    candidate_score = self._candidate_quality(candidate_text, candidate_confidence)
                    if candidate_score > best_score + 0.65:
                        best_text = candidate_text
                        best_confidence = candidate_confidence
                        best_score = candidate_score
                if best_text and best_text != block.ocr_text:
                    block.ocr_text = best_text
                    block.confidence = best_confidence
        for order, block in enumerate(sorted(blocks, key=lambda item: self._line_sort_key(item, source_lang))):
            block.reading_order = order
        return blocks

    def recognize(
        self,
        image_path: str | Path,
        source_lang: SourceLang,
        page_index: int,
        *,
        use_gpu: bool = False,
        min_confidence: float = 0.20,
        merge_lines: bool = True,
        filter_noise: bool = True,
        refine_crops: bool = True,
    ) -> list[OcrBlock]:
        image_path = Path(image_path)
        reader = self._reader(source_lang, use_gpu=use_gpu)
        raw_results = reader.readtext(str(image_path), detail=1, paragraph=False)
        blocks = self._postprocess_results(
            raw_results,
            source_lang=source_lang,
            page_index=page_index,
            min_confidence=min_confidence,
            merge_lines=merge_lines,
            filter_noise=filter_noise,
        )
        if refine_crops:
            blocks = self._refine_blocks_from_crops(
                image_path,
                blocks,
                source_lang,
                use_gpu=use_gpu,
                min_confidence=min_confidence,
                filter_noise=filter_noise,
            )
        return blocks
