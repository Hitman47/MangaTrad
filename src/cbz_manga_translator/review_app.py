from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cbz_manga_translator import __version__
from cbz_manga_translator.review.model import (
    DECISIONS,
    ReviewItem,
    ReviewProject,
    apply_review_to_block,
    block_source_text,
    find_block,
    find_page,
    iter_review_items,
    load_review_project,
    review_decision_for_block,
    resolve_image_path,
    save_review_project,
)

DECISION_HELP_TEXT = """Décisions rapides :
- validate : bloc correct, rien à changer.
- correct : OCR/source/traduction corrigé(e).
- review : doute, à revoir plus tard.
- fused : bulles ou SFX fusionnés avec une bulle, à retraiter/séparer.
- ignore : bloc inutile / parasite.
- sfx : bruit, onomatopée, effet sonore."""

REVIEW_FIELD_LABELS = {
    "ocr_raw": "OCR brut — lecture machine, non modifiable",
    "ocr_corrected": "OCR corrigé — à remplir si la bulle est mal lue",
    "source_current": "Source actuelle — texte actuellement envoyé au traducteur",
    "source_corrected": "Source corrigée — reformulation propre avant traduction",
    "translation_current": "Traduction actuelle — sortie automatique",
    "translation_corrected": "Traduction FR corrigée — texte final à apprendre/garder",
    "warnings": "QC / alternatives OCR — indices pour décider",
    "notes": "Notes — doute, règle à créer, remarque libre",
}

CORRECTION_MODE_HELP = (
    "Mode correction actif : les champs modifiables sont à droite de chaque source. "
    "Corrige uniquement ce qui est nécessaire, puis utilise ‘Enregistrer correction + suivant’ "
    "ou ‘Sauvegarder seulement’. Le bouton Correction ne sauvegarde jamais tout seul."
)

REVIEW_WORKBENCH_HELP = (
    "Workflow fiable : lis la bulle sur l’image → compare la colonne SOURCE à la colonne À CORRIGER → "
    "sauvegarde avec l’action explicite. Les champs modifiables sont toujours placés à droite "
    "du texte de référence. Les changements non sauvegardés déclenchent une confirmation avant de changer de bloc."
)

FILTER_OPTIONS = [
    "À traiter",
    "Risques HIGH/MED",
    "High",
    "Tous",
    "Corrections faites",
    "À revoir",
    "Fusion",
    "Validés",
    "Ignorés",
    "SFX",
]

STATUS_COLORS = {
    "HIGH": "#7f1d1d",
    "MED": "#78350f",
    "OK": "#164e63",
}


class _LazyQt:
    QApplication = None


def _qt():
    if _LazyQt.QApplication is not None:
        return _LazyQt
    from PySide6.QtCore import Qt, QRectF, QSize
    from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    _LazyQt.Qt = Qt
    _LazyQt.QRectF = QRectF
    _LazyQt.QSize = QSize
    _LazyQt.QAction = QAction
    _LazyQt.QColor = QColor
    _LazyQt.QFont = QFont
    _LazyQt.QPainter = QPainter
    _LazyQt.QPen = QPen
    _LazyQt.QPixmap = QPixmap
    _LazyQt.QApplication = QApplication
    _LazyQt.QComboBox = QComboBox
    _LazyQt.QFileDialog = QFileDialog
    _LazyQt.QFrame = QFrame
    _LazyQt.QGridLayout = QGridLayout
    _LazyQt.QGroupBox = QGroupBox
    _LazyQt.QHBoxLayout = QHBoxLayout
    _LazyQt.QLabel = QLabel
    _LazyQt.QListWidget = QListWidget
    _LazyQt.QListWidgetItem = QListWidgetItem
    _LazyQt.QMainWindow = QMainWindow
    _LazyQt.QMessageBox = QMessageBox
    _LazyQt.QPushButton = QPushButton
    _LazyQt.QScrollArea = QScrollArea
    _LazyQt.QSplitter = QSplitter
    _LazyQt.QTextEdit = QTextEdit
    _LazyQt.QVBoxLayout = QVBoxLayout
    _LazyQt.QWidget = QWidget
    return _LazyQt


try:
    _QT_WIDGET_BASE = _qt().QWidget
    _QT_MAINWINDOW_BASE = _qt().QMainWindow
except ModuleNotFoundError:  # Allows `--version`/help in minimal CI without PySide6.
    _QT_WIDGET_BASE = object
    _QT_MAINWINDOW_BASE = object


class PageImageView(_QT_WIDGET_BASE):
    def __init__(self) -> None:
        q = _qt()
        super().__init__()
        self._pixmap = q.QPixmap()
        self._selected_bbox: list[int] | None = None
        self._all_bboxes: list[list[int]] = []
        self._image_path: Path | None = None
        self._zoom = 1.0
        self._base_size = q.QSize(520, 760)
        self.setMinimumSize(340, 520)
        self.resize(self._base_size)

    def sizeHint(self):  # type: ignore[override]
        return self._base_size

    def set_page(self, image_path: Path, selected_bbox: list[int] | None, all_bboxes: list[list[int]]) -> None:
        q = _qt()
        self._image_path = image_path
        self._pixmap = q.QPixmap(str(image_path)) if image_path.exists() else q.QPixmap()
        self._selected_bbox = selected_bbox
        self._all_bboxes = all_bboxes
        self._resize_for_zoom()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.5, min(4.0, zoom))
        self._resize_for_zoom()
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def _resize_for_zoom(self) -> None:
        q = _qt()
        width = max(340, int(self._base_size.width() * self._zoom))
        height = max(520, int(self._base_size.height() * self._zoom))
        self.setMinimumSize(q.QSize(width, height))
        self.resize(width, height)
        self.updateGeometry()

    def paintEvent(self, event):  # type: ignore[override]
        q = _qt()
        painter = q.QPainter(self)
        painter.fillRect(self.rect(), q.QColor("#0b1120"))
        if self._pixmap.isNull():
            painter.setPen(q.QColor("#f87171"))
            painter.drawText(self.rect(), q.Qt.AlignmentFlag.AlignCenter, f"Image introuvable\n{self._image_path or ''}")
            return

        view_w = max(1, self.width() - 24)
        view_h = max(1, self.height() - 24)
        scale = min(view_w / self._pixmap.width(), view_h / self._pixmap.height())
        draw_w = self._pixmap.width() * scale
        draw_h = self._pixmap.height() * scale
        offset_x = (self.width() - draw_w) / 2
        offset_y = (self.height() - draw_h) / 2
        target = q.QRectF(offset_x, offset_y, draw_w, draw_h)
        painter.drawPixmap(target, self._pixmap, q.QRectF(self._pixmap.rect()))

        def mapped_rect(bbox: list[int]) -> q.QRectF:
            x1, y1, x2, y2 = bbox
            return q.QRectF(offset_x + x1 * scale, offset_y + y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale)

        painter.setRenderHint(q.QPainter.RenderHint.Antialiasing)
        for bbox in self._all_bboxes:
            painter.setPen(q.QPen(q.QColor(148, 163, 184, 120), 1.25))
            painter.drawRect(mapped_rect(bbox))
        if self._selected_bbox:
            painter.setPen(q.QPen(q.QColor("#ef4444"), 4))
            painter.drawRect(mapped_rect(self._selected_bbox))


class ReviewWindow(_QT_MAINWINDOW_BASE):
    def __init__(self, project_path: Path | None = None, output_path: Path | None = None) -> None:
        q = _qt()
        super().__init__()
        self.setWindowTitle(f"MangaTrad Reviewer {__version__}")
        self.resize(1360, 920)
        self.review_project: ReviewProject | None = None
        self.current_item: ReviewItem | None = None
        self._items: list[ReviewItem] = []
        self._is_loading_block = False
        self._dirty = False
        self._ignore_selection_guard = False

        self.filter_combo = q.QComboBox()
        self.filter_combo.addItems(FILTER_OPTIONS)
        self.filter_combo.setToolTip("Filtre les blocs à corriger selon le niveau de risque ou le statut.")
        self.filter_combo.currentTextChanged.connect(self.refresh_list)

        self.search_box = q.QTextEdit()
        self.search_box.setPlaceholderText("Rechercher dans OCR, traduction ou warnings…")
        self.search_box.setMaximumHeight(56)
        self.search_box.textChanged.connect(self.refresh_list)

        self.queue_summary = q.QLabel("Aucun projet chargé")
        self.queue_summary.setObjectName("SmallMutedLabel")
        self.queue_summary.setWordWrap(True)

        self.list_widget = q.QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.list_widget.setToolTip("Liste des blocs. Sélectionner un bloc charge l’image et les champs de correction.")

        left = self._build_left_panel()
        self.image_view = PageImageView()
        self.zoom_label = q.QLabel("100%")
        self.zoom_label.setObjectName("SmallMutedLabel")
        right = self._build_right_panel()

        splitter = q.QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self._build_image_panel())
        splitter.addWidget(right)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([300, 470, 590])
        self.setCentralWidget(splitter)
        self._build_menu()
        self._apply_review_style()

        if project_path:
            self.open_project(project_path, output_path)
        else:
            self.open_project_dialog()

    def _build_left_panel(self):
        q = _qt()
        left = q.QWidget()
        left_layout = q.QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_title = q.QLabel("File de review")
        left_title.setObjectName("SectionTitle")
        left_layout.addWidget(left_title)
        left_layout.addWidget(self.queue_summary)
        left_layout.addWidget(q.QLabel("Filtre"))
        left_layout.addWidget(self.filter_combo)
        left_layout.addWidget(q.QLabel("Recherche"))
        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.list_widget, 1)
        return left

    def _build_image_panel(self):
        q = _qt()
        panel = q.QWidget()
        layout = q.QVBoxLayout(panel)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        controls = q.QHBoxLayout()
        zoom_out = q.QPushButton("-")
        zoom_out.setToolTip("Zoom arrière")
        zoom_out.clicked.connect(self.zoom_out)
        zoom_in = q.QPushButton("+")
        zoom_in.setToolTip("Zoom avant")
        zoom_in.clicked.connect(self.zoom_in)
        zoom_reset = q.QPushButton("100%")
        zoom_reset.setToolTip("Revenir au zoom normal")
        zoom_reset.clicked.connect(self.reset_zoom)
        zoom_fit = q.QPushButton("Adapter")
        zoom_fit.setToolTip("Adapter la page au panneau")
        zoom_fit.clicked.connect(self.fit_zoom)
        for button in (zoom_out, zoom_reset, zoom_in, zoom_fit):
            controls.addWidget(button)
        controls.addWidget(self.zoom_label)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.image_scroll = q.QScrollArea()
        self.image_scroll.setWidgetResizable(False)
        self.image_scroll.setAlignment(q.Qt.AlignmentFlag.AlignCenter)
        self.image_scroll.setWidget(self.image_view)
        layout.addWidget(self.image_scroll, 1)
        return panel

    def _build_right_panel(self):
        q = _qt()
        right = q.QWidget()
        right_layout = q.QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        title = q.QLabel("Correction du bloc sélectionné")
        title.setObjectName("SectionTitle")
        right_layout.addWidget(title)

        self.context_label = q.QLabel("Aucun projet chargé")
        self.context_label.setWordWrap(True)
        self.context_label.setObjectName("ContextLabel")
        self.context_label.setTextInteractionFlags(q.Qt.TextInteractionFlag.TextSelectableByMouse)
        right_layout.addWidget(self._panel("Contexte", self.context_label, "Chemin image, page, bloc, bbox, statut et fichier de sauvegarde."))

        self.decision_combo = q.QComboBox()
        self.decision_combo.addItems(list(DECISIONS))
        self.decision_combo.setToolTip(DECISION_HELP_TEXT)
        self.decision_combo.currentTextChanged.connect(self._mark_dirty)
        self.unsaved_label = q.QLabel("Aucune modification non sauvegardée.")
        self.unsaved_label.setObjectName("SavedLabel")
        decision_panel = q.QWidget()
        decision_layout = q.QGridLayout(decision_panel)
        decision_layout.setContentsMargins(0, 0, 0, 0)
        decision_layout.addWidget(q.QLabel("Décision"), 0, 0)
        decision_layout.addWidget(self.decision_combo, 0, 1)
        decision_layout.addWidget(self.unsaved_label, 1, 0, 1, 2)
        right_layout.addWidget(self._panel("Décision à enregistrer", decision_panel, DECISION_HELP_TEXT))

        right_layout.addWidget(self._make_action_panel())

        self.action_status = q.QLabel(REVIEW_WORKBENCH_HELP)
        self.action_status.setWordWrap(True)
        self.action_status.setObjectName("HintLabel")
        right_layout.addWidget(self.action_status)

        self.ocr_raw = self._text_area(readonly=True, min_height=96)
        self.ocr_corrected = self._text_area(readonly=False, min_height=96)
        self.source_current = self._text_area(readonly=True, min_height=96)
        self.source_corrected = self._text_area(readonly=False, min_height=96)
        self.translation_current = self._text_area(readonly=True, min_height=112)
        self.translation_corrected = self._text_area(readonly=False, min_height=112)
        self.warnings_text = self._text_area(readonly=True, min_height=140)
        self.notes_text = self._text_area(readonly=False, min_height=140)

        for edit in [self.ocr_corrected, self.source_corrected, self.translation_corrected]:
            edit.textChanged.connect(self._mark_corrected_dirty)
        self.notes_text.textChanged.connect(self._mark_dirty)

        detail_inner = q.QWidget()
        form = q.QVBoxLayout(detail_inner)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(12)
        form.addWidget(self._make_pair_panel(
            "OCR — comparer puis corriger si nécessaire",
            REVIEW_FIELD_LABELS["ocr_raw"],
            self.ocr_raw,
            REVIEW_FIELD_LABELS["ocr_corrected"],
            self.ocr_corrected,
            "Gauche = texte brut détecté. Droite = correction à apprendre si l’OCR est faux.",
        ))
        form.addWidget(self._make_pair_panel(
            "Source — texte qui doit être traduit",
            REVIEW_FIELD_LABELS["source_current"],
            self.source_current,
            REVIEW_FIELD_LABELS["source_corrected"],
            self.source_corrected,
            "Corrige ici l’anglais dialectal, les typos OCR et la phrase source avant traduction.",
        ))
        form.addWidget(self._make_pair_panel(
            "Traduction — résultat français",
            REVIEW_FIELD_LABELS["translation_current"],
            self.translation_current,
            REVIEW_FIELD_LABELS["translation_corrected"],
            self.translation_corrected,
            "Corrige ici la traduction finale qui servira à l’apprentissage.",
        ))
        form.addWidget(self._make_pair_panel(
            "Diagnostic et notes",
            REVIEW_FIELD_LABELS["warnings"],
            self.warnings_text,
            REVIEW_FIELD_LABELS["notes"],
            self.notes_text,
            "Warnings QC / alternatives OCR à gauche. Tes observations ou règle à créer à droite.",
        ))

        scroll = q.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(detail_inner)
        scroll.setMinimumWidth(420)
        right_layout.addWidget(scroll, 1)
        return right

    def _apply_review_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background: #111827; color: #e5e7eb; font-size: 13px; }
            QLabel#SectionTitle { font-size: 18px; font-weight: 800; color: #f9fafb; padding: 4px 0; }
            QLabel#ContextLabel { color: #cbd5e1; line-height: 1.25; }
            QLabel#SmallMutedLabel { color: #9ca3af; font-size: 12px; }
            QLabel#HintLabel { color: #fde68a; background: #1f2937; border: 1px solid #4b5563; border-radius: 8px; padding: 8px; }
            QLabel#DirtyLabel { color: #fbbf24; font-weight: 700; }
            QLabel#SavedLabel { color: #86efac; font-weight: 700; }
            QLabel#FieldTitle { color: #e5e7eb; font-weight: 800; padding: 3px 0; }
            QGroupBox { border: 1px solid #374151; border-radius: 8px; margin-top: 12px; padding: 12px; font-weight: 800; color: #f3f4f6; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QTextEdit, QComboBox, QListWidget { background: #1f2937; border: 1px solid #4b5563; border-radius: 6px; padding: 6px; color: #f9fafb; selection-background-color: #2563eb; }
            QTextEdit[readOnly="true"] { background: #172033; color: #d1d5db; }
            QTextEdit:focus, QComboBox:focus, QListWidget:focus { border: 1px solid #60a5fa; }
            QPushButton { background: #374151; border: 1px solid #6b7280; border-radius: 6px; padding: 8px 10px; }
            QPushButton:hover { background: #4b5563; }
            QPushButton#PrimaryButton { background: #1d4ed8; border-color: #60a5fa; font-weight: 800; }
            QPushButton#DangerButton { background: #7f1d1d; border-color: #fca5a5; }
            QScrollArea { border: 0; }
            QListWidget::item { padding: 6px; }
            """
        )

    def _build_menu(self) -> None:
        q = _qt()
        menu = self.menuBar().addMenu("Fichier")
        open_action = q.QAction("Ouvrir projet", self)
        open_action.triggered.connect(self.open_project_dialog)
        save_action = q.QAction("Sauvegarder", self)
        save_action.triggered.connect(self.save_current)
        menu.addAction(open_action)
        menu.addAction(save_action)

    def _text_area(self, *, readonly: bool, min_height: int):
        q = _qt()
        edit = q.QTextEdit()
        edit.setReadOnly(readonly)
        edit.setMinimumHeight(min_height)
        edit.setAcceptRichText(False)
        edit.setLineWrapMode(q.QTextEdit.LineWrapMode.WidgetWidth)
        font = q.QFont("Consolas")
        font.setPointSize(10)
        edit.setFont(font)
        return edit

    def _panel(self, title: str, widget, tooltip: str = ""):
        q = _qt()
        group = q.QGroupBox(title)
        if tooltip:
            group.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        layout = q.QVBoxLayout(group)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.addWidget(widget)
        return group

    def _field_label(self, text: str):
        q = _qt()
        label = q.QLabel(text)
        label.setObjectName("FieldTitle")
        return label

    def _make_pair_panel(self, title: str, left_title: str, left_widget, right_title: str, right_widget, tooltip: str):
        q = _qt()
        group = q.QGroupBox(title)
        group.setToolTip(tooltip)
        layout = q.QVBoxLayout(group)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(8)
        left_label = q.QLabel(left_title)
        left_label.setObjectName("FieldTitle")
        right_label = q.QLabel(right_title)
        right_label.setObjectName("FieldTitle")
        layout.addWidget(left_label)
        layout.addWidget(left_widget)
        layout.addWidget(right_label)
        layout.addWidget(right_widget)
        left_widget.setToolTip(tooltip)
        right_widget.setToolTip(tooltip)
        return group

    def _make_action_panel(self):
        q = _qt()
        box = q.QGroupBox("Actions explicites")
        grid = q.QGridLayout(box)
        specs = [
            ("Valider OK (V)", "validate", 0, 0, "Bloc correct : sauvegarde validate et passe au suivant.", "PrimaryButton"),
            ("Mode correction (C)", "start_correct", 0, 1, "Place le focus dans la correction FR, sans sauvegarder.", ""),
            ("Enregistrer correction + suivant", "save_next", 0, 2, "Sauvegarde les champs et passe au bloc suivant.", "PrimaryButton"),
            ("Sauvegarder seulement", "save_only", 1, 0, "Sauvegarde le bloc courant sans changer de sélection.", "PrimaryButton"),
            ("SFX (S)", "sfx", 1, 1, "Bruit / onomatopée : sauvegarde et passe au suivant.", ""),
            ("À revoir (R)", "review", 1, 2, "Marque le bloc à revoir plus tard.", ""),
            ("Ignorer (I)", "ignore", 2, 0, "Bloc parasite/inutile : sauvegarde et passe au suivant.", "DangerButton"),
            ("Bulle fusionnée", "fused", 2, 1, "Bulles/SFX fusionnés : marque fusion et passe au suivant.", ""),
            ("Précédent", "prev_only", 2, 2, "Va au bloc précédent, avec confirmation si besoin.", ""),
            ("Suivant", "next_only", 3, 2, "Va au bloc suivant, avec confirmation si besoin.", ""),
        ]
        for label, decision, row, col, tooltip, obj_name in specs:
            btn = q.QPushButton(label)
            btn.setToolTip(tooltip)
            if obj_name:
                btn.setObjectName(obj_name)
            btn.clicked.connect(lambda _checked=False, d=decision: self.apply_decision(d))
            grid.addWidget(btn, row, col)
        return box

    def open_project_dialog(self) -> None:
        q = _qt()
        path, _ = q.QFileDialog.getOpenFileName(self, "Ouvrir un projet MangaTrad", "", "Project JSON (*.json)")
        if path:
            self.open_project(Path(path), None)

    def open_project(self, project_path: Path, output_path: Path | None = None) -> None:
        q = _qt()
        try:
            self.review_project = load_review_project(project_path, output_path)
        except Exception as exc:
            q.QMessageBox.critical(self, "Erreur ouverture projet", str(exc))
            return
        self.setWindowTitle(f"MangaTrad Reviewer {__version__} — {project_path.name} → {self.review_project.output_path.name}")
        self._dirty = False
        self.refresh_list()

    def refresh_list(self, _text: str | None = None, *, select_first: bool = True) -> None:
        if not self.review_project:
            return
        q = _qt()
        filter_name = self.filter_combo.currentText()
        search = self.search_box.toPlainText().strip().lower()
        all_items = list(iter_review_items(self.review_project.project))
        self._items = []
        self.list_widget.clear()
        for item in all_items:
            if not self._item_matches_filter(item, filter_name):
                continue
            haystack = (
                f"{item.display} {item.block_id} {item.source_preview} {item.translation_preview} "
                f"{item.diagnostic_preview} {item.notes_preview}"
            ).lower()
            if search and search not in haystack:
                continue
            self._items.append(item)
            widget_item = q.QListWidgetItem(item.display)
            widget_item.setData(q.Qt.ItemDataRole.UserRole, (item.page_index, item.block_id))
            if item.risk_band in STATUS_COLORS:
                widget_item.setBackground(q.QColor(STATUS_COLORS[item.risk_band]))
            self.list_widget.addItem(widget_item)
        self._update_queue_summary(all_items, filter_name)
        self.statusBar().showMessage(f"{self.list_widget.count()} bloc(s) visibles — filtre: {filter_name}", 3000)
        if select_first and self.list_widget.count() > 0 and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

    def _update_queue_summary(self, all_items: list[ReviewItem], filter_name: str) -> None:
        total = len(all_items)
        high = sum(1 for item in all_items if item.risk_band == "HIGH")
        med = sum(1 for item in all_items if item.risk_band == "MED")
        todo = sum(1 for item in all_items if item.review_decision in {"unchecked", "review"})
        corrected = sum(1 for item in all_items if item.review_decision == "correct")
        validated = sum(1 for item in all_items if item.review_decision == "validate")
        ignored = sum(1 for item in all_items if item.review_decision == "ignore")
        sfx = sum(1 for item in all_items if item.review_decision == "sfx")
        fused = sum(1 for item in all_items if item.review_decision == "fused")
        review = sum(1 for item in all_items if item.review_decision == "review")
        self.queue_summary.setText(
            f"Total {total} · à traiter {todo} · corrigés {corrected} · validés {validated} · ignorés {ignored} · SFX {sfx} · fusion {fused}\n"
            f"HIGH {high} · MED {med} · à revoir {review} · visibles {self.list_widget.count()} · filtre : {filter_name}"
        )

    def _item_matches_filter(self, item: ReviewItem, filter_name: str) -> bool:
        if filter_name == "À traiter":
            return item.review_decision in {"unchecked", "review"}
        if filter_name == "Risques HIGH/MED":
            return item.risk_band in {"HIGH", "MED"} and item.review_decision not in {"validate", "ignore", "sfx"}
        if filter_name == "High":
            return item.risk_band == "HIGH" and item.review_decision not in {"validate", "ignore", "sfx"}
        if filter_name == "Corrections faites":
            return item.review_decision == "correct"
        if filter_name == "À revoir":
            return item.review_decision == "review"
        if filter_name == "Fusion":
            return item.review_decision == "fused"
        if filter_name == "Validés":
            return item.review_decision == "validate"
        if filter_name == "Ignorés":
            return item.review_decision == "ignore"
        if filter_name == "SFX":
            return item.review_decision == "sfx"
        return True

    def _on_selection_changed(self, current, previous) -> None:
        if self._ignore_selection_guard:
            return
        if not current or not self.review_project:
            return
        if self._dirty and previous is not None:
            choice = self._confirm_unsaved_changes()
            if choice == "cancel":
                self._ignore_selection_guard = True
                self.list_widget.setCurrentItem(previous)
                self._ignore_selection_guard = False
                return
            if choice == "save":
                self._apply_current_fields(self.decision_combo.currentText() or "correct")
            elif choice == "discard":
                self._dirty = False
                self._set_dirty_state(False)
        q = _qt()
        page_index, block_id = current.data(q.Qt.ItemDataRole.UserRole)
        self.load_block(int(page_index), str(block_id))

    def _confirm_unsaved_changes(self) -> str:
        q = _qt()
        box = q.QMessageBox(self)
        box.setWindowTitle("Modifications non sauvegardées")
        box.setText("Le bloc courant contient des modifications non sauvegardées.")
        box.setInformativeText("Sauvegarder avant de changer de bloc ?")
        save_btn = box.addButton("Sauvegarder", q.QMessageBox.ButtonRole.AcceptRole)
        discard_btn = box.addButton("Abandonner", q.QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = box.addButton("Annuler", q.QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == save_btn:
            return "save"
        if clicked == discard_btn:
            return "discard"
        if clicked == cancel_btn:
            return "cancel"
        return "cancel"

    def load_block(self, page_index: int, block_id: str) -> None:
        if not self.review_project:
            return
        self._is_loading_block = True
        try:
            project = self.review_project.project
            page = find_page(project, page_index)
            block = find_block(project, page_index, block_id)
            self.current_item = ReviewItem(
                page_index=page_index,
                block_id=block_id,
                display="",
                risk_score=0,
                risk_band="",
                manual_status=block.manual_status,
                review_decision=review_decision_for_block(block),
                source_preview="",
                translation_preview="",
                diagnostic_preview="",
                notes_preview="",
            )
            image_path = resolve_image_path(self.review_project.project_path, project, page)
            self.image_view.set_page(image_path, block.bbox, [b.bbox for b in page.blocks])
            warnings = "\n".join(block.quality_warnings)
            warnings_count = len(block.quality_warnings)
            self.context_label.setText(
                f"Page {page.page_index + 1} · Bloc {block.id} · Statut {block.manual_status} · Confiance OCR {block.confidence if block.confidence is not None else 'n/a'}\n"
                f"BBox {block.bbox} · Warnings QC {warnings_count}\n"
                f"Image : {image_path}\n"
                f"Sauvegarde : {self.review_project.output_path}"
            )
            self.ocr_raw.setPlainText(block.ocr_text)
            self.ocr_corrected.setPlainText(block.ocr_corrected_text or block.ocr_text)
            self.source_current.setPlainText(block_source_text(block))
            self.source_corrected.setPlainText(block.normalized_source_text or block.ocr_corrected_text or block.ocr_text)
            self.translation_current.setPlainText(block.translation_fr or block.raw_translation_fr)
            self.translation_corrected.setPlainText(block.translation_fr or block.raw_translation_fr)
            self.notes_text.setPlainText(getattr(block, "review_notes", ""))
            if block.ocr_alternatives:
                alt_lines = [
                    f"{idx + 1}. {alt.get('source', '?')} · score={alt.get('score', '')} · {alt.get('text', '')}"
                    for idx, alt in enumerate(block.ocr_alternatives[:10])
                ]
                warnings = (warnings + "\n\nAlternatives OCR:\n" + "\n".join(alt_lines)).strip()
            self.warnings_text.setPlainText(warnings or "Aucun warning QC / aucune alternative OCR pour ce bloc.")
            self.decision_combo.setCurrentText(review_decision_for_block(block) if block.manual_status != "unchecked" else "correct")
            self.action_status.setText("Bloc chargé. Les champs à remplir sont à droite de chaque texte de référence.")
            self._dirty = False
            self._set_dirty_state(False)
        finally:
            self._is_loading_block = False

    def _mark_dirty(self, *_args) -> None:
        if self._is_loading_block:
            return
        self._dirty = True
        self._set_dirty_state(True)

    def _mark_corrected_dirty(self) -> None:
        if self._is_loading_block:
            return
        if self.decision_combo.currentText() not in {"correct", "ignore", "sfx"}:
            self.decision_combo.setCurrentText("correct")
            self.action_status.setText("Correction détectée : la décision est passée à correct.")
        self._mark_dirty()

    def _set_dirty_state(self, dirty: bool) -> None:
        if dirty:
            self.unsaved_label.setText("Modifications non sauvegardées")
            self.unsaved_label.setObjectName("DirtyLabel")
            self.unsaved_label.style().unpolish(self.unsaved_label)
            self.unsaved_label.style().polish(self.unsaved_label)
        else:
            self.unsaved_label.setText("Aucune modification non sauvegardée.")
            self.unsaved_label.setObjectName("SavedLabel")
            self.unsaved_label.style().unpolish(self.unsaved_label)
            self.unsaved_label.style().polish(self.unsaved_label)

    def enter_correction_mode(self) -> None:
        self.decision_combo.setCurrentText("correct")
        self.action_status.setText(CORRECTION_MODE_HELP)
        self.translation_corrected.setFocus()
        self.translation_corrected.selectAll()
        self.statusBar().showMessage("Mode correction actif — modifie les champs puis utilise une action explicite.", 5000)

    def zoom_in(self) -> None:
        self._set_image_zoom(self.image_view.zoom() * 1.25)

    def zoom_out(self) -> None:
        self._set_image_zoom(self.image_view.zoom() / 1.25)

    def reset_zoom(self) -> None:
        self._set_image_zoom(1.0)

    def fit_zoom(self) -> None:
        self._set_image_zoom(1.0)
        self.image_scroll.ensureVisible(0, 0)

    def _set_image_zoom(self, zoom: float) -> None:
        self.image_view.set_zoom(zoom)
        self.zoom_label.setText(f"{round(self.image_view.zoom() * 100):.0f}%")
        self.statusBar().showMessage(f"Zoom image : {self.zoom_label.text()}", 1500)

    def _apply_current_fields(self, decision: str) -> tuple[int, str]:
        if not self.review_project or not self.current_item:
            raise RuntimeError("Aucun bloc courant à enregistrer.")
        block = find_block(self.review_project.project, self.current_item.page_index, self.current_item.block_id)
        apply_review_to_block(
            block,
            decision=decision,
            corrected_ocr=self.ocr_corrected.toPlainText(),
            corrected_source=self.source_corrected.toPlainText(),
            corrected_fr=self.translation_corrected.toPlainText(),
            notes=self.notes_text.toPlainText(),
        )
        save_review_project(self.review_project)
        self._dirty = False
        self._set_dirty_state(False)
        self.action_status.setText(f"Décision enregistrée : {decision}. Sauvegarde : {self.review_project.output_path}")
        self.statusBar().showMessage(f"Bloc enregistré ({decision}) → {self.review_project.output_path}", 5000)
        return self.current_item.page_index, self.current_item.block_id

    def save_current(self) -> None:
        if not self.review_project:
            return
        if self.current_item:
            self._apply_current_fields(self.decision_combo.currentText() or "correct")
            self.refresh_list_keep_position(advance=False)
        else:
            save_review_project(self.review_project)
            self.statusBar().showMessage(f"Sauvegardé: {self.review_project.output_path}", 4000)

    def apply_decision(self, decision: str) -> None:
        if decision == "zoom_in":
            self.zoom_in()
            return
        if decision == "zoom_out":
            self.zoom_out()
            return
        if decision == "zoom_reset":
            self.reset_zoom()
            return
        if decision == "next_only":
            self.move_selection(1)
            return
        if decision == "prev_only":
            self.move_selection(-1)
            return
        if decision == "start_correct":
            self.enter_correction_mode()
            return
        if not self.review_project or not self.current_item:
            return
        if decision == "save_only":
            self.save_current()
            return

        if decision == "save_next":
            decision = self.decision_combo.currentText() or "correct"
        else:
            self.decision_combo.setCurrentText(decision)

        old_row = self.list_widget.currentRow()
        saved_key = self._apply_current_fields(decision)
        self.refresh_list_keep_position(advance=True, previous_row=old_row, previous_key=saved_key)

    def refresh_list_keep_position(
        self,
        *,
        advance: bool,
        previous_row: int | None = None,
        previous_key: tuple[int, str] | None = None,
    ) -> None:
        previous_row = self.list_widget.currentRow() if previous_row is None else previous_row
        self.refresh_list(select_first=False)
        count = self.list_widget.count()
        if count <= 0:
            return
        target = previous_row if previous_row is not None and previous_row >= 0 else 0
        if previous_key is not None:
            for idx, item in enumerate(self._items):
                if (item.page_index, item.block_id) == previous_key:
                    target = idx + (1 if advance else 0)
                    break
            else:
                target = previous_row if previous_row is not None and previous_row >= 0 else 0
        elif advance:
            target += 1
        self.list_widget.setCurrentRow(max(0, min(count - 1, target)))

    def move_selection(self, delta: int) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        next_row = max(0, min(self.list_widget.count() - 1, row + delta))
        self.list_widget.setCurrentRow(next_row)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._dirty:
            event.accept()
            return
        choice = self._confirm_unsaved_changes()
        if choice == "save":
            self._apply_current_fields(self.decision_combo.currentText() or "correct")
            event.accept()
        elif choice == "discard":
            event.accept()
        else:
            event.ignore()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MangaTrad human review GUI")
    parser.add_argument("project", nargs="?", type=Path, help="mangatrad_corpus_project.json à reviewer")
    parser.add_argument("--out-project", type=Path, help="Chemin reviewed.json. Défaut: <project>.reviewed.json")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    q = _qt()
    app = q.QApplication(sys.argv[:1])
    window = ReviewWindow(args.project, args.out_project)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
