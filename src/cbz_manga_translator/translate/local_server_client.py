from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import fields
from typing import Any

from cbz_manga_translator.core.models import OcrBlock, SourceLang


class LocalTranslationServerError(RuntimeError):
    """Raised when the local translation HTTP server cannot be reached or returns an invalid response."""


class LocalTranslationServerClient:
    """Small dependency-free HTTP client for the optional local Argos server.

    The client deliberately mirrors the embedded ``ArgosTranslator.translate_blocks``
    method so the GUI can switch backend without changing the workflow.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8765", timeout: float = 120.0) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.timeout = timeout

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned:
            return "http://127.0.0.1:8765"
        if not cleaned.startswith(("http://", "https://")):
            cleaned = f"http://{cleaned}"
        return cleaned.rstrip("/")

    def health(self) -> dict[str, Any]:
        return self._post_json("/health", {})

    def preload(self, source_langs: list[SourceLang], *, use_gpu: bool = False) -> dict[str, Any]:
        return self._post_json("/preload", {"source_langs": source_langs, "use_gpu": use_gpu})

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
        payload = {
            "source_lang": source_lang,
            "blocks": [block.to_dict() for block in blocks],
            "use_gpu": use_gpu,
            "raw_terms": raw_terms or "",
            "normalize_english": normalize_english,
            "use_builtin_glossary": use_builtin_glossary,
            "force": force,
        }
        response = self._post_json("/translate-blocks", payload)
        returned = response.get("blocks")
        if not isinstance(returned, list):
            raise LocalTranslationServerError("Réponse invalide du serveur local: champ 'blocks' absent ou invalide.")
        updated = [OcrBlock.from_dict(item) for item in returned]
        self._copy_blocks_in_place(blocks, updated)
        return blocks

    @staticmethod
    def _copy_blocks_in_place(targets: list[OcrBlock], updates: list[OcrBlock]) -> None:
        by_id = {block.id: block for block in updates}
        editable_fields = [field.name for field in fields(OcrBlock)]
        for target in targets:
            update = by_id.get(target.id)
            if update is None:
                continue
            for name in editable_fields:
                setattr(target, name, getattr(update, name))

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - user-provided local URL by design
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LocalTranslationServerError(f"Serveur local HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LocalTranslationServerError(f"Serveur local inaccessible ({url}): {exc.reason}") from exc
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LocalTranslationServerError(f"Réponse JSON invalide du serveur local: {body[:300]}") from exc
        if not isinstance(decoded, dict):
            raise LocalTranslationServerError("Réponse invalide du serveur local: objet JSON attendu.")
        if decoded.get("error"):
            raise LocalTranslationServerError(str(decoded["error"]))
        return decoded
