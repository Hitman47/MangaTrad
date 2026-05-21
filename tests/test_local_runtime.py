from __future__ import annotations

from cbz_manga_translator.core.local_runtime import collect_local_runtime_checks, format_runtime_checks


def test_collect_local_runtime_checks_reports_local_policy() -> None:
    checks = collect_local_runtime_checks(
        translation_backend="embedded",
        server_url="http://127.0.0.1:8765",
        gpu_requested=False,
    )

    assert any(check.name == "Politique" and check.ok for check in checks)
    assert any(check.name == "OCR EasyOCR" for check in checks)
    assert any(check.name == "Traduction" and "Argos intégré" in check.detail for check in checks)
    assert "OCR/traduction exécutés localement" in format_runtime_checks(checks)


def test_collect_local_runtime_checks_describes_server_backend_without_network_call() -> None:
    checks = collect_local_runtime_checks(
        translation_backend="server",
        server_url="http://127.0.0.1:8765",
        gpu_requested=True,
    )

    assert any(check.name == "Traduction" and "serveur Argos local" in check.detail for check in checks)
