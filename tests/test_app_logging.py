from pathlib import Path

from cbz_manga_translator.core.app_logging import setup_app_logging


def test_setup_app_logging_creates_log_files(tmp_path: Path):
    app_log, fatal_log = setup_app_logging(tmp_path)
    assert app_log.parent == tmp_path
    assert fatal_log.parent == tmp_path
    assert app_log.name == "mangatrad.log"
    assert fatal_log.name == "mangatrad_fatal.log"
