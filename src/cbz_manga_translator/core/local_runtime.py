from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
import shutil


@dataclass(slots=True)
class RuntimeCheck:
    name: str
    ok: bool
    detail: str
    local_only: bool = True


def cuda_status() -> RuntimeCheck:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return RuntimeCheck("GPU CUDA", True, f"disponible: {name}")
        return RuntimeCheck("GPU CUDA", False, "non disponible, exécution CPU")
    except Exception as exc:  # pragma: no cover - defensive diagnostic helper
        return RuntimeCheck("GPU CUDA", False, f"PyTorch indisponible: {type(exc).__name__}: {exc}")


def package_status(import_name: str, label: str, *, required: bool = True, install_hint: str = "") -> RuntimeCheck:
    found = find_spec(import_name) is not None
    if found:
        return RuntimeCheck(label, True, "installé localement")
    hint = f" — {install_hint}" if install_hint else ""
    if required:
        return RuntimeCheck(label, False, f"absent: installation requise{hint}")
    return RuntimeCheck(label, True, f"optionnel absent: fallback désactivé{hint}")


def tesseract_status() -> RuntimeCheck:
    if find_spec("pytesseract") is None:
        return RuntimeCheck(
            "OCR Tesseract",
            True,
            "optionnel absent: installer avec winget install --id UB-Mannheim.TesseractOCR -e puis python -m pip install pytesseract",
        )
    binary = shutil.which("tesseract")
    if not binary:
        return RuntimeCheck(
            "OCR Tesseract",
            False,
            "pytesseract est installé mais tesseract.exe est absent du PATH",
        )
    try:
        import pytesseract

        version = pytesseract.get_tesseract_version()
        langs = ",".join(pytesseract.get_languages(config=""))
        return RuntimeCheck("OCR Tesseract", True, f"{version}; binaire={binary}; langues={langs}")
    except Exception as exc:
        return RuntimeCheck("OCR Tesseract", False, f"erreur runtime: {type(exc).__name__}: {exc}")


def paddleocr_status() -> RuntimeCheck:
    if find_spec("paddleocr") is None:
        return RuntimeCheck(
            "OCR PaddleOCR",
            True,
            "optionnel absent: installer avec python -m pip install paddleocr",
        )
    try:
        import paddleocr

        return RuntimeCheck("OCR PaddleOCR", True, f"installé: {getattr(paddleocr, '__version__', 'version inconnue')}")
    except Exception as exc:
        return RuntimeCheck("OCR PaddleOCR", False, f"import impossible: {type(exc).__name__}: {exc}")


def collect_local_runtime_checks(*, translation_backend: str, server_url: str, gpu_requested: bool) -> list[RuntimeCheck]:
    """Return non-network runtime diagnostics for the local/free execution policy.

    The function intentionally does not contact any model registry, Tesseract, PaddleOCR,
    or the optional HTTP server. It only reports whether the configured execution
    path is local and whether import-time dependencies look present.
    """

    checks = [
        RuntimeCheck("Politique", True, "OCR/traduction exécutés localement; aucune dépendance Hugging Face configurée"),
        package_status("easyocr", "OCR EasyOCR", required=True, install_hint="python -m pip install easyocr"),
        package_status("argostranslate", "Argos Translate", required=True, install_hint="python -m pip install argostranslate"),
        package_status("torch", "PyTorch", required=True, install_hint="installer PyTorch CUDA/CPU adapté"),
        tesseract_status(),
        paddleocr_status(),
    ]
    try:
        from cbz_manga_translator.translate.argos import ArgosTranslator

        for label, ok, detail in ArgosTranslator.local_translation_status():
            checks.append(RuntimeCheck(label, ok, detail))
    except Exception as exc:  # pragma: no cover - diagnostic helper must not crash GUI
        checks.append(RuntimeCheck("Modèles Argos", False, f"impossible de vérifier les modèles: {type(exc).__name__}: {exc}"))
    checks.append(cuda_status())
    if translation_backend == "server":
        checks.append(
            RuntimeCheck(
                "Traduction",
                True,
                f"serveur Argos local configuré: {server_url.strip() or 'URL vide'}; bouton Tester serveur pour vérifier",
            )
        )
    else:
        checks.append(RuntimeCheck("Traduction", True, "Argos intégré dans l’application; modèles .argosmodel requis"))
    if gpu_requested and not checks[-2].ok:
        checks.append(RuntimeCheck("GPU demandé", False, "GPU coché mais CUDA indisponible; retour CPU probable"))
    return checks


def format_runtime_checks(checks: list[RuntimeCheck]) -> str:
    lines: list[str] = []
    for check in checks:
        marker = "OK" if check.ok else "ATTENTION"
        scope = "local" if check.local_only else "non-local"
        lines.append(f"[{marker}] {check.name} ({scope}) — {check.detail}")
    return "\n".join(lines)
