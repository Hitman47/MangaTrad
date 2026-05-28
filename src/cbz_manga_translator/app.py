from __future__ import annotations

import logging
import tempfile
import time
import traceback
from pathlib import Path
from typing import Callable

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.cbz_reader import CbzReader
from cbz_manga_translator.core.block_view import (
    BlockFilter,
    block_display_source,
    page_block_stats,
    project_stats,
    visible_blocks,
)
from cbz_manga_translator.core.editing import (
    apply_ocr_alternative,
    merge_blocks,
    move_block_order,
    set_block_field,
    set_manual_status,
    split_block_by_lines,
    status_label,
)
from cbz_manga_translator.core.models import OcrBlock, ProjectData, SourceLang
from cbz_manga_translator.core.local_runtime import collect_local_runtime_checks, format_runtime_checks
from cbz_manga_translator.core.app_logging import setup_app_logging
from cbz_manga_translator.export.html_export import export_html_project
from cbz_manga_translator.analysis.export_review import export_review_dataset
from cbz_manga_translator.analysis.review_filter import apply_review_filters
from cbz_manga_translator.gui.theme import APP_STYLESHEET
from cbz_manga_translator.ocr.easyocr_engine import EasyOcrEngine
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.local_server_client import LocalTranslationServerClient
from cbz_manga_translator.translate.quality import TranslationQualityChecker


def run_gui() -> int:
    app_log_path, fatal_log_path = setup_app_logging()
    logger = logging.getLogger("cbz_manga_translator.gui")
    logger.info("Starting MangaTrad GUI")
    from PySide6 import QtCore, QtGui, QtWidgets

    class TaskThread(QtCore.QThread):
        result_ready = QtCore.Signal(object)
        failed = QtCore.Signal(str)

        def __init__(self, fn: Callable[[], object]) -> None:
            super().__init__()
            self._fn = fn

        def run(self) -> None:
            try:
                self.result_ready.emit(self._fn())
            except Exception as exc:  # pragma: no cover - GUI defensive path
                self.failed.emit(f"{type(exc).__name__}: {exc}\n\nTraceback:\n{traceback.format_exc()}")

    class ImageCanvas(QtWidgets.QLabel):
        def __init__(self) -> None:
            super().__init__()
            self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.setMinimumSize(360, 480)
            self._source_pixmap: QtGui.QPixmap | None = None
            self._blocks: list[OcrBlock] = []
            self._selected_id: str | None = None
            self._max_width = 1250

        def set_page(self, image_bytes: bytes, blocks: list[OcrBlock], selected_id: str | None = None) -> None:
            pixmap = QtGui.QPixmap()
            if not pixmap.loadFromData(image_bytes):
                raise ValueError("Unable to load page image")
            self._source_pixmap = pixmap
            self._blocks = list(blocks)
            self._selected_id = selected_id
            self._redraw()

        def set_selected_block(self, block_id: str | None) -> None:
            self._selected_id = block_id
            self._redraw()

        def _redraw(self) -> None:
            if self._source_pixmap is None:
                self.clear()
                return
            source = self._source_pixmap
            display_width = min(source.width(), self._max_width)
            scale = display_width / max(1, source.width())
            display = source.scaledToWidth(display_width, QtCore.Qt.TransformationMode.SmoothTransformation)
            painter = QtGui.QPainter(display)
            for block in self._blocks:
                selected = block.id == self._selected_id
                if block.manual_status == "validated":
                    color = QtGui.QColor(65, 190, 110)
                elif block.manual_status == "review" or block.quality_warnings:
                    color = QtGui.QColor(255, 170, 45)
                elif block.manual_status == "ignored":
                    color = QtGui.QColor(130, 130, 130)
                else:
                    color = QtGui.QColor(80, 180, 255)
                pen = QtGui.QPen(color, 4 if selected else 2)
                painter.setPen(pen)
                x1, y1, x2, y2 = block.bbox
                painter.drawRect(
                    int(x1 * scale),
                    int(y1 * scale),
                    max(1, int((x2 - x1) * scale)),
                    max(1, int((y2 - y1) * scale)),
                )
            painter.end()
            self.setPixmap(display)
            self.resize(display.size())

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("MangaTrad — OCR et traduction locale")
            self.resize(1760, 1040)
            self.setMinimumSize(1280, 820)

            self.reader: CbzReader | None = None
            self.project: ProjectData | None = None
            self.cache_path: Path | None = None
            self.current_index = 0
            self.ocr_engine = EasyOcrEngine()
            self.ocr_fallback_engine = OcrFallbackEngine(self.ocr_engine)
            self.translator = ArgosTranslator()
            self.quality_checker = TranslationQualityChecker()
            self.task: TaskThread | None = None
            self._loading_detail = False

            self._build_widgets()
            self._layout_widgets()
            self._connect_widgets()
            self._set_project_controls(False)
            self._set_detail_enabled(False)

        def _build_widgets(self) -> None:
            self.open_button = QtWidgets.QPushButton("Ouvrir CBZ")
            self.save_button = QtWidgets.QPushButton("Sauvegarder")
            self.export_button = QtWidgets.QPushButton("Exporter HTML")
            self.export_analysis_button = QtWidgets.QPushButton("Exporter analyse")
            self.export_analysis_button.setToolTip("Exporte CSV/JSONL + rapport qualité + suggestions glossaire pour comparer des dizaines de pages.")

            self.lang_combo = QtWidgets.QComboBox()
            self.lang_combo.addItem("EN → FR", "en")
            self.lang_combo.addItem("JP → FR", "ja")

            self.backend_combo = QtWidgets.QComboBox()
            self.backend_combo.addItem("Intégré dans l'app", "embedded")
            self.backend_combo.addItem("Serveur local HTTP", "server")
            self.backend_combo.setToolTip("Serveur local = moteur Argos gardé chargé dans un processus séparé. Nécessite des .argosmodel installés.")
            self.server_url_edit = QtWidgets.QLineEdit("http://127.0.0.1:8765")
            self.server_url_edit.setMinimumWidth(210)
            self.server_url_edit.setPlaceholderText("http://127.0.0.1:8765")
            self.server_url_edit.setToolTip("URL du serveur lancé avec python -m cbz_manga_translator.server")
            self.server_health_button = QtWidgets.QPushButton("Tester serveur")
            self.server_preload_button = QtWidgets.QPushButton("Vérifier modèles EN+JP")
            self.local_runtime_button = QtWidgets.QPushButton("Vérifier local")
            self.local_runtime_button.setToolTip("Vérifie les backends locaux installés sans contacter d’API externe.")
            self.local_runtime_label = QtWidgets.QLabel(f"Local: OCR EasyOCR + traduction Argos; aucun Hugging Face; logs: {app_log_path}")
            self.local_runtime_label.setObjectName("statusPill")
            self.local_runtime_label.setWordWrap(True)

            self.ocr_button = QtWidgets.QPushButton("OCR local page")
            self.reocr_suspects_button = QtWidgets.QPushButton("Relire OCR suspects")
            self.reocr_suspects_button.setToolTip("Relit les blocs suspects avec EasyOCR multi-crops + corrections locales + Tesseract/PaddleOCR si installés.")
            self.reocr_all_button = QtWidgets.QPushButton("Relire OCR tous")
            self.reocr_all_button.setToolTip("Relit tous les blocs de la page, même sans warning. Plus lent, utile quand EasyOCR semble globalement faible.")
            self.translate_button = QtWidgets.QPushButton("Traduction locale page")
            self.full_button = QtWidgets.QPushButton("OCR + trad locale")
            self.qc_button = QtWidgets.QPushButton("Quality check")

            self.validate_button = QtWidgets.QPushButton("Valider")
            self.review_button = QtWidgets.QPushButton("À revoir")
            self.ignore_button = QtWidgets.QPushButton("Ignorer")
            self.retranslate_button = QtWidgets.QPushButton("Retraduire")
            self.apply_detail_button = QtWidgets.QPushButton("Appliquer corrections")
            self.use_ocr_alternative_button = QtWidgets.QPushButton("Utiliser alternative OCR")
            self.merge_blocks_button = QtWidgets.QPushButton("Fusionner blocs")
            self.split_block_button = QtWidgets.QPushButton("Séparer bloc")
            self.order_up_button = QtWidgets.QPushButton("↑ Ordre")
            self.order_down_button = QtWidgets.QPushButton("↓ Ordre")
            self.save_glossary_button = QtWidgets.QPushButton("Sauver glossaire")

            cuda_available = EasyOcrEngine.cuda_available() and ArgosTranslator.cuda_available()
            self.gpu_checkbox = QtWidgets.QCheckBox("GPU CUDA")
            self.gpu_checkbox.setChecked(cuda_available)
            self.gpu_checkbox.setEnabled(cuda_available)
            self.gpu_checkbox.setToolTip(
                "Utilise CUDA si PyTorch détecte le GPU. Si grisé, installe PyTorch CUDA puis relance l'application."
            )
            self.merge_checkbox = QtWidgets.QCheckBox("Fusionner lignes")
            self.merge_checkbox.setChecked(True)
            self.noise_filter_checkbox = QtWidgets.QCheckBox("Filtrer bruit")
            self.noise_filter_checkbox.setChecked(True)
            self.refine_ocr_checkbox = QtWidgets.QCheckBox("OCR multi-variantes")
            self.refine_ocr_checkbox.setChecked(True)
            self.ocr_fallback_checkbox = QtWidgets.QCheckBox("Fallback OCR local")
            self.ocr_fallback_checkbox.setChecked(True)
            self.ocr_fallback_checkbox.setToolTip("Après EasyOCR, relit les blocs suspects avec stratégies locales et moteurs optionnels gratuits.")
            self.normalize_english_checkbox = QtWidgets.QCheckBox("Normaliser EN familier")
            self.normalize_english_checkbox.setChecked(True)
            self.builtin_glossary_checkbox = QtWidgets.QCheckBox("Dico manga intégré")
            self.builtin_glossary_checkbox.setChecked(True)
            self.min_conf_spin = QtWidgets.QDoubleSpinBox()
            self.min_conf_spin.setRange(0.0, 1.0)
            self.min_conf_spin.setSingleStep(0.05)
            self.min_conf_spin.setDecimals(2)
            self.min_conf_spin.setValue(0.20)
            self.min_conf_spin.setPrefix("Conf. min ")

            self.terms_edit = QtWidgets.QPlainTextEdit()
            self.terms_edit.setMinimumHeight(220)
            self.terms_edit.setPlaceholderText("Naru\nNARL=Naru\ncontrail=traînée de condensation")
            self.terms_edit.setToolTip(
                "Glossaire projet persistant. Syntaxe: NomPropre, source=traduction, source=>traduction. Une entrée par ligne conseillé."
            )

            self.status_label = QtWidgets.QLabel("Aucun CBZ chargé.")
            self.page_list = QtWidgets.QListWidget()
            self.page_list.setMinimumWidth(230)
            self.page_list.setUniformItemSizes(True)

            self.image_canvas = ImageCanvas()
            self.image_scroll = QtWidgets.QScrollArea()
            self.image_scroll.setWidget(self.image_canvas)
            self.image_scroll.setWidgetResizable(False)
            self.image_scroll.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.table = QtWidgets.QTableWidget(0, 6)
            self.table.setHorizontalHeaderLabels(["#", "Conf.", "QC", "Statut", "Source", "Traduction FR"])
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            self.table.setWordWrap(True)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.horizontalHeader().setStretchLastSection(True)
            for column in range(4):
                self.table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.table.setMinimumHeight(520)
            self.table.setMinimumWidth(720)
            self.table.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

            self.block_filter_combo = QtWidgets.QComboBox()
            self.block_filter_combo.addItem("Tous les blocs", "all")
            self.block_filter_combo.addItem("QC uniquement", "warnings")
            self.block_filter_combo.addItem("À revoir", "review")
            self.block_filter_combo.addItem("Sans traduction", "untranslated")
            self.block_filter_combo.addItem("Non validés", "unvalidated")
            self.block_filter_combo.addItem("Validés", "validated")
            self.block_filter_combo.addItem("Ignorés", "ignored")
            self.block_filter_combo.setToolTip("Filtre les blocs visibles sans modifier le cache.")
            self.block_search_edit = QtWidgets.QLineEdit()
            self.block_search_edit.setPlaceholderText("Rechercher dans OCR / traduction / QC…")
            self.block_search_edit.setClearButtonEnabled(True)
            self.block_search_edit.setToolTip("Recherche multi-mots dans OCR brut/corrigé, normalisé, traduction et warnings QC.")
            self.page_summary_label = QtWidgets.QLabel("Page: —")
            self.page_summary_label.setObjectName("summaryLabel")
            self.project_summary_label = QtWidgets.QLabel("Projet: —")
            self.project_summary_label.setObjectName("summaryLabel")

            self.detail_title = QtWidgets.QLabel("Aucun bloc sélectionné")
            self.detail_title.setObjectName("detailTitle")
            self.block_meta_label = QtWidgets.QLabel("—")
            self.ocr_raw_edit = self._make_text_edit(editable=True, min_height=92)
            self.ocr_corrected_edit = self._make_text_edit(editable=True, min_height=92)
            self.normalized_edit = self._make_text_edit(editable=True, min_height=92)
            self.raw_translation_edit = self._make_text_edit(editable=False, min_height=92)
            self.final_translation_edit = self._make_text_edit(editable=True, min_height=132)
            self.qc_warnings_edit = self._make_text_edit(editable=False, min_height=92)
            self.ocr_alternatives_combo = QtWidgets.QComboBox()
            self.ocr_alternatives_combo.setMinimumWidth(260)
            self.ocr_alternatives_combo.setToolTip("Choisis une alternative OCR, puis applique-la comme texte source du bloc.")
            self.ocr_alternatives_edit = self._make_text_edit(editable=False, min_height=92)

        def _make_text_edit(self, *, editable: bool, min_height: int) -> QtWidgets.QPlainTextEdit:
            widget = QtWidgets.QPlainTextEdit()
            widget.setMinimumHeight(min_height)
            widget.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
            widget.setReadOnly(not editable)
            widget.setTabChangesFocus(True)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
            return widget

        def _layout_widgets(self) -> None:
            project_box = QtWidgets.QGroupBox("Projet")
            project_layout = QtWidgets.QGridLayout(project_box)
            project_layout.addWidget(self.open_button, 0, 0)
            project_layout.addWidget(self.save_button, 0, 1)
            project_layout.addWidget(self.export_button, 0, 2)
            project_layout.addWidget(self.export_analysis_button, 0, 3)
            project_layout.addWidget(QtWidgets.QLabel("Langue"), 1, 0)
            project_layout.addWidget(self.lang_combo, 1, 1, 1, 2)

            backend_box = QtWidgets.QGroupBox("Local / serveur")
            backend_layout = QtWidgets.QGridLayout(backend_box)
            backend_layout.addWidget(QtWidgets.QLabel("Backend"), 0, 0)
            backend_layout.addWidget(self.backend_combo, 0, 1, 1, 2)
            backend_layout.addWidget(QtWidgets.QLabel("URL"), 1, 0)
            backend_layout.addWidget(self.server_url_edit, 1, 1, 1, 2)
            backend_layout.addWidget(self.server_health_button, 2, 0)
            backend_layout.addWidget(self.server_preload_button, 2, 1)
            backend_layout.addWidget(self.local_runtime_button, 2, 2)
            backend_layout.addWidget(self.local_runtime_label, 3, 0, 1, 3)

            actions_box = QtWidgets.QGroupBox("Actions page")
            actions_layout = QtWidgets.QGridLayout(actions_box)
            actions_layout.addWidget(self.ocr_button, 0, 0)
            actions_layout.addWidget(self.reocr_suspects_button, 0, 1)
            actions_layout.addWidget(self.reocr_all_button, 0, 2)
            actions_layout.addWidget(self.translate_button, 1, 0)
            actions_layout.addWidget(self.full_button, 1, 1)
            actions_layout.addWidget(self.qc_button, 1, 2)

            options_box = QtWidgets.QGroupBox("Options")
            options_layout = QtWidgets.QGridLayout(options_box)
            options_layout.addWidget(self.gpu_checkbox, 0, 0)
            options_layout.addWidget(self.merge_checkbox, 0, 1)
            options_layout.addWidget(self.noise_filter_checkbox, 0, 2)
            options_layout.addWidget(self.refine_ocr_checkbox, 1, 0)
            options_layout.addWidget(self.ocr_fallback_checkbox, 1, 1)
            options_layout.addWidget(self.normalize_english_checkbox, 1, 2)
            options_layout.addWidget(self.builtin_glossary_checkbox, 2, 0)
            options_layout.addWidget(self.min_conf_spin, 2, 1, 1, 2)

            top = QtWidgets.QWidget()
            top_layout = QtWidgets.QHBoxLayout(top)
            top_layout.setContentsMargins(0, 0, 0, 0)
            top_layout.setSpacing(10)
            top_layout.addWidget(project_box)
            top_layout.addWidget(backend_box, 1)
            top_layout.addWidget(actions_box)
            top_layout.addWidget(options_box)

            pages_box = QtWidgets.QGroupBox("Pages")
            pages_layout = QtWidgets.QVBoxLayout(pages_box)
            pages_layout.addWidget(self.page_list)

            right_panel = self._build_right_panel()

            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            splitter.addWidget(pages_box)
            splitter.addWidget(self.image_scroll)
            splitter.addWidget(right_panel)
            splitter.setSizes([230, 850, 760])
            splitter.setCollapsible(1, False)
            splitter.setCollapsible(2, False)

            root = QtWidgets.QWidget()
            root_layout = QtWidgets.QVBoxLayout(root)
            root_layout.setContentsMargins(8, 8, 8, 8)
            root_layout.setSpacing(8)
            root_layout.addWidget(top)
            root_layout.addWidget(splitter, 1)
            root_layout.addWidget(self.status_label)
            self.setCentralWidget(root)

        def _build_right_panel(self) -> QtWidgets.QWidget:
            right_panel = QtWidgets.QWidget()
            right_layout = QtWidgets.QVBoxLayout(right_panel)
            right_layout.setContentsMargins(8, 0, 0, 0)
            right_layout.setSpacing(8)

            self.right_tabs = QtWidgets.QTabWidget()
            self.right_tabs.setDocumentMode(True)
            self.right_tabs.addTab(self._build_blocks_tab(), "Blocs")
            self.right_tabs.addTab(self._build_detail_tab(), "Détail / correction")
            self.right_tabs.addTab(self._build_glossary_tab(), "Glossaire")
            self.right_tabs.addTab(self._build_local_tab(), "Local")
            right_layout.addWidget(self.right_tabs, 1)
            return right_panel

        def _build_blocks_tab(self) -> QtWidgets.QWidget:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)

            title = QtWidgets.QLabel("Blocs détectés")
            title.setObjectName("sectionTitle")
            hint = QtWidgets.QLabel("Sélectionne une ligne, puis ouvre l’onglet Détail / correction pour travailler proprement le bloc.")
            hint.setObjectName("mutedText")
            hint.setWordWrap(True)

            filter_row = QtWidgets.QHBoxLayout()
            filter_row.addWidget(QtWidgets.QLabel("Filtre"))
            filter_row.addWidget(self.block_filter_combo)
            filter_row.addWidget(self.block_search_edit, 1)

            layout.addWidget(title)
            layout.addWidget(hint)
            layout.addLayout(filter_row)
            layout.addWidget(self.page_summary_label)
            layout.addWidget(self.table, 1)
            layout.addWidget(self.project_summary_label)
            return tab

        def _build_detail_tab(self) -> QtWidgets.QWidget:
            tab = QtWidgets.QWidget()
            outer_layout = QtWidgets.QVBoxLayout(tab)
            outer_layout.setContentsMargins(0, 0, 0, 0)

            detail_container = QtWidgets.QWidget()
            detail_layout = QtWidgets.QVBoxLayout(detail_container)
            detail_layout.setContentsMargins(14, 14, 14, 14)
            detail_layout.setSpacing(12)

            detail_layout.addWidget(self.detail_title)
            self.block_meta_label.setWordWrap(True)
            self.block_meta_label.setObjectName("mutedText")
            detail_layout.addWidget(self.block_meta_label)

            action_grid = QtWidgets.QGridLayout()
            action_grid.setHorizontalSpacing(8)
            action_grid.setVerticalSpacing(8)
            action_buttons = [
                self.apply_detail_button,
                self.retranslate_button,
                self.use_ocr_alternative_button,
                self.merge_blocks_button,
                self.split_block_button,
                self.order_up_button,
                self.order_down_button,
                self.validate_button,
                self.review_button,
                self.ignore_button,
            ]
            for index, widget in enumerate(action_buttons):
                widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
                action_grid.addWidget(widget, index // 3, index % 3)
            detail_layout.addLayout(action_grid)

            alternative_row = QtWidgets.QHBoxLayout()
            alternative_row.addWidget(QtWidgets.QLabel("Choix OCR"))
            alternative_row.addWidget(self.ocr_alternatives_combo, 1)

            detail_layout.addWidget(self._field_section("OCR brut", self.ocr_raw_edit))
            detail_layout.addWidget(self._field_section("OCR corrigé", self.ocr_corrected_edit))
            detail_layout.addLayout(alternative_row)
            detail_layout.addWidget(self._field_section("Alternatives OCR", self.ocr_alternatives_edit))
            detail_layout.addWidget(self._field_section("Texte normalisé", self.normalized_edit))
            detail_layout.addWidget(self._field_section("Traduction brute", self.raw_translation_edit))
            detail_layout.addWidget(self._field_section("Traduction finale", self.final_translation_edit))
            detail_layout.addWidget(self._field_section("Quality check", self.qc_warnings_edit))
            detail_layout.addStretch(1)

            detail_scroll = QtWidgets.QScrollArea()
            detail_scroll.setObjectName("detailScroll")
            detail_scroll.setWidget(detail_container)
            detail_scroll.setWidgetResizable(True)
            detail_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            detail_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            detail_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            outer_layout.addWidget(detail_scroll, 1)
            return tab

        def _build_glossary_tab(self) -> QtWidgets.QWidget:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setSpacing(10)
            title = QtWidgets.QLabel("Glossaire projet")
            title.setObjectName("sectionTitle")
            help_text = QtWidgets.QLabel(
                "Une entrée par ligne. Exemples : Naru, NARL=Naru, contrail=traînée de condensation. "
                "Le glossaire reste local et sert à protéger/corriger les noms et termes récurrents."
            )
            help_text.setObjectName("mutedText")
            help_text.setWordWrap(True)
            layout.addWidget(title)
            layout.addWidget(help_text)
            layout.addWidget(self.terms_edit, 1)
            layout.addWidget(self.save_glossary_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)
            return tab

        def _build_local_tab(self) -> QtWidgets.QWidget:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setSpacing(10)
            title = QtWidgets.QLabel("Exécution locale")
            title.setObjectName("sectionTitle")
            help_text = QtWidgets.QLabel(
                "OCR : EasyOCR local. Traduction : Argos Translate local avec modèles .argosmodel. "
                "Aucun Hugging Face n’est utilisé par le backend 0.3.x. Le serveur HTTP est optionnel et doit être lancé séparément."
            )
            help_text.setObjectName("mutedText")
            help_text.setWordWrap(True)
            instructions = QtWidgets.QPlainTextEdit()
            instructions.setReadOnly(True)
            instructions.setPlainText(
                "Boutons utiles dans la barre du haut :\n"
                "- Vérifier local : contrôle EasyOCR, Argos, modèles installés et CUDA.\n"
                "- Tester serveur : uniquement si Backend = Serveur local HTTP.\n"
                "- Vérifier modèles EN+JP : uniquement si le serveur local est déjà lancé.\n\n"
                "Mode recommandé pour travailler : Backend = Intégré dans l'app.\n"
                "Le serveur HTTP est optionnel et sert seulement à garder le moteur de traduction chargé."
            )
            instructions.setMinimumHeight(240)
            layout.addWidget(title)
            layout.addWidget(help_text)
            layout.addWidget(instructions)
            layout.addStretch(1)
            return tab

        def _field_section(self, label: str, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
            section = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(section)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)
            label_widget = QtWidgets.QLabel(label)
            label_widget.setObjectName("fieldLabel")
            layout.addWidget(label_widget)
            layout.addWidget(widget)
            return section

        def _field_row(self, label: str, widget: QtWidgets.QWidget) -> QtWidgets.QHBoxLayout:
            layout = QtWidgets.QHBoxLayout()
            label_widget = QtWidgets.QLabel(label)
            label_widget.setMinimumWidth(110)
            label_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight)
            layout.addWidget(label_widget)
            layout.addWidget(widget, 1)
            return layout

        def _connect_widgets(self) -> None:
            self.open_button.clicked.connect(self.open_cbz)
            self.ocr_button.clicked.connect(self.ocr_current_page)
            self.reocr_suspects_button.clicked.connect(self.re_ocr_suspect_blocks)
            self.reocr_all_button.clicked.connect(self.re_ocr_all_blocks)
            self.translate_button.clicked.connect(self.translate_current_page)
            self.full_button.clicked.connect(self.ocr_and_translate_current_page)
            self.qc_button.clicked.connect(self.quality_check_current_page)
            self.validate_button.clicked.connect(self.validate_selected_blocks)
            self.review_button.clicked.connect(self.review_selected_blocks)
            self.ignore_button.clicked.connect(self.ignore_selected_blocks)
            self.retranslate_button.clicked.connect(self.retranslate_selected_blocks)
            self.apply_detail_button.clicked.connect(self.apply_detail_changes)
            self.use_ocr_alternative_button.clicked.connect(self.use_selected_ocr_alternative)
            self.merge_blocks_button.clicked.connect(self.merge_selected_blocks)
            self.split_block_button.clicked.connect(self.split_selected_block)
            self.order_up_button.clicked.connect(lambda: self.move_selected_block_order(-1))
            self.order_down_button.clicked.connect(lambda: self.move_selected_block_order(1))
            self.save_glossary_button.clicked.connect(self.save_project_glossary)
            self.server_health_button.clicked.connect(self.test_local_server)
            self.server_preload_button.clicked.connect(self.preload_local_server)
            self.local_runtime_button.clicked.connect(self.show_local_runtime_report)
            self.backend_combo.currentIndexChanged.connect(self._refresh_backend_controls)
            self.save_button.clicked.connect(self.save_project)
            self.export_button.clicked.connect(self.export_html)
            self.export_analysis_button.clicked.connect(self.export_analysis_dataset)
            self.page_list.currentRowChanged.connect(self.change_page)
            self.table.itemSelectionChanged.connect(self.table_selection_changed)
            self.block_filter_combo.currentIndexChanged.connect(lambda _index: self.refresh_current_page())
            self.block_search_edit.textChanged.connect(lambda _text: self.refresh_current_page())
            self._refresh_backend_controls()

        def _set_project_controls(self, enabled: bool) -> None:
            self.block_filter_combo.setEnabled(enabled)
            self.block_search_edit.setEnabled(enabled)
            for button in [
                self.ocr_button,
                self.reocr_suspects_button,
                self.reocr_all_button,
                self.translate_button,
                self.full_button,
                self.qc_button,
                self.validate_button,
                self.review_button,
                self.ignore_button,
                self.retranslate_button,
                self.apply_detail_button,
                self.use_ocr_alternative_button,
                self.merge_blocks_button,
                self.split_block_button,
                self.order_up_button,
                self.order_down_button,
                self.save_button,
                self.export_button,
                self.export_analysis_button,
                self.save_glossary_button,
            ]:
                button.setEnabled(enabled)

        def _set_detail_enabled(self, enabled: bool) -> None:
            for widget in [
                self.ocr_raw_edit,
                self.ocr_corrected_edit,
                self.ocr_alternatives_combo,
                self.ocr_alternatives_edit,
                self.normalized_edit,
                self.raw_translation_edit,
                self.final_translation_edit,
                self.qc_warnings_edit,
                self.apply_detail_button,
                self.use_ocr_alternative_button,
                self.retranslate_button,
                self.merge_blocks_button,
                self.split_block_button,
                self.order_up_button,
                self.order_down_button,
                self.validate_button,
                self.review_button,
                self.ignore_button,
            ]:
                widget.setEnabled(enabled)

        def _set_busy(self, busy: bool, text: str | None = None) -> None:
            self.open_button.setEnabled(not busy)
            self._set_project_controls((not busy) and self.project is not None)
            self.server_health_button.setEnabled(not busy)
            self.server_preload_button.setEnabled(not busy)
            self.local_runtime_button.setEnabled(not busy)
            if text:
                self.status_label.setText(text)

        def _refresh_backend_controls(self) -> None:
            use_server = self.translation_backend() == "server"
            self.server_url_edit.setEnabled(use_server)
            self.server_health_button.setEnabled(use_server)
            self.server_preload_button.setEnabled(use_server)

        def _current_block_filter(self) -> BlockFilter:
            return str(self.block_filter_combo.currentData() or "all")  # type: ignore[return-value]

        def _refresh_summary_labels(self) -> None:
            if self.project is None:
                self.page_summary_label.setText("Page: —")
                self.project_summary_label.setText("Projet: —")
                return
            page = self.project.pages[self.current_index]
            filtered_count = len(visible_blocks(page.blocks, self._current_block_filter(), self.block_search_edit.text()))
            page_stats = page_block_stats(page)
            project_status = project_stats(self.project)
            self.page_summary_label.setText(
                f"Page {self.current_index + 1:03d}: {page_stats.as_status_text()} · visibles {filtered_count}"
            )
            self.project_summary_label.setText(f"Projet: {project_status.as_status_text()}")

        def selected_lang(self) -> SourceLang:
            return self.lang_combo.currentData()

        def translation_backend(self) -> str:
            return str(self.backend_combo.currentData())

        def use_gpu(self) -> bool:
            return bool(self.gpu_checkbox.isChecked())

        def min_confidence(self) -> float:
            return float(self.min_conf_spin.value())

        def merge_lines(self) -> bool:
            return bool(self.merge_checkbox.isChecked())

        def filter_noise(self) -> bool:
            return bool(self.noise_filter_checkbox.isChecked())

        def refine_ocr(self) -> bool:
            return bool(self.refine_ocr_checkbox.isChecked())

        def fallback_ocr(self) -> bool:
            return bool(self.ocr_fallback_checkbox.isChecked())

        def normalize_english(self) -> bool:
            return bool(self.normalize_english_checkbox.isChecked())

        def translation_terms(self) -> str:
            return self.terms_edit.toPlainText().strip()

        def use_builtin_glossary(self) -> bool:
            return bool(self.builtin_glossary_checkbox.isChecked())

        def _server_client(self) -> LocalTranslationServerClient:
            return LocalTranslationServerClient(self.server_url_edit.text().strip())

        def _translate_blocks_backend(self, blocks: list[OcrBlock], lang: SourceLang, *, force: bool = False) -> list[OcrBlock]:
            if self.translation_backend() == "server":
                return self._server_client().translate_blocks(
                    blocks,
                    lang,
                    use_gpu=self.use_gpu(),
                    raw_terms=self.translation_terms(),
                    normalize_english=self.normalize_english(),
                    use_builtin_glossary=self.use_builtin_glossary(),
                    force=force,
                )
            return self.translator.translate_blocks(
                blocks,
                lang,
                use_gpu=self.use_gpu(),
                raw_terms=self.translation_terms(),
                normalize_english=self.normalize_english(),
                use_builtin_glossary=self.use_builtin_glossary(),
                force=force,
            )

        def open_cbz(self) -> None:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Ouvrir un CBZ", "", "CBZ files (*.cbz *.zip)")
            if not file_path:
                return
            try:
                self.reader = CbzReader(file_path)
                image_names = self.reader.image_names()
                if not image_names:
                    raise ValueError("No supported image found in this CBZ")
                self.project = ProjectCache.load_or_create(file_path, image_names)
                self.cache_path = ProjectCache.default_path(file_path)
                self.terms_edit.blockSignals(True)
                self.terms_edit.setPlainText(self.project.glossary_terms)
                self.terms_edit.blockSignals(False)
                self.page_list.clear()
                for page in self.project.pages:
                    self.page_list.addItem(self._page_label(page.page_index))
                self._set_project_controls(True)
                self.page_list.setCurrentRow(0)
                self.status_label.setText(f"CBZ chargé: {file_path} — cache: {self.cache_path}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erreur", str(exc))

        def _page_label(self, index: int) -> str:
            if self.project is None:
                return str(index + 1)
            page = self.project.pages[index]
            active = [block for block in page.blocks if block.manual_status != "ignored"]
            if active and all(block.manual_status == "validated" for block in active):
                marker = "✓"
            elif any(block.manual_status == "review" or block.quality_warnings for block in page.blocks):
                marker = "⚠"
            elif active and all(block.translation_fr for block in active):
                marker = "·"
            else:
                marker = " "
            return f"{marker} {index + 1:03d}  {Path(page.image_name).name}"

        def refresh_current_page(self, preferred_block_id: str | None = None) -> None:
            if self.reader is None or self.project is None:
                return
            selected_id = preferred_block_id or self._selected_block_id()
            page = self.project.pages[self.current_index]
            self.image_canvas.set_page(self.reader.read_image_bytes(page.image_name), page.blocks, selected_id=selected_id)
            self._refresh_summary_labels()
            self._fill_table(page.blocks, preferred_block_id=selected_id)
            item = self.page_list.item(self.current_index)
            if item is not None:
                item.setText(self._page_label(self.current_index))
            if selected_id and selected_id in self._current_blocks_by_id():
                self._fill_detail(self._current_blocks_by_id()[selected_id])
            else:
                self._clear_detail()

        def change_page(self, row: int) -> None:
            if row < 0 or self.project is None:
                return
            self.current_index = row
            self.refresh_current_page(preferred_block_id=None)

        @staticmethod
        def _preview(value: str, limit: int = 120) -> str:
            compact = " ".join(value.strip().split())
            if len(compact) <= limit:
                return compact
            return compact[: limit - 1].rstrip() + "…"

        def _fill_table(self, blocks: list[OcrBlock], *, preferred_block_id: str | None = None) -> None:
            self.table.blockSignals(True)
            self.table.setRowCount(0)
            warning_background = QtGui.QColor(96, 54, 22)
            selected_row = -1
            filtered_blocks = visible_blocks(blocks, self._current_block_filter(), self.block_search_edit.text())
            for row, block in enumerate(filtered_blocks):
                self.table.insertRow(row)
                warnings = list(block.quality_warnings)
                warning_text = " ; ".join(warnings)
                source_preview = block_display_source(block)
                values = [
                    str(block.reading_order),
                    "" if block.confidence is None else f"{block.confidence:.2f}",
                    "⚠" if warnings else "",
                    status_label(block.manual_status),
                    self._preview(source_preview),
                    self._preview(block.translation_fr),
                ]
                for col, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, block.id)
                    item.setToolTip(self._block_tooltip(block))
                    if block.manual_status == "validated":
                        item.setBackground(QtGui.QColor(28, 70, 40))
                    elif block.manual_status == "ignored":
                        item.setBackground(QtGui.QColor(52, 52, 52))
                    elif block.manual_status == "review":
                        item.setBackground(QtGui.QColor(90, 65, 30))
                    elif warnings:
                        item.setBackground(warning_background)
                    if warnings and col == 2:
                        item.setToolTip(warning_text)
                    self.table.setItem(row, col, item)
                self.table.setRowHeight(row, 50)
                if block.id == preferred_block_id:
                    selected_row = row
            self.table.blockSignals(False)
            if selected_row >= 0:
                self.table.selectRow(selected_row)
            elif self.table.rowCount() > 0:
                self.table.selectRow(0)
            else:
                self._clear_detail()

        @staticmethod
        def _block_tooltip(block: OcrBlock) -> str:
            warnings = "\n".join(f"- {item}" for item in block.quality_warnings) or "Aucun warning QC"
            return (
                f"OCR brut: {block.ocr_text}\n"
                f"OCR corrigé: {block.ocr_corrected_text}\n"
                f"Normalisé: {block.normalized_source_text}\n"
                f"Trad brute: {block.raw_translation_fr}\n"
                f"Trad finale: {block.translation_fr}\n\n"
                f"QC:\n{warnings}\n\n"
                f"Alternatives OCR:\n{MainWindow._format_ocr_alternatives(block)}"
            )


        @staticmethod
        def _format_ocr_alternatives(block: OcrBlock) -> str:
            if not block.ocr_alternatives:
                return "Aucune alternative OCR enregistrée."
            lines: list[str] = []
            for index, item in enumerate(block.ocr_alternatives, start=1):
                engine = item.get("engine", "unknown")
                text = item.get("text", "")
                score = item.get("score", 0.0)
                confidence = item.get("confidence")
                note = item.get("note", "")
                confidence_text = "—" if confidence is None else f"{float(confidence):.2f}"
                lines.append(f"{index}. [{engine}] score={float(score):.2f} conf={confidence_text} {note}\n   {text}")
            return "\n".join(lines)

        def _fill_ocr_alternatives_combo(self, block: OcrBlock) -> None:
            self.ocr_alternatives_combo.blockSignals(True)
            try:
                self.ocr_alternatives_combo.clear()
                for index, item in enumerate(block.ocr_alternatives):
                    text = str(item.get("text", "")).strip()
                    if not text:
                        continue
                    engine = item.get("engine", "unknown")
                    score = float(item.get("score", 0.0))
                    preview = self._preview(text, limit=70)
                    self.ocr_alternatives_combo.addItem(f"{index + 1}. {engine} · score {score:.2f} · {preview}", index)
            finally:
                self.ocr_alternatives_combo.blockSignals(False)

        def _current_blocks_by_id(self) -> dict[str, OcrBlock]:
            assert self.project is not None
            return {block.id: block for block in self.project.pages[self.current_index].blocks}

        def _selected_block_id(self) -> str | None:
            if self.table.currentItem() is not None:
                block_id = self.table.currentItem().data(QtCore.Qt.ItemDataRole.UserRole)
                return str(block_id) if block_id else None
            return None

        def _current_detail_block(self) -> OcrBlock | None:
            if self.project is None:
                return None
            block_id = self._selected_block_id()
            if not block_id:
                return None
            return self._current_blocks_by_id().get(block_id)

        def _selected_blocks(self) -> list[OcrBlock]:
            if self.project is None:
                return []
            block_by_id = self._current_blocks_by_id()
            ids: list[str] = []
            for index in self.table.selectionModel().selectedRows():
                item = self.table.item(index.row(), 0)
                if item is None:
                    continue
                block_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if block_id and block_id not in ids:
                    ids.append(block_id)
            if not ids:
                block_id = self._selected_block_id()
                if block_id:
                    ids.append(block_id)
            return [block_by_id[block_id] for block_id in ids if block_id in block_by_id]

        def _fill_detail(self, block: OcrBlock) -> None:
            self._loading_detail = True
            try:
                self._set_detail_enabled(True)
                self.detail_title.setText(f"Bloc #{block.reading_order} — {status_label(block.manual_status)}")
                confidence = "—" if block.confidence is None else f"{block.confidence:.2f}"
                self.block_meta_label.setText(f"id={block.id} | bbox={block.bbox} | confiance={confidence}")
                self.ocr_raw_edit.setPlainText(block.ocr_text)
                self.ocr_corrected_edit.setPlainText(block.ocr_corrected_text)
                self._fill_ocr_alternatives_combo(block)
                self.ocr_alternatives_edit.setPlainText(self._format_ocr_alternatives(block))
                self.normalized_edit.setPlainText(block.normalized_source_text)
                self.raw_translation_edit.setPlainText(block.raw_translation_fr)
                self.final_translation_edit.setPlainText(block.translation_fr)
                self.qc_warnings_edit.setPlainText("\n".join(block.quality_warnings))
            finally:
                self._loading_detail = False

        def _clear_detail(self) -> None:
            self._loading_detail = True
            try:
                self.detail_title.setText("Aucun bloc sélectionné")
                self.block_meta_label.setText("—")
                self.ocr_alternatives_combo.clear()
                for widget in [
                    self.ocr_raw_edit,
                    self.ocr_corrected_edit,
                    self.ocr_alternatives_edit,
                    self.normalized_edit,
                    self.raw_translation_edit,
                    self.final_translation_edit,
                    self.qc_warnings_edit,
                ]:
                    widget.clear()
                self._set_detail_enabled(False)
            finally:
                self._loading_detail = False

        def table_selection_changed(self) -> None:
            block = self._current_detail_block()
            if block is None:
                self.image_canvas.set_selected_block(None)
                self._clear_detail()
                return
            self.image_canvas.set_selected_block(block.id)
            self._fill_detail(block)

        def apply_detail_changes(self) -> None:
            if self._loading_detail:
                return
            block = self._current_detail_block()
            if block is None:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne un bloc à corriger.")
                return
            updates = [
                ("ocr_text", self.ocr_raw_edit.toPlainText(), block.ocr_text),
                ("ocr_corrected_text", self.ocr_corrected_edit.toPlainText(), block.ocr_corrected_text),
                ("normalized_source_text", self.normalized_edit.toPlainText(), block.normalized_source_text),
                ("translation_fr", self.final_translation_edit.toPlainText(), block.translation_fr),
            ]
            changed = 0
            for field, value, current in updates:
                if value.strip() != current.strip():
                    set_block_field(block, field, value)  # type: ignore[arg-type]
                    changed += 1
            if not changed:
                self.status_label.setText("Aucune modification à appliquer.")
                return
            self._autosave("correction sauvegardée automatiquement")
            self.refresh_current_page(preferred_block_id=block.id)

        def use_selected_ocr_alternative(self) -> None:
            block = self._current_detail_block()
            if block is None:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne un bloc avec des alternatives OCR.")
                return
            index_data = self.ocr_alternatives_combo.currentData()
            if index_data is None:
                QtWidgets.QMessageBox.information(self, "Info", "Aucune alternative OCR sélectionnable pour ce bloc.")
                return
            try:
                selected_text = apply_ocr_alternative(block, int(index_data))
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Alternative OCR", str(exc))
                return
            self._autosave(f"Alternative OCR appliquée: {self._preview(selected_text, 80)}")
            self.refresh_current_page(preferred_block_id=block.id)

        def merge_selected_blocks(self) -> None:
            if self.project is None:
                return
            blocks = self._selected_blocks()
            if len(blocks) < 2:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne au moins deux blocs à fusionner.")
                return
            page = self.project.pages[self.current_index]
            try:
                merged = merge_blocks(page.blocks, [block.id for block in blocks])
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Fusion", str(exc))
                return
            self._autosave(f"{len(blocks)} blocs fusionnés")
            self.refresh_current_page(preferred_block_id=merged.id)

        def split_selected_block(self) -> None:
            if self.project is None:
                return
            block = self._current_detail_block()
            if block is None:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne un bloc à séparer.")
                return
            source_lines = self.ocr_corrected_edit.toPlainText().strip() or self.ocr_raw_edit.toPlainText().strip()
            if "\n" not in source_lines.replace("\r\n", "\n"):
                QtWidgets.QMessageBox.information(
                    self,
                    "Séparer bloc",
                    "Ajoute d'abord des retours ligne dans OCR corrigé ou OCR brut pour indiquer les morceaux à créer.",
                )
                return
            page = self.project.pages[self.current_index]
            try:
                created = split_block_by_lines(page.blocks, block.id, source_lines)
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Séparer bloc", str(exc))
                return
            self._autosave(f"Bloc séparé en {len(created)} blocs")
            self.refresh_current_page(preferred_block_id=created[0].id)

        def move_selected_block_order(self, direction: int) -> None:
            if self.project is None:
                return
            block = self._current_detail_block()
            if block is None:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne un bloc à déplacer dans l'ordre de lecture.")
                return
            page = self.project.pages[self.current_index]
            try:
                moved = move_block_order(page.blocks, block.id, direction)
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Ordre de lecture", str(exc))
                return
            self._autosave("Ordre de lecture mis à jour")
            self.refresh_current_page(preferred_block_id=moved.id)

        def _autosave(self, message: str | None = None) -> None:
            if self.project is None or self.cache_path is None:
                return
            self.project.glossary_terms = self.translation_terms()
            ProjectCache.save(self.cache_path, self.project)
            if message:
                self.status_label.setText(f"{message}: {self.cache_path}")

        def save_project_glossary(self) -> None:
            if self.project is None:
                return
            self._autosave("Glossaire projet sauvegardé")

        def _set_selected_status(self, status: str, label: str) -> None:
            blocks = self._selected_blocks()
            if not blocks:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne au moins un bloc.")
                return
            count = set_manual_status(blocks, status)
            preferred = blocks[0].id if blocks else None
            self._autosave(f"{count} bloc(s) {label}")
            self.refresh_current_page(preferred_block_id=preferred)

        def validate_selected_blocks(self) -> None:
            self._set_selected_status("validated", "validé(s)")

        def review_selected_blocks(self) -> None:
            self._set_selected_status("review", "marqué(s) à revoir")

        def ignore_selected_blocks(self) -> None:
            self._set_selected_status("ignored", "ignoré(s)")

        def retranslate_selected_blocks(self) -> None:
            if self.project is None:
                return
            blocks = self._selected_blocks()
            if not blocks:
                QtWidgets.QMessageBox.information(self, "Info", "Sélectionne au moins un bloc à retraduire.")
                return
            lang = self.selected_lang()
            preferred = blocks[0].id

            def work() -> list[OcrBlock]:
                return self._translate_blocks_backend(blocks, lang, force=True)

            def done(result: object) -> None:
                translated = list(result)  # type: ignore[arg-type]
                flagged = self.quality_checker.apply(translated, source_lang=lang)
                for block in translated:
                    if block.manual_status == "validated":
                        block.manual_status = "edited"
                self._autosave(f"Retraduction sélection terminée — QC: {flagged} bloc(s) à vérifier")
                self.refresh_current_page(preferred_block_id=preferred)

            self._run_task(self._translation_task_label("Retraduction sélection"), work, done)

        def _run_task(self, label: str, fn: Callable[[], object], on_success: Callable[[object], None]) -> None:
            started_at = time.monotonic()
            logger.info("Task started: %s", label)
            self._set_busy(True, label)
            self.task = TaskThread(fn)
            self.task.result_ready.connect(lambda result: self._task_done(label, started_at, result, on_success))
            self.task.failed.connect(lambda message: self._task_failed(label, started_at, message))
            self.task.start()

        def _task_done(
            self,
            label: str,
            started_at: float,
            result: object,
            on_success: Callable[[object], None],
        ) -> None:
            logger.info("Task finished: %s in %.2fs", label, time.monotonic() - started_at)
            on_success(result)
            self.task = None
            self._set_busy(False)

        def _task_failed(self, label: str, started_at: float, message: str) -> None:
            logger.error("Task failed: %s in %.2fs\n%s", label, time.monotonic() - started_at, message)
            self.task = None
            self._set_busy(False, "Erreur — voir logs.")
            QtWidgets.QMessageBox.critical(
                self,
                "Erreur",
                f"{message}\n\nLogs écrits ici:\n{app_log_path}\n{fatal_log_path}",
            )

        def _translation_task_label(self, prefix: str) -> str:
            device = "GPU CUDA" if self.use_gpu() else "CPU"
            backend = "serveur local" if self.translation_backend() == "server" else "intégré"
            return f"{prefix} — Argos {backend} sur {device}…"


        def show_local_runtime_report(self) -> None:
            checks = collect_local_runtime_checks(
                translation_backend=self.translation_backend(),
                server_url=self.server_url_edit.text().strip(),
                gpu_requested=self.use_gpu(),
            )
            report = format_runtime_checks(checks)
            failures = [check for check in checks if not check.ok and check.name not in {"GPU CUDA"}]
            if failures:
                self.local_runtime_label.setObjectName("warningPill")
                self.local_runtime_label.setText(f"Local: {len(failures)} alerte(s) — détails affichés")
            else:
                self.local_runtime_label.setObjectName("statusPill")
                self.local_runtime_label.setText("Local: OCR/traduction disponibles — sans Hugging Face")
            self.local_runtime_label.style().unpolish(self.local_runtime_label)
            self.local_runtime_label.style().polish(self.local_runtime_label)
            QtWidgets.QMessageBox.information(self, "Vérification locale", report)

        def test_local_server(self) -> None:
            def work() -> dict[str, object]:
                return self._server_client().health()

            def done(result: object) -> None:
                payload = result if isinstance(result, dict) else {}
                self.status_label.setText(f"Serveur local OK: {payload}")

            self._run_task("Test du serveur local…", work, done)

        def preload_local_server(self) -> None:
            def work() -> dict[str, object]:
                return self._server_client().preload(["en", "ja"], use_gpu=self.use_gpu())

            def done(result: object) -> None:
                self.status_label.setText(f"Modèles Argos vérifiés sur le serveur local: {result}")

            self._run_task("Vérification EN+JP sur le serveur Argos local…", work, done)

        def ocr_current_page(self) -> None:
            if self.reader is None or self.project is None:
                return
            page = self.project.pages[self.current_index]
            lang = self.selected_lang()
            image_bytes = self.reader.read_image_bytes(page.image_name)
            suffix = Path(page.image_name).suffix or ".jpg"

            def work() -> list[OcrBlock]:
                with tempfile.TemporaryDirectory(prefix="cbz_manga_ocr_") as temp_dir:
                    image_path = Path(temp_dir) / f"page{suffix}"
                    image_path.write_bytes(image_bytes)
                    blocks = self.ocr_engine.recognize(
                        image_path,
                        lang,
                        page.page_index,
                        use_gpu=self.use_gpu(),
                        min_confidence=self.min_confidence(),
                        merge_lines=self.merge_lines(),
                        filter_noise=self.filter_noise(),
                        refine_crops=self.refine_ocr(),
                    )
                    if self.fallback_ocr():
                        blocks, _changed = self.ocr_fallback_engine.improve_blocks(
                            image_path,
                            blocks,
                            lang,
                            use_gpu=self.use_gpu(),
                            min_confidence=self.min_confidence(),
                            only_suspect=True,
                        )
                    return blocks

            def done(blocks: object) -> None:
                page.blocks = list(blocks)  # type: ignore[arg-type]
                page.status = "ocr_done"
                self._autosave(f"OCR terminé: {len(page.blocks)} bloc(s)")
                self.refresh_current_page()

            device = "GPU CUDA" if self.use_gpu() else "CPU"
            self._run_task(f"OCR en cours sur {device}…", work, done)

        def _re_ocr_blocks(self, *, only_suspect: bool) -> None:
            if self.reader is None or self.project is None:
                return
            page = self.project.pages[self.current_index]
            if not page.blocks:
                QtWidgets.QMessageBox.information(self, "Info", "Aucun bloc OCR à relire sur cette page.")
                return
            if not only_suspect:
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "Relire tous les blocs OCR",
                    "Cette action relit tous les blocs avec plusieurs variantes OCR et peut prendre plusieurs minutes.\n"
                    "Elle peut aussi consommer beaucoup de RAM/GPU avec PaddleOCR/Tesseract.\n\n"
                    f"Nombre de blocs sur cette page: {len(page.blocks)}\n\n"
                    "Continuer ?",
                )
                if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
            lang = self.selected_lang()
            image_bytes = self.reader.read_image_bytes(page.image_name)
            suffix = Path(page.image_name).suffix or ".jpg"

            def work() -> tuple[list[OcrBlock], int]:
                with tempfile.TemporaryDirectory(prefix="cbz_manga_reocr_") as temp_dir:
                    image_path = Path(temp_dir) / f"page{suffix}"
                    image_path.write_bytes(image_bytes)
                    return self.ocr_fallback_engine.improve_blocks(
                        image_path,
                        page.blocks,
                        lang,
                        use_gpu=self.use_gpu(),
                        min_confidence=self.min_confidence(),
                        only_suspect=only_suspect,
                    )

            def done(result: object) -> None:
                blocks, changed = result  # type: ignore[misc]
                page.blocks = list(blocks)
                ignored = apply_review_filters(page.blocks, source_lang=lang)
                flagged = self.quality_checker.apply(page.blocks, source_lang=lang)
                page.status = "ocr_fallback_checked" if only_suspect else "ocr_deep_checked"
                scope = "suspects" if only_suspect else "tous"
                self._autosave(f"Relance OCR {scope}: {changed} bloc(s) amélioré(s), QC: {flagged} bloc(s) à vérifier")
                self.refresh_current_page()

            device = "GPU CUDA" if self.use_gpu() else "CPU"
            scope = "des blocs suspects" if only_suspect else "de tous les blocs"
            self._run_task(f"Relance OCR locale {scope} sur {device}…", work, done)

        def re_ocr_suspect_blocks(self) -> None:
            self._re_ocr_blocks(only_suspect=True)

        def re_ocr_all_blocks(self) -> None:
            self._re_ocr_blocks(only_suspect=False)

        def translate_current_page(self) -> None:
            if self.project is None:
                return
            page = self.project.pages[self.current_index]
            lang = self.selected_lang()
            if not page.blocks:
                QtWidgets.QMessageBox.information(self, "Info", "Aucun bloc OCR à traduire sur cette page.")
                return

            def work() -> list[OcrBlock]:
                apply_review_filters(page.blocks, source_lang=lang)
                return self._translate_blocks_backend(page.blocks, lang)

            def done(blocks: object) -> None:
                page.blocks = list(blocks)  # type: ignore[arg-type]
                ignored = apply_review_filters(page.blocks, source_lang=lang)
                flagged = self.quality_checker.apply(page.blocks, source_lang=lang)
                page.status = "translated"
                self._autosave(f"Traduction terminée — QC: {flagged} bloc(s) à vérifier")
                self.refresh_current_page()

            self._run_task(self._translation_task_label("Traduction page"), work, done)

        def ocr_and_translate_current_page(self) -> None:
            if self.reader is None or self.project is None:
                return
            page = self.project.pages[self.current_index]
            lang = self.selected_lang()
            image_bytes = self.reader.read_image_bytes(page.image_name)
            suffix = Path(page.image_name).suffix or ".jpg"

            def work() -> list[OcrBlock]:
                with tempfile.TemporaryDirectory(prefix="cbz_manga_ocr_") as temp_dir:
                    image_path = Path(temp_dir) / f"page{suffix}"
                    image_path.write_bytes(image_bytes)
                    blocks = self.ocr_engine.recognize(
                        image_path,
                        lang,
                        page.page_index,
                        use_gpu=self.use_gpu(),
                        min_confidence=self.min_confidence(),
                        merge_lines=self.merge_lines(),
                        filter_noise=self.filter_noise(),
                        refine_crops=self.refine_ocr(),
                    )
                    if self.fallback_ocr():
                        blocks, _changed = self.ocr_fallback_engine.improve_blocks(
                            image_path,
                            blocks,
                            lang,
                            use_gpu=self.use_gpu(),
                            min_confidence=self.min_confidence(),
                            only_suspect=True,
                        )
                    apply_review_filters(blocks, source_lang=lang)
                return self._translate_blocks_backend(blocks, lang)

            def done(blocks: object) -> None:
                page.blocks = list(blocks)  # type: ignore[arg-type]
                ignored = apply_review_filters(page.blocks, source_lang=lang)
                flagged = self.quality_checker.apply(page.blocks, source_lang=lang)
                page.status = "translated"
                self._autosave(f"OCR + traduction terminés — QC: {flagged} bloc(s) à vérifier")
                self.refresh_current_page()

            self._run_task(self._translation_task_label("OCR + traduction"), work, done)

        def quality_check_current_page(self) -> None:
            if self.project is None:
                return
            page = self.project.pages[self.current_index]
            if not page.blocks:
                QtWidgets.QMessageBox.information(self, "Info", "Aucun bloc OCR à contrôler sur cette page.")
                return
            ignored = apply_review_filters(page.blocks, source_lang=self.selected_lang())
            flagged = self.quality_checker.apply(page.blocks, source_lang=self.selected_lang())
            page.status = "quality_checked"
            self._autosave(f"Quality check terminé: {flagged} bloc(s) à vérifier")
            self.refresh_current_page()

        def save_project(self) -> None:
            if self.project is None or self.cache_path is None:
                return
            self._autosave(f"Projet sauvegardé")

        def export_html(self) -> None:
            if self.reader is None or self.project is None:
                return
            output_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choisir le dossier d'export HTML")
            if not output_dir:
                return
            try:
                self._autosave()
                index = export_html_project(self.reader, self.project, output_dir)
                self.status_label.setText(f"Export HTML: {index}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erreur export", str(exc))

        def export_analysis_dataset(self) -> None:
            if self.project is None:
                return
            output_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choisir le dossier d'export analyse")
            if not output_dir:
                return
            try:
                self._autosave()
                outputs = export_review_dataset(self.project, output_dir)
                lines = [f"{name}: {path}" for name, path in outputs.items()]
                self.status_label.setText(f"Export analyse: {outputs.get('csv')}")
                QtWidgets.QMessageBox.information(
                    self,
                    "Export analyse terminé",
                    "Fichiers créés:\n" + "\n".join(lines),
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erreur export analyse", str(exc))

    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()
