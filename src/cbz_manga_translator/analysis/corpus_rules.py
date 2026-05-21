from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z][A-Za-z'’-]{2,}\b")
_FRENCH_STOP = {
    "bonjour", "quoi", "pourquoi", "comment", "avec", "sans", "dans", "pour", "mais", "donc",
    "alors", "vous", "nous", "elle", "elles", "ils", "cela", "cette", "comme", "plus", "moins",
    "bien", "fait", "faire", "être", "avoir", "suis", "sont", "était", "étais", "mon", "ton",
    "son", "des", "une", "les", "aux", "est", "pas", "que", "qui", "sur", "par", "ici",
}
_ENGLISH_COMMON = {
    "the", "and", "that", "this", "with", "from", "have", "will", "would", "could", "should", "what",
    "when", "where", "why", "there", "here", "your", "you", "they", "them", "their", "been", "being",
    "because", "into", "about", "after", "before", "world", "friend", "friends", "girl", "time",
    "work", "death", "door", "food", "shelter", "steal", "orphanage", "tiger", "bomb", "bandit",
}
_SAFE_NAME_STOP = {
    "The", "This", "That", "Then", "With", "From", "Just", "Maybe", "Well", "But", "And", "Now", "You",
    "They", "Get", "Know", "Out", "How", "When", "What", "Who", "Someone", "Chapter", "Story",
}


@dataclass(slots=True)
class LearnedCorpusProfile:
    summary: dict[str, Any]
    high_risk_examples: list[dict[str, Any]]
    suspicious_ocr_tokens: list[dict[str, Any]]
    source_residue_tokens: list[dict[str, Any]]
    probable_name_candidates: list[dict[str, Any]]
    repeated_sources: list[dict[str, Any]]
    learned_token_weights: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _find_analysis_file(path: Path, filename: str) -> Path:
    direct = path / filename
    if direct.exists():
        return direct
    matches = list(path.rglob(filename))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"{filename} introuvable sous {path}")
    raise FileNotFoundError(f"Plusieurs {filename} trouvés sous {path}: {matches[:5]}")


def read_review_rows(analysis_path: str | Path) -> list[dict[str, str]]:
    root = Path(analysis_path)
    csv_path = _find_analysis_file(root, "mangatrad_review_blocks.csv")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _tokens(text: str) -> list[str]:
    return [token.strip("'’-") for token in _WORD_RE.findall(text or "") if token.strip("'’-")]


def _source_text(row: dict[str, str]) -> str:
    return (row.get("source_for_review") or row.get("normalized_source_text") or row.get("ocr_corrected_text") or row.get("ocr_text") or "").strip()


def _risk(row: dict[str, str]) -> int:
    try:
        return int(float(row.get("risk_score") or 0))
    except ValueError:
        return 0


def _is_high_risk(row: dict[str, str]) -> bool:
    return _risk(row) >= 55 or (row.get("suggested_action") or "") == "review_high"


def _weird_ocr_token(token: str) -> bool:
    if len(token) < 3:
        return False
    if re.search(r"[0-9$]", token):
        return True
    if re.search(r"[A-Z][a-z][A-Z]|[a-z][A-Z]", token):
        return True
    lowered = token.lower()
    if lowered in _ENGLISH_COMMON:
        return False
    return bool(re.search(r"(?:l{2}|rlp|lnn|olgh|lmi|p[e]?house|nestern|wopld|wolld|colld|fopm|folr|t0)", lowered))


def build_learned_profile(rows: list[dict[str, str]], *, max_items: int = 120) -> LearnedCorpusProfile:
    suspicious = Counter()
    suspicious_high = Counter()
    residue = Counter()
    residue_high = Counter()
    name_counter = Counter()
    source_counter = Counter()
    source_translation_counter: dict[str, Counter[str]] = defaultdict(Counter)
    token_high = Counter()
    token_total = Counter()
    series_counter = Counter()

    high_examples: list[dict[str, Any]] = []
    for row in rows:
        source = _source_text(row)
        translation = row.get("translation_fr") or ""
        risk = _risk(row)
        high = _is_high_risk(row)
        series = row.get("series_label") or "unknown"
        series_counter[series] += 1
        source_counter[source] += 1
        if source:
            source_translation_counter[source][translation] += 1

        for token in _tokens(source):
            normalized = token.lower()
            token_total[normalized] += 1
            if high:
                token_high[normalized] += 1
            if _weird_ocr_token(token):
                suspicious[token] += 1
                if high:
                    suspicious_high[token] += 1

        source_tokens = {token.lower() for token in _tokens(source) if len(token) >= 4}
        translation_tokens = {token.lower() for token in _tokens(translation) if len(token) >= 4}
        for token in sorted((source_tokens & translation_tokens) - _FRENCH_STOP):
            residue[token] += 1
            if high:
                residue_high[token] += 1

        for token in _CAPITALIZED_RE.findall(source):
            if token not in _SAFE_NAME_STOP and token.lower() not in _ENGLISH_COMMON:
                name_counter[token] += 1

        if high:
            high_examples.append({
                "risk_score": risk,
                "series_label": series,
                "page_number": row.get("page_number", ""),
                "block_id": row.get("block_id", ""),
                "source": source,
                "translation_fr": translation,
                "reasons": row.get("risk_reasons", ""),
                "warnings": row.get("quality_warnings", ""),
            })

    def suspicious_rows() -> list[dict[str, Any]]:
        rows_out = []
        for token, count in suspicious.most_common():
            rows_out.append({"token": token, "count": count, "high_risk_count": suspicious_high[token]})
        return rows_out[:max_items]

    def residue_rows() -> list[dict[str, Any]]:
        rows_out = []
        for token, count in residue.most_common():
            # Ignore likely French words that slipped through simple filtering.
            if token in _FRENCH_STOP:
                continue
            rows_out.append({"token": token, "count": count, "high_risk_count": residue_high[token]})
        return rows_out[:max_items]

    repeated = []
    for source, count in source_counter.most_common():
        if count < 2 or not source:
            continue
        translations = source_translation_counter[source]
        repeated.append({
            "source": source,
            "count": count,
            "translations": [{"translation_fr": text, "count": c} for text, c in translations.most_common(5)],
        })

    weights = []
    for token, total in token_total.items():
        if total < 2:
            continue
        high = token_high[token]
        # Simple smoothed high-risk likelihood. This is intentionally transparent
        # rather than a black-box model.
        weight = (high + 1) / (total + 2)
        if weight >= 0.55:
            weights.append({"token": token, "count": total, "high_risk_count": high, "risk_weight": round(weight, 4)})
    weights.sort(key=lambda row: (-row["risk_weight"], -row["count"], row["token"]))

    high_examples.sort(key=lambda row: -int(row["risk_score"]))
    summary = {
        "rows": len(rows),
        "high_risk_rows": sum(1 for row in rows if _is_high_risk(row)),
        "medium_risk_rows": sum(1 for row in rows if 25 <= _risk(row) < 55),
        "probably_ok_rows": sum(1 for row in rows if _risk(row) < 25),
        "series_count": len(series_counter),
        "top_series": [{"series_label": s, "blocks": c} for s, c in series_counter.most_common(20)],
    }
    return LearnedCorpusProfile(
        summary=summary,
        high_risk_examples=high_examples[:max_items],
        suspicious_ocr_tokens=suspicious_rows(),
        source_residue_tokens=residue_rows(),
        probable_name_candidates=[{"term": t, "count": c} for t, c in name_counter.most_common(max_items)],
        repeated_sources=repeated[:max_items],
        learned_token_weights=weights[:max_items],
    )


def write_learned_profile(profile: LearnedCorpusProfile, output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    profile_path = out / "mangatrad_learned_profile.json"
    report_path = out / "mangatrad_learned_report.md"
    glossary_path = out / "mangatrad_project_glossary_seed.txt"
    residue_path = out / "mangatrad_qc_residue_words.txt"

    profile_path.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    glossary_lines = [item["term"] for item in profile.probable_name_candidates if int(item["count"]) >= 1]
    glossary_path.write_text("\n".join(glossary_lines) + ("\n" if glossary_lines else ""), encoding="utf-8")
    residue_lines = [item["token"] for item in profile.source_residue_tokens if int(item["count"]) >= 1]
    residue_path.write_text("\n".join(residue_lines) + ("\n" if residue_lines else ""), encoding="utf-8")

    lines = [
        "# MangaTrad learned corpus profile",
        "",
        "## Summary",
        "",
    ]
    for key, value in profile.summary.items():
        if key != "top_series":
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Top series", ""])
    for row in profile.summary.get("top_series", [])[:20]:
        lines.append(f"- {row['series_label']}: {row['blocks']} blocks")
    lines.extend(["", "## Suspicious OCR tokens", ""])
    for row in profile.suspicious_ocr_tokens[:40]:
        lines.append(f"- `{row['token']}` — count={row['count']}, high={row['high_risk_count']}")
    lines.extend(["", "## Source residue tokens copied into translations", ""])
    for row in profile.source_residue_tokens[:40]:
        lines.append(f"- `{row['token']}` — count={row['count']}, high={row['high_risk_count']}")
    lines.extend(["", "## Learned token risk weights", ""])
    for row in profile.learned_token_weights[:40]:
        lines.append(f"- `{row['token']}` — weight={row['risk_weight']}, high={row['high_risk_count']}/{row['count']}")
    lines.extend(["", "## High risk examples", ""])
    for row in profile.high_risk_examples[:20]:
        lines.append(f"- score={row['risk_score']} `{row['source']}` → `{row['translation_fr']}`")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"profile": profile_path, "report": report_path, "glossary": glossary_path, "residue_words": residue_path}
