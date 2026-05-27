import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from cbz_manga_translator.analysis.review_diagnose import classify_block
from cbz_manga_translator.analysis.review_filter import non_reviewable_reason, page_non_reviewable_reason
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation
from cbz_manga_translator.review.model import block_source_text, review_decision_for_block
from cbz_manga_translator.review.replay import expected_source_is_translation_like, text_similarity
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer


@dataclass(slots=True)
class RegressionItem:
    project_path: str
    page_index: int
    block_id: str
    decision: str
    status: str
    categories: list[str]
    raw_ocr: str
    expected_source: str
    predicted_source: str
    source_similarity: float
    source_checked: bool
    expected_translation: str
    predicted_translation: str
    translation_similarity: float
    notes: str


@dataclass(slots=True)
class RegressionReport:
    project_count: int
    block_count: int
    evaluated_source_count: int
    source_match_count: int
    evaluated_translation_count: int
    translation_match_count: int
    ignored_count: int
    ignored_auto_covered_count: int
    status_counts: dict[str, int]
    category_counts: dict[str, int]
    scores: dict[str, float]
    items: list[RegressionItem]


def discover_review_projects(paths: list[str | Path]) -> list[Path]:
    projects: list[Path] = []
    seen: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        candidates: list[Path]
        if path.is_dir():
            candidates = sorted(path.rglob("*.reviewed.json"))
        elif path.exists():
            candidates = [path]
        else:
            candidates = sorted(path.parent.glob(path.name))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if ".diagnostic" in candidate.parts or ".replay" in candidate.parts:
                continue
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                projects.append(candidate)
    return projects


def _changed_or_reviewed(block: OcrBlock) -> bool:
    raw = block.ocr_text.strip()
    source = block_source_text(block).strip()
    raw_translation = block.raw_translation_fr.strip()
    translation = block.translation_fr.strip()
    return (
        block.manual_status in {"edited", "validated", "review", "ignored"}
        or bool(block.review_notes.strip())
        or bool(source and text_similarity(source, raw) < 0.995)
        or bool(raw_translation and translation and text_similarity(raw_translation, translation) < 0.995)
    )


def _predict_source(raw_ocr: str) -> str:
    cleaned = normalize_ocr_text_for_translation(raw_ocr)
    return EnglishDialogueNormalizer.prepare(cleaned).normalized_text


def _predict_translation(predicted_source: str) -> str:
    return EnglishDialogueNormalizer.translation_override(predicted_source)


def _source_similarity(expected_source: str, predicted_source: str) -> float:
    expected_normalized = EnglishDialogueNormalizer.normalize_colloquial(expected_source)
    predicted_normalized = EnglishDialogueNormalizer.normalize_colloquial(predicted_source)
    return max(
        text_similarity(expected_source, predicted_source),
        text_similarity(expected_normalized, predicted_source),
        text_similarity(expected_source, predicted_normalized),
        text_similarity(expected_normalized, predicted_normalized),
    )


def evaluate_block(
    project_path: Path,
    block: OcrBlock,
    page_index: int,
    source_threshold: float,
    translation_threshold: float,
    *,
    page_ignore_reason: str = "",
) -> RegressionItem:
    decision = review_decision_for_block(block)
    expected_source = block_source_text(block).strip()
    expected_translation = (block.translation_fr or block.raw_translation_fr).strip()
    categories = sorted({item.category for item in classify_block(block, page_index)})

    if decision in {"sfx", "ignore"}:
        covered = bool(page_ignore_reason or non_reviewable_reason(block))
        status = "ignored_covered" if covered else "ignored_uncovered"
        return RegressionItem(
            project_path=str(project_path),
            page_index=page_index,
            block_id=block.id,
            decision=decision,
            status=status,
            categories=categories or ["sfx_or_non_dialogue"],
            raw_ocr=block.ocr_text,
            expected_source=expected_source,
            predicted_source="",
            source_similarity=1.0 if covered else 0.0,
            source_checked=False,
            expected_translation=expected_translation,
            predicted_translation="",
            translation_similarity=1.0 if covered else 0.0,
            notes=block.review_notes,
        )

    if decision in {"fused", "zone"}:
        return RegressionItem(
            project_path=str(project_path),
            page_index=page_index,
            block_id=block.id,
            decision=decision,
            status=f"{decision}_excluded",
            categories=categories or [decision],
            raw_ocr=block.ocr_text,
            expected_source=expected_source,
            predicted_source="",
            source_similarity=1.0,
            source_checked=False,
            expected_translation=expected_translation,
            predicted_translation="",
            translation_similarity=1.0,
            notes=block.review_notes,
        )

    predicted_source = _predict_source(block.ocr_text)
    source_checked = not expected_source_is_translation_like(expected_source, expected_translation)
    source_similarity = 1.0 if not source_checked else _source_similarity(expected_source, predicted_source)
    source_ok = source_similarity >= source_threshold

    predicted_translation = _predict_translation(predicted_source)
    translation_similarity = 1.0
    translation_status = "not_checked"
    user_changed_translation = bool(
        block.translation_fr.strip()
        and block.raw_translation_fr.strip()
        and text_similarity(block.translation_fr, block.raw_translation_fr) < 0.995
    )
    if expected_translation and (predicted_translation or user_changed_translation):
        translation_similarity = text_similarity(expected_translation, predicted_translation)
        if predicted_translation and translation_similarity >= translation_threshold:
            translation_status = "translation_match"
        elif predicted_translation:
            translation_status = "translation_mismatch"
        else:
            translation_status = "translation_missing_rule"

    if source_ok and translation_status in {"not_checked", "translation_match"}:
        status = "match"
    elif not source_ok and translation_status in {"translation_mismatch", "translation_missing_rule"}:
        status = "source_and_translation_mismatch"
    elif not source_ok:
        status = "source_mismatch"
    else:
        status = translation_status

    return RegressionItem(
        project_path=str(project_path),
        page_index=page_index,
        block_id=block.id,
        decision=decision,
        status=status,
        categories=categories,
        raw_ocr=block.ocr_text,
        expected_source=expected_source,
        predicted_source=predicted_source,
        source_similarity=round(source_similarity, 4),
        source_checked=source_checked,
        expected_translation=expected_translation,
        predicted_translation=predicted_translation,
        translation_similarity=round(translation_similarity, 4),
        notes=block.review_notes,
    )


def run_review_regression(
    project_paths: list[str | Path],
    *,
    source_threshold: float = 0.92,
    translation_threshold: float = 0.85,
) -> RegressionReport:
    paths = discover_review_projects(project_paths)
    items: list[RegressionItem] = []
    for path in paths:
        project = ProjectCache.load(path)
        for page in project.pages:
            for block in page.blocks:
                if _changed_or_reviewed(block):
                    items.append(
                        evaluate_block(
                            path,
                            block,
                            page.page_index,
                            source_threshold,
                            translation_threshold,
                            page_ignore_reason=page_non_reviewable_reason(page.blocks),
                        )
                    )

    status_counts: Counter[str] = Counter(item.status for item in items)
    category_counts: Counter[str] = Counter(category for item in items for category in item.categories)
    evaluated_source = [item for item in items if item.source_checked]
    evaluated_translation = [
        item
        for item in items
        if item.expected_translation
        and (
            bool(item.predicted_translation)
            or item.status in {"translation_missing_rule", "source_and_translation_mismatch"}
        )
    ]
    ignored_items = [item for item in items if item.status in {"ignored_covered", "ignored_uncovered"}]
    source_matches = sum(1 for item in evaluated_source if item.source_similarity >= source_threshold)
    translation_matches = sum(1 for item in evaluated_translation if item.translation_similarity >= translation_threshold)
    ignored_covered = sum(1 for item in ignored_items if item.status == "ignored_covered")
    scores = {
        "source_match_rate": round(source_matches / len(evaluated_source), 4) if evaluated_source else 1.0,
        "translation_rule_match_rate": round(translation_matches / len(evaluated_translation), 4) if evaluated_translation else 1.0,
        "ignored_auto_covered_rate": round(ignored_covered / len(ignored_items), 4) if ignored_items else 1.0,
    }
    return RegressionReport(
        project_count=len(paths),
        block_count=len(items),
        evaluated_source_count=len(evaluated_source),
        source_match_count=source_matches,
        evaluated_translation_count=len(evaluated_translation),
        translation_match_count=translation_matches,
        ignored_count=len(ignored_items),
        ignored_auto_covered_count=ignored_covered,
        status_counts=dict(sorted(status_counts.items())),
        category_counts=dict(sorted(category_counts.items())),
        scores=scores,
        items=items,
    )


def write_regression_report(report: RegressionReport, output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "mangatrad_review_regression_report.json"
    md_path = out / "mangatrad_review_regression_report.md"
    json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# MangaTrad Review Regression",
        "",
        f"- Projets: {report.project_count}",
        f"- Blocs historiques évalués: {report.block_count}",
        f"- Source OK: {report.source_match_count}/{report.evaluated_source_count} ({report.scores['source_match_rate']:.2%})",
        f"- Traductions apprises OK: {report.translation_match_count}/{report.evaluated_translation_count} ({report.scores['translation_rule_match_rate']:.2%})",
        f"- Ignorés auto-couverts: {report.ignored_auto_covered_count}/{report.ignored_count} ({report.scores['ignored_auto_covered_rate']:.2%})",
        "",
        "## Statuts",
        "",
    ]
    for status, count in sorted(report.status_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Catégories", ""])
    for category, count in sorted(report.category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Échecs prioritaires", ""])
    failures = [
        item
        for item in report.items
        if item.status
        in {"source_mismatch", "translation_mismatch", "translation_missing_rule", "source_and_translation_mismatch", "ignored_uncovered"}
    ]
    failures.sort(key=lambda item: (item.status, item.source_similarity, item.translation_similarity))
    if not failures:
        lines.append("Aucun échec prioritaire.")
    for item in failures[:80]:
        lines.extend(
            [
                f"### {item.status} · p{item.page_index + 1} · {item.block_id}",
                "",
                f"- Projet: `{item.project_path}`",
                f"- Décision: `{item.decision}`",
                f"- Catégories: `{', '.join(item.categories)}`",
        f"- Similarité source: {item.source_similarity:.2f}",
                f"- Source vérifiée: `{item.source_checked}`",
                f"- Similarité traduction: {item.translation_similarity:.2f}",
                f"- OCR brut: `{item.raw_ocr}`",
                f"- Source attendue: `{item.expected_source}`",
                f"- Source prédite: `{item.predicted_source}`",
                f"- Traduction attendue: `{item.expected_translation}`",
                f"- Traduction prédite: `{item.predicted_translation}`",
            ]
        )
        if item.notes:
            lines.append(f"- Notes: `{item.notes}`")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
