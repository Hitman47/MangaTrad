from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.translate.argos import ArgosTranslationError, ArgosTranslator


def _print_pairs() -> None:
    pairs = ArgosTranslator.installed_pairs()
    if not pairs:
        print("Aucune paire Argos installée.")
    else:
        print("Paires Argos installées:")
        for source, target in pairs:
            print(f"- {source} -> {target}")

    print("\nStatut requis par MangaTrad:")
    for label, ok, detail in ArgosTranslator.local_translation_status():
        marker = "OK" if ok else "MANQUANT"
        print(f"- [{marker}] {label}: {detail}")


def _install_index_pairs(pairs: list[str]) -> None:
    for pair in pairs:
        if ":" not in pair:
            raise ArgosTranslationError(f"Format de paire invalide: {pair}. Format attendu: en:fr")
        source, target = [part.strip().lower() for part in pair.split(":", 1)]
        if not source or not target:
            raise ArgosTranslationError(f"Format de paire invalide: {pair}. Format attendu: en:fr")
        print(f"Recherche Argos index: {source} -> {target}")
        installed = ArgosTranslator.install_package_from_index(source, target)
        if installed:
            print(f"Installé depuis l’index Argos: {source} -> {target}")
        else:
            print(f"Non trouvé dans l’index Argos: {source} -> {target}")


def _bootstrap_basic() -> None:
    print("Installation minimale Argos pour MangaTrad: en->fr, ja->en, ja->fr si disponible")
    for source, target, installed in ArgosTranslator.bootstrap_basic_packages():
        marker = "installé" if installed else "non trouvé"
        print(f"- {source} -> {target}: {marker}")
    print("\nNote: ja->fr direct peut être absent. MangaTrad utilise alors ja->en + en->fr.")


def _test_translation(source_lang: str, text: str) -> None:
    translator = ArgosTranslator()
    result = translator.translate_texts([text], source_lang)  # type: ignore[arg-type]
    print(result[0] if result else "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gestion locale des packages Argos Translate (.argosmodel) sans Hugging Face."
    )
    parser.add_argument("--install", nargs="*", type=Path, help="Installer un ou plusieurs fichiers .argosmodel locaux.")
    parser.add_argument(
        "--install-index",
        nargs="*",
        metavar="SRC:DST",
        help="Télécharger/installer une ou plusieurs paires depuis l’index Argos, ex: en:fr ja:en.",
    )
    parser.add_argument(
        "--bootstrap-basic",
        action="store_true",
        help="Installer le minimum recommandé pour MangaTrad: en->fr et ja->en, plus ja->fr si disponible.",
    )
    parser.add_argument("--list", action="store_true", help="Lister les paires de traduction Argos installées.")
    parser.add_argument(
        "--test",
        nargs=2,
        metavar=("LANG", "TEXT"),
        help="Tester une traduction locale vers le français, ex: --test en \"hello\".",
    )
    args = parser.parse_args(argv)

    did_action = False
    if args.install:
        did_action = True
        for package_path in args.install:
            ArgosTranslator.install_package_file(package_path)
            print(f"Installé: {package_path}")
    if args.install_index:
        did_action = True
        _install_index_pairs(args.install_index)
    if args.bootstrap_basic:
        did_action = True
        _bootstrap_basic()
    if args.test:
        did_action = True
        _test_translation(args.test[0], args.test[1])
    if args.list or not did_action:
        _print_pairs()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
