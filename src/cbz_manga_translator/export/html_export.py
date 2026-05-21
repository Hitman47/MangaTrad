from __future__ import annotations

import html
from pathlib import Path

from cbz_manga_translator.core.cbz_reader import CbzReader
from cbz_manga_translator.core.models import ProjectData


STYLE = """
:root { color-scheme: dark; }
body { margin: 0; font-family: system-ui, sans-serif; background: #111; color: #eee; }
header { position: sticky; top: 0; background: #181818; border-bottom: 1px solid #333; padding: 12px 18px; z-index: 1; }
.page { display: grid; grid-template-columns: minmax(320px, 52vw) 1fr; gap: 18px; padding: 18px; border-bottom: 1px solid #333; }
.page img { width: 100%; height: auto; background: #222; }
.blocks { display: flex; flex-direction: column; gap: 12px; }
.block { border: 1px solid #444; border-radius: 10px; padding: 10px 12px; background: #1a1a1a; }
.meta { color: #aaa; font-size: 0.85rem; margin-bottom: 6px; }
.source { color: #bbb; white-space: pre-wrap; }
.diagnostic { color: #999; font-size: 0.9rem; margin-top: 6px; white-space: pre-wrap; }
.translation { margin-top: 8px; font-size: 1.05rem; white-space: pre-wrap; }
.raw-translation { color: #aaa; font-size: 0.9rem; margin-top: 6px; white-space: pre-wrap; }
.warnings { color: #ffbd6e; font-size: 0.9rem; margin-top: 6px; white-space: pre-wrap; }
.status-validated { border-color: #4c9f5f; }
.status-review { border-color: #d19b43; }
.status-ignored { opacity: 0.55; }
.empty { color: #888; font-style: italic; }
@media (max-width: 900px) { .page { grid-template-columns: 1fr; } }
""".strip()


def export_html_project(reader: CbzReader, project: ProjectData, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    images_dir = output / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    page_fragments: list[str] = []
    for page in project.pages:
        image_target = images_dir / Path(page.image_name).name
        if not image_target.exists():
            image_target.write_bytes(reader.read_image_bytes(page.image_name))
        blocks_html = []
        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            bbox = ",".join(str(v) for v in block.bbox)
            confidence = "" if block.confidence is None else f" · conf. {block.confidence:.2f}"
            source = html.escape(block.ocr_text)
            corrected = html.escape(block.ocr_corrected_text)
            normalized = html.escape(block.normalized_source_text)
            raw_translation = html.escape(block.raw_translation_fr)
            translation = html.escape(block.translation_fr or "[non traduit]")
            diagnostics = ""
            if corrected or normalized:
                diagnostics = (
                    f'<div class="diagnostic"><strong>OCR corrigé:</strong> {corrected or "—"}</div>'
                    f'<div class="diagnostic"><strong>Texte normalisé:</strong> {normalized or "—"}</div>'
                )
            raw_html = f'<div class="raw-translation"><strong>Trad brute:</strong> {raw_translation}</div>' if raw_translation else ""
            warning_html = ""
            if block.quality_warnings:
                warning_html = '<div class="warnings"><strong>QC:</strong> ' + html.escape(" ; ".join(block.quality_warnings)) + '</div>'
            status_class = f"status-{block.manual_status}"
            blocks_html.append(
                f"""
                <article class="block {html.escape(status_class)}" id="{html.escape(block.id)}">
                  <div class="meta">#{block.reading_order} · {html.escape(block.source_lang.upper())} · bbox {bbox}{confidence} · statut {html.escape(block.manual_status)}</div>
                  <div class="source"><strong>OCR brut:</strong> {source}</div>
                  {diagnostics}
                  {raw_html}
                  {warning_html}
                  <div class="translation"><strong>FR finale:</strong> {translation}</div>
                </article>
                """.strip()
            )
        if not blocks_html:
            blocks_html.append('<p class="empty">Aucun bloc OCR pour cette page.</p>')
        rel_image = f"images/{html.escape(image_target.name)}"
        page_fragments.append(
            f"""
            <section class="page" id="page-{page.page_index}">
              <div><img src="{rel_image}" alt="{html.escape(page.image_name)}"></div>
              <div class="blocks">
                <h2>Page {page.page_index + 1} — {html.escape(page.image_name)}</h2>
                {''.join(blocks_html)}
              </div>
            </section>
            """.strip()
        )

    index = output / "index.html"
    index.write_text(
        f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CBZ manga translation</title>
  <style>{STYLE}</style>
</head>
<body>
  <header><strong>CBZ manga translation</strong> — prototype OCR + Argos</header>
  {''.join(page_fragments)}
</body>
</html>
""",
        encoding="utf-8",
    )
    return index
