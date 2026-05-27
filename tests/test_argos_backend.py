from __future__ import annotations

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.translate.argos import ArgosTranslator


def test_argos_bypasses_package_for_deterministic_overrides(monkeypatch) -> None:
    translator = ArgosTranslator()

    def fail_chain(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Argos package should not be loaded for deterministic overrides")

    monkeypatch.setattr(translator, "_translation_chain", fail_chain)
    blocks = [
        OcrBlock(id="b1", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="Aww:"),
        OcrBlock(id="b2", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="please Inhook this"),
    ]

    translator.translate_blocks(blocks, "en")

    assert blocks[0].translation_fr == "Aww..."
    assert blocks[1].ocr_corrected_text == "please unhook this"
    assert blocks[1].translation_fr == "Décroche ça, s’il te plaît."


class _FakeLanguage:
    def __init__(self, code: str) -> None:
        self.code = code
        self._targets: dict[str, object] = {}

    def allow(self, target: "_FakeLanguage") -> None:
        self._targets[target.code] = object()

    def get_translation(self, target: "_FakeLanguage") -> object | None:
        return self._targets.get(target.code)


class _FakeTranslateModule:
    def __init__(self, languages: list[_FakeLanguage]) -> None:
        self._languages = languages

    def get_installed_languages(self) -> list[_FakeLanguage]:
        return self._languages


def test_argos_installed_pairs_uses_get_translation_api(monkeypatch) -> None:
    en = _FakeLanguage("en")
    fr = _FakeLanguage("fr")
    ja = _FakeLanguage("ja")
    en.allow(fr)
    ja.allow(en)

    fake_translate = _FakeTranslateModule([en, fr, ja])
    monkeypatch.setattr(ArgosTranslator, "_argostranslate_modules", staticmethod(lambda: (object(), fake_translate)))

    assert ArgosTranslator.installed_pairs() == [("en", "fr"), ("ja", "en")]

class _FakePackageEntry:
    def __init__(self, from_code: str, to_code: str) -> None:
        self.from_code = from_code
        self.to_code = to_code

    def download(self) -> str:
        return f"/tmp/{self.from_code}_{self.to_code}.argosmodel"


class _FakePackageModule:
    def __init__(self) -> None:
        self.installed_paths: list[str] = []

    def update_package_index(self) -> None:
        return None

    def get_available_packages(self) -> list[_FakePackageEntry]:
        return [_FakePackageEntry("en", "fr"), _FakePackageEntry("ja", "en")]

    def install_from_path(self, path: str) -> None:
        self.installed_paths.append(path)


def test_argos_install_package_from_index(monkeypatch) -> None:
    fake_package = _FakePackageModule()
    fake_translate = _FakeTranslateModule([])
    monkeypatch.setattr(ArgosTranslator, "_argostranslate_modules", staticmethod(lambda: (fake_package, fake_translate)))

    assert ArgosTranslator.install_package_from_index("en", "fr") is True
    assert fake_package.installed_paths == ["/tmp/en_fr.argosmodel"]
    assert ArgosTranslator.install_package_from_index("ja", "fr") is False


def test_argos_local_translation_status_detects_pivot(monkeypatch) -> None:
    en = _FakeLanguage("en")
    fr = _FakeLanguage("fr")
    ja = _FakeLanguage("ja")
    en.allow(fr)
    ja.allow(en)

    fake_translate = _FakeTranslateModule([en, fr, ja])
    monkeypatch.setattr(ArgosTranslator, "_argostranslate_modules", staticmethod(lambda: (object(), fake_translate)))

    statuses = dict((label, (ok, detail)) for label, ok, detail in ArgosTranslator.local_translation_status())
    assert statuses["Argos en->fr"][0] is True
    assert statuses["Argos ja->fr"][0] is True
    assert "via pivot" in statuses["Argos ja->fr"][1]


def test_argos_configure_device_uses_minisbd(monkeypatch) -> None:
    import os
    import argostranslate.settings as settings

    settings.chunk_type = settings.ChunkType.ARGOSTRANSLATE

    monkeypatch.setenv("ARGOS_DEVICE_TYPE", "cuda")
    ArgosTranslator._configure_device(use_gpu=False)

    assert settings.chunk_type == settings.ChunkType.MINISBD
    assert os.environ["ARGOS_DEVICE_TYPE"] == "cpu"
    assert settings.device == "cpu"


def test_argos_configure_device_clears_cached_stanza_translations(monkeypatch) -> None:
    import argostranslate.translate as translate

    class _CachedLanguages:
        cleared = False

        def cache_clear(self) -> None:
            self.cleared = True

    cached_languages = _CachedLanguages()
    stale_translates = [object()]
    monkeypatch.setattr(translate, "get_installed_languages", cached_languages)
    monkeypatch.setattr(translate, "installed_translates", stale_translates)

    ArgosTranslator._configure_device(use_gpu=False)

    assert cached_languages.cleared is True
    assert stale_translates == []


class _CudaFailTranslation:
    def translate(self, text: str) -> str:
        raise RuntimeError("CUDA failed with error out of memory")


class _CpuTranslation:
    def translate(self, text: str) -> str:
        return f"fr:{text}"


def test_argos_translation_falls_back_to_cpu_on_cuda_oom(monkeypatch) -> None:
    translator = ArgosTranslator()
    calls: list[bool] = []

    def fake_chain(_source_lang: str, *, use_gpu: bool):  # type: ignore[no-untyped-def]
        calls.append(use_gpu)
        return [_CudaFailTranslation()] if use_gpu else [_CpuTranslation()]

    monkeypatch.setattr(translator, "_translation_chain", fake_chain)
    monkeypatch.setattr(translator, "_clear_cuda_cache", lambda: None)
    block = OcrBlock(id="b1", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="Hello there")

    translator.translate_blocks([block], "en", use_gpu=True)

    assert calls == [True, False]
    assert block.translation_fr == "fr:Hello there"


def test_argos_translation_keeps_source_when_cpu_retry_still_reports_cuda_oom(monkeypatch) -> None:
    translator = ArgosTranslator()

    monkeypatch.setattr(translator, "_translation_chain", lambda _source_lang, *, use_gpu: [_CudaFailTranslation()])
    monkeypatch.setattr(translator, "_clear_cuda_cache", lambda: None)
    block = OcrBlock(id="b1", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="Hello there")

    translator.translate_blocks([block], "en", use_gpu=True)

    assert block.translation_fr == "Hello there"
    assert "Argos CUDA OOM" in block.quality_warnings[-1]


def test_argos_translation_recovers_from_cuda_oom_even_when_gpu_flag_is_false(monkeypatch) -> None:
    translator = ArgosTranslator()
    calls: list[bool] = []

    def fake_chain(_source_lang: str, *, use_gpu: bool):  # type: ignore[no-untyped-def]
        calls.append(use_gpu)
        return [_CudaFailTranslation()] if len(calls) == 1 else [_CpuTranslation()]

    monkeypatch.setattr(translator, "_translation_chain", fake_chain)
    monkeypatch.setattr(translator, "_clear_cuda_cache", lambda: None)
    block = OcrBlock(id="b1", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="Hello there")

    translator.translate_blocks([block], "en", use_gpu=False)

    assert calls == [False, False]
    assert block.translation_fr == "fr:Hello there"


def test_argos_skips_unreliable_japanese_fragments(monkeypatch) -> None:
    translator = ArgosTranslator()

    def fail_chain(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Unreliable Japanese OCR fragments must not be sent to Argos")

    monkeypatch.setattr(translator, "_translation_chain", fail_chain)
    blocks = [
        OcrBlock(id="symbol", bbox=[0, 0, 1, 1], source_lang="ja", ocr_text="@", confidence=0.1),
        OcrBlock(id="short", bbox=[0, 0, 1, 1], source_lang="ja", ocr_text="青", confidence=0.2),
        OcrBlock(id="medium", bbox=[0, 0, 1, 1], source_lang="ja", ocr_text="我喜ちかに", confidence=0.58),
    ]

    translator.translate_blocks(blocks, "ja")

    assert [block.translation_fr for block in blocks] == ["", "", ""]
    assert all("fragment japonais" in block.quality_warnings[-1] for block in blocks)


def test_argos_translates_confident_japanese_text(monkeypatch) -> None:
    translator = ArgosTranslator()
    calls: list[str] = []

    class _Translation:
        def translate(self, text: str) -> str:
            calls.append(text)
            return "Une phrase lisible."

    monkeypatch.setattr(translator, "_translation_chain", lambda _source_lang, *, use_gpu: [_Translation()])
    block = OcrBlock(
        id="ja",
        bbox=[0, 0, 1, 1],
        source_lang="ja",
        ocr_text="今日は会社に行きます",
        confidence=0.95,
    )

    translator.translate_blocks([block], "ja")

    assert calls == ["今日は会社に行きます"]
    assert block.translation_fr == "Une phrase lisible."


def test_argos_keeps_japanese_numeric_amounts_translatable(monkeypatch) -> None:
    translator = ArgosTranslator()

    class _Translation:
        def translate(self, text: str) -> str:
            return "8,2 millions"

    monkeypatch.setattr(translator, "_translation_chain", lambda _source_lang, *, use_gpu: [_Translation()])
    block = OcrBlock(id="amount", bbox=[0, 0, 1, 1], source_lang="ja", ocr_text="820万", confidence=0.9)

    translator.translate_blocks([block], "ja")

    assert block.translation_fr == "8,2 millions"
