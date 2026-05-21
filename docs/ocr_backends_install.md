# Installation des backends OCR locaux

MangaTrad utilise **EasyOCR** par défaut. Tesseract et PaddleOCR sont optionnels : ils servent uniquement au fallback OCR quand EasyOCR lit mal une bulle.

## Vérification rapide

Dans PowerShell, depuis le projet et avec le venv actif :

```powershell
cd C:\temp\MangaTrad_v0_2_0
.\.venv\Scripts\Activate.ps1
python -m cbz_manga_translator.ocr_setup --check
```

Pour afficher les commandes :

```powershell
python -m cbz_manga_translator.ocr_setup --commands
```

## Tesseract

Tesseract nécessite deux éléments :

1. le programme Windows `tesseract.exe` ;
2. le wrapper Python `pytesseract`.

Installation Windows recommandée :

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
python -m pip install pytesseract
```

Ouvre ensuite un nouveau PowerShell, active le venv, puis vérifie :

```powershell
.\.venv\Scripts\Activate.ps1
tesseract --version
tesseract --list-langs
python -c "import pytesseract; print(pytesseract.get_tesseract_version()); print(pytesseract.get_languages(config=''))"
```

Pour MangaTrad, `eng` suffit pour OCR anglais. Pour OCR japonais, il faut aussi `jpn` dans `tesseract --list-langs`.

## PaddleOCR

PaddleOCR est plus lourd que Tesseract. Installe-le seulement si tu veux tester le fallback alternatif :

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install paddleocr
python -c "import paddleocr; print('PaddleOCR OK', getattr(paddleocr, '__version__', 'unknown'))"
```

Puis vérifie côté MangaTrad :

```powershell
python -m cbz_manga_translator.ocr_setup --check
```

## Utilisation dans MangaTrad

1. Lance l'application :

```powershell
python -m cbz_manga_translator.main
```

2. Ouvre un CBZ.
3. Lance `OCR local page` ou `OCR + trad locale`.
4. Utilise ensuite `Relire OCR suspects`.
5. Utilise `Relire OCR tous` seulement sur une page problématique : c'est très lent et beaucoup plus lourd.

## Logs

À partir de la version 0.3.5, MangaTrad écrit des logs dans :

```text
<dossier du projet>\logs\mangatrad.log
<dossier du projet>\logs\mangatrad_fatal.log
```

Si une bibliothèque native OCR/ML fait crasher Python, `mangatrad_fatal.log` est le fichier à regarder en premier.
