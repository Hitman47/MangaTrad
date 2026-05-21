from cbz_manga_translator.ocr_setup import main


def test_ocr_setup_commands_prints(capsys):
    assert main(["--commands"]) == 0
    out = capsys.readouterr().out
    assert "Tesseract" in out
    assert "PaddleOCR" in out
    assert "python -m pip" in out
