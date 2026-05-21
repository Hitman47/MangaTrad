from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from cbz_manga_translator.analysis.learning import build_learning_report
from cbz_manga_translator.analysis.light_quality import compute_quality_features
from cbz_manga_translator.core.models import ProjectData, OcrBlock, PageRecord


def _corpus_path_labels(image_name: str) -> tuple[str, str]:
    """Best-effort series/volume labels for exported corpus paths."""
    path = Path(str(image_name))
    parts = path.parts
    if "pages" in parts:
        index = parts.index("pages")
        series = parts[index + 1] if len(parts) > index + 1 else ""
        volume = parts[index + 2] if len(parts) > index + 2 else ""
        return series, volume
    return "", ""


def _block_row(page: PageRecord, block: OcrBlock) -> dict[str, Any]:
    features = compute_quality_features(block)
    source = (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text or "").strip()
    series_label, volume_label = _corpus_path_labels(page.image_name)
    return {
        "page_index": page.page_index,
        "page_number": page.page_index + 1,
        "series_label": series_label,
        "volume_label": volume_label,
        "image_name": page.image_name,
        "block_id": block.id,
        "reading_order": block.reading_order,
        "bbox": ",".join(str(v) for v in block.bbox),
        "source_lang": block.source_lang,
        "confidence": "" if block.confidence is None else f"{block.confidence:.4f}",
        "manual_status": block.manual_status,
        "risk_score": features.risk_score,
        "suggested_action": features.action,
        "risk_reasons": " | ".join(features.reasons),
        "quality_warnings": " | ".join(block.quality_warnings),
        "ocr_text": block.ocr_text,
        "ocr_corrected_text": block.ocr_corrected_text,
        "normalized_source_text": block.normalized_source_text,
        "source_for_review": source,
        "raw_translation_fr": block.raw_translation_fr,
        "translation_fr": block.translation_fr,
        "ocr_alternatives_count": len(block.ocr_alternatives),
        "ocr_alternatives": json.dumps(block.ocr_alternatives, ensure_ascii=False),
    }


def iter_review_rows(project: ProjectData) -> Iterable[dict[str, Any]]:
    for page in project.pages:
        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            yield _block_row(page, block)


def export_review_dataset(project: ProjectData, output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = list(iter_review_rows(project))
    csv_path = output / "mangatrad_review_blocks.csv"
    jsonl_path = output / "mangatrad_review_blocks.jsonl"
    learning_path = output / "mangatrad_learning_report.json"
    glossary_path = output / "mangatrad_glossary_suggestions.txt"
    report_path = output / "mangatrad_quality_report.md"

    fieldnames = list(rows[0].keys()) if rows else [
        "page_index", "page_number", "series_label", "volume_label", "image_name", "block_id", "reading_order", "bbox",
        "source_lang", "confidence", "manual_status", "risk_score", "suggested_action",
        "risk_reasons", "quality_warnings", "ocr_text", "ocr_corrected_text",
        "normalized_source_text", "source_for_review", "raw_translation_fr", "translation_fr",
        "ocr_alternatives_count", "ocr_alternatives",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    learning = build_learning_report(project)
    learning_path.write_text(json.dumps(learning.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    glossary_lines = [f"{item['term']}  # count={item['count']}" for item in learning.glossary_candidates]
    glossary_path.write_text("\n".join(glossary_lines) + ("\n" if glossary_lines else ""), encoding="utf-8")

    high_risk_count = sum(1 for row in rows if int(row["risk_score"]) >= 55)
    medium_risk_count = sum(1 for row in rows if 25 <= int(row["risk_score"]) < 55)
    ok_count = sum(1 for row in rows if int(row["risk_score"]) < 25)
    from collections import Counter

    reason_counter: Counter[str] = Counter()
    series_counter: Counter[str] = Counter()
    for row in rows:
        series_counter[str(row.get("series_label") or "unknown")] += 1
        for reason in str(row.get("risk_reasons") or "").split(" | "):
            reason = reason.strip()
            if reason:
                reason_counter[reason] += 1

    report_lines = [
        "# MangaTrad quality report",
        "",
        f"- Pages: {len(project.pages)}",
        f"- Blocks: {len(rows)}",
        f"- High risk blocks: {high_risk_count}",
        f"- Medium risk blocks: {medium_risk_count}",
        f"- Probably OK blocks: {ok_count}",
        f"- Learnable blocks: {learning.summary['learnable_blocks']}",
        "",
        "## Top risk reasons",
        "",
    ]
    if reason_counter:
        for reason, count in reason_counter.most_common(20):
            report_lines.append(f"- {count}: {reason}")
    else:
        report_lines.append("- Aucun signal de risque.")
    report_lines.extend(["", "## Blocks by series", ""])
    for series, count in series_counter.most_common(30):
        report_lines.append(f"- {series}: {count} blocks")
    report_lines.extend(["", "## Top high-risk examples", ""])
    for item in learning.high_risk_examples[:30]:
        report_lines.extend([
            f"### Page {int(item['page_index']) + 1} — {item['block_id']} — risk {item['risk_score']}",
            "",
            f"Source: `{item['source']}`",
            "",
            f"FR: `{item['translation_fr']}`",
            "",
            "Reasons: " + "; ".join(item["reasons"]),
            "",
        ])
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "csv": csv_path,
        "jsonl": jsonl_path,
        "learning_report": learning_path,
        "glossary_suggestions": glossary_path,
        "quality_report": report_path,
    }
