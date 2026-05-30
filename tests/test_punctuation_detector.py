from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.ocr.punctuation import (
    apply_punctuation_hints,
    apply_visual_punctuation_to_blocks,
    detect_visual_punctuation_hints,
    infer_textual_punctuation_hints,
    visual_zone_warnings_for_block,
)


def test_detect_visual_ellipsis_and_apply_hint(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "ellipsis.png"
    image = Image.new("L", (80, 40), "white")
    draw = ImageDraw.Draw(image)
    for x in (46, 54, 62):
        draw.ellipse((x, 28, x + 3, 31), fill="black")
    image.save(image_path)
    block = OcrBlock(id="b", bbox=[0, 0, 80, 40], source_lang="en", ocr_text="SO Why")

    hints = detect_visual_punctuation_hints(image_path, block)

    assert any(hint.mark == "..." for hint in hints)
    assert apply_punctuation_hints("SO Why", hints) == "SO Why..."


def test_detect_visual_exclamation_and_apply_hint(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "bang.png"
    image = Image.new("L", (50, 60), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((32, 16, 35, 38), fill="black")
    draw.ellipse((31, 45, 36, 50), fill="black")
    image.save(image_path)
    block = OcrBlock(id="b", bbox=[0, 0, 50, 60], source_lang="en", ocr_text="NO WAY")

    hints = detect_visual_punctuation_hints(image_path, block)

    assert any(hint.mark == "!" for hint in hints)
    assert apply_punctuation_hints("NO WAY", hints) == "NO WAY!"


def test_detect_visual_question_mark_and_apply_hint(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "question.png"
    image = Image.new("L", (70, 70), "white")
    draw = ImageDraw.Draw(image)
    draw.arc((22, 10, 48, 34), start=200, end=535, fill="black", width=3)
    draw.line((36, 33, 34, 42), fill="black", width=3)
    draw.ellipse((31, 52, 37, 58), fill="black")
    image.save(image_path)
    block = OcrBlock(id="b", bbox=[0, 0, 70, 70], source_lang="en", ocr_text="WHAT NOW")

    hints = detect_visual_punctuation_hints(image_path, block)

    assert any(hint.mark == "?" for hint in hints)
    assert apply_punctuation_hints("WHAT NOW", hints) == "WHAT NOW?"


def test_infer_textual_question_hint() -> None:
    hints = infer_textual_punctuation_hints("What kind of shifty things are you doing")

    assert [hint.mark for hint in hints] == ["?"]
    assert apply_punctuation_hints("What kind of shifty things are you doing", hints).endswith("?")


def test_apply_visual_punctuation_to_blocks_updates_standard_ocr_block(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "page.png"
    image = Image.new("L", (80, 40), "white")
    draw = ImageDraw.Draw(image)
    for x in (46, 54, 62):
        draw.ellipse((x, 28, x + 3, 31), fill="black")
    image.save(image_path)
    block = OcrBlock(id="b", bbox=[0, 0, 80, 40], source_lang="en", ocr_text="I understand")

    changed = apply_visual_punctuation_to_blocks(image_path, [block])

    assert changed == 1
    assert block.ocr_text == "I understand..."
    assert any("ponctuation visuelle" in warning for warning in block.quality_warnings)


def test_visual_zone_warning_when_text_touches_crop_edge(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "edge.png"
    image = Image.new("L", (60, 40), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 12, 16, 24), fill="black")
    image.save(image_path)
    block = OcrBlock(id="b", bbox=[0, 0, 60, 40], source_lang="en", ocr_text="cut")

    warnings = visual_zone_warnings_for_block(image_path, block)

    assert any("bord du crop" in warning for warning in warnings)
