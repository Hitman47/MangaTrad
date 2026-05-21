from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from cbz_manga_translator import __version__
from cbz_manga_translator.core.models import OcrBlock, SourceLang
from cbz_manga_translator.translate.argos import ArgosTranslator


class TranslationRequestError(ValueError):
    """Client-side request error for the local translation server."""


def _as_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _as_source_lang(value: Any) -> SourceLang:
    if value not in {"en", "ja"}:
        raise TranslationRequestError("source_lang doit valoir 'en' ou 'ja'.")
    return value


def translate_texts_request(
    translator: ArgosTranslator,
    payload: dict[str, Any],
    *,
    default_use_gpu: bool = False,
) -> dict[str, Any]:
    source_lang = _as_source_lang(payload.get("source_lang", "en"))
    texts = payload.get("texts")
    if not isinstance(texts, list) or not all(isinstance(item, str) for item in texts):
        raise TranslationRequestError("texts doit être une liste de chaînes.")
    translations = translator.translate_texts(
        texts,
        source_lang,
        use_gpu=_as_bool(payload, "use_gpu", default_use_gpu),
        raw_terms=str(payload.get("raw_terms", "")),
        normalize_english=_as_bool(payload, "normalize_english", True),
        use_builtin_glossary=_as_bool(payload, "use_builtin_glossary", True),
    )
    return {"translations": translations, "source_lang": source_lang, "backend": "argos"}


def translate_blocks_request(
    translator: ArgosTranslator,
    payload: dict[str, Any],
    *,
    default_use_gpu: bool = False,
) -> dict[str, Any]:
    source_lang = _as_source_lang(payload.get("source_lang", "en"))
    raw_blocks = payload.get("blocks")
    if not isinstance(raw_blocks, list):
        raise TranslationRequestError("blocks doit être une liste de blocs OCR.")
    blocks = [OcrBlock.from_dict(item) for item in raw_blocks]
    translated = translator.translate_blocks(
        blocks,
        source_lang,
        use_gpu=_as_bool(payload, "use_gpu", default_use_gpu),
        raw_terms=str(payload.get("raw_terms", "")),
        normalize_english=_as_bool(payload, "normalize_english", True),
        use_builtin_glossary=_as_bool(payload, "use_builtin_glossary", True),
        force=_as_bool(payload, "force", False),
    )
    return {"blocks": [block.to_dict() for block in translated], "source_lang": source_lang, "backend": "argos"}


def preload_request(
    translator: ArgosTranslator,
    payload: dict[str, Any],
    *,
    default_use_gpu: bool = False,
) -> dict[str, Any]:
    langs = payload.get("source_langs", ["en", "ja"])
    if isinstance(langs, str):
        langs = [langs]
    if not isinstance(langs, list):
        raise TranslationRequestError("source_langs doit être une chaîne ou une liste.")
    loaded: list[str] = []
    for raw_lang in langs:
        lang = _as_source_lang(raw_lang)
        translator.preload(lang, use_gpu=_as_bool(payload, "use_gpu", default_use_gpu))
        loaded.append(lang)
    return {"loaded": loaded, "backend": "argos"}


class TranslationHandler(BaseHTTPRequestHandler):
    server_version = f"CBZMangaTranslator/{__version__}"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        try:
            payload = self._read_payload()
            result = self._dispatch(payload)
            self._write_json(200, result)
        except TranslationRequestError as exc:
            self._write_json(400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive server boundary
            self._write_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def _read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TranslationRequestError("JSON invalide.") from exc
        if not isinstance(data, dict):
            raise TranslationRequestError("Le corps de requête doit être un objet JSON.")
        return data

    def _dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        translator: ArgosTranslator = self.server.translator  # type: ignore[attr-defined]
        default_use_gpu: bool = self.server.use_gpu  # type: ignore[attr-defined]
        if self.path == "/health":
            return {
                "ok": True,
                "version": __version__,
                "backend": "argos",
                "use_gpu_default": default_use_gpu,
                "cuda_available": ArgosTranslator.cuda_available(),
            }
        if self.path == "/preload":
            return preload_request(translator, payload, default_use_gpu=default_use_gpu)
        if self.path == "/translate":
            return translate_texts_request(translator, payload, default_use_gpu=default_use_gpu)
        if self.path == "/translate-blocks":
            return translate_blocks_request(translator, payload, default_use_gpu=default_use_gpu)
        raise TranslationRequestError(f"Endpoint inconnu: {self.path}")

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class TranslationHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], *, use_gpu: bool, quiet: bool) -> None:
        super().__init__(server_address, handler_cls)
        self.translator = ArgosTranslator()
        self.use_gpu = use_gpu
        self.quiet = quiet


def serve(host: str = "127.0.0.1", port: int = 8765, *, use_gpu: bool = False, preload: list[SourceLang] | None = None, quiet: bool = False) -> None:
    server = TranslationHttpServer((host, port), TranslationHandler, use_gpu=use_gpu, quiet=quiet)
    if preload:
        for lang in preload:
            server.translator.preload(lang, use_gpu=use_gpu)
    print(f"CBZ Manga Translator local server {__version__} — http://{host}:{port} — backend=argos — gpu={use_gpu}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur local.")
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Argos translation server for CBZ Manga Translator. Requires installed .argosmodel packages.")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute. Garde 127.0.0.1 pour usage local uniquement.")
    parser.add_argument("--port", type=int, default=8765, help="Port HTTP local.")
    parser.add_argument("--gpu", action="store_true", help="Utiliser CUDA si PyTorch détecte un GPU.")
    parser.add_argument("--preload", nargs="*", choices=["en", "ja"], default=[], help="Vérifier/charger les paires Argos installées au démarrage.")
    parser.add_argument("--quiet", action="store_true", help="Réduire les logs HTTP.")
    args = parser.parse_args(argv)
    serve(args.host, args.port, use_gpu=args.gpu, preload=args.preload, quiet=args.quiet)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
