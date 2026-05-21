from __future__ import annotations

import argparse
import shutil
from importlib.util import find_spec


def _print_commands() -> None:
    print("Commandes Windows recommandées, dans le venv actif :")
    print()
    print("# Vérifier le Python utilisé")
    print("python -c \"import sys; print(sys.executable)\"")
    print()
    print("# Tesseract: installer le binaire Windows, puis le wrapper Python")
    print("winget install --id UB-Mannheim.TesseractOCR -e")
    print("python -m pip install pytesseract")
    print("tesseract --version")
    print("tesseract --list-langs")
    print("python -c \"import pytesseract; print(pytesseract.get_tesseract_version()); print(pytesseract.get_languages(config=''))\"")
    print()
    print("# PaddleOCR: backend optionnel plus lourd")
    print("python -m pip install paddleocr")
    print("python -c \"import paddleocr; print('PaddleOCR OK', getattr(paddleocr, '__version__', 'unknown'))\"")
    print()
    print("# Vérifier ce que MangaTrad voit")
    print("python -m cbz_manga_translator.ocr_setup --check")


def _check() -> int:
    print("=== OCR backends MangaTrad ===")
    code = 0

    try:
        import easyocr  # noqa: F401

        print("[OK] EasyOCR: importable")
    except Exception as exc:
        print(f"[ERREUR] EasyOCR: {type(exc).__name__}: {exc}")
        code = 1

    try:
        import torch

        if torch.cuda.is_available():
            print(f"[OK] CUDA PyTorch: {torch.cuda.get_device_name(0)}")
        else:
            print("[INFO] CUDA PyTorch: non disponible, OCR sur CPU")
    except Exception as exc:
        print(f"[ERREUR] PyTorch: {type(exc).__name__}: {exc}")
        code = 1

    tesseract_bin = shutil.which("tesseract")
    if tesseract_bin:
        print(f"[OK] tesseract.exe: {tesseract_bin}")
    else:
        print("[INFO] tesseract.exe: introuvable dans PATH")

    if find_spec("pytesseract") is not None:
        try:
            import pytesseract

            print(f"[OK] pytesseract: {pytesseract.get_tesseract_version()}")
            try:
                print(f"[INFO] langues Tesseract: {', '.join(pytesseract.get_languages(config=''))}")
            except Exception as exc:
                print(f"[INFO] langues Tesseract non lisibles: {exc}")
        except Exception as exc:
            print(f"[ATTENTION] pytesseract importable mais non fonctionnel: {type(exc).__name__}: {exc}")
    else:
        print("[INFO] pytesseract: non installé")

    if find_spec("paddleocr") is not None:
        try:
            import paddleocr

            print(f"[OK] PaddleOCR: {getattr(paddleocr, '__version__', 'unknown')}")
        except Exception as exc:
            print(f"[ATTENTION] PaddleOCR importable mais erreur: {type(exc).__name__}: {exc}")
    else:
        print("[INFO] PaddleOCR: non installé")

    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostic et commandes d'installation OCR pour MangaTrad.")
    parser.add_argument("--commands", action="store_true", help="affiche les commandes d'installation Windows")
    parser.add_argument("--check", action="store_true", help="vérifie les backends OCR visibles par Python")
    args = parser.parse_args(argv)

    if args.commands:
        _print_commands()
    if args.check or not args.commands:
        return _check()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
