"""
views/quick_check.py
────────────────────
Quick Check screen.

A general-purpose examination flow that is NOT tied to any patient.
Flow:
  1. Doctor uploads a cell image (same upload card as New Examination)
  2. Clicks "Show Result" → AI pipeline runs
  3. Results are displayed (same 4-image grid + diagnosis badge)
  4. NO "Save Result" button, NO "Show Report" button
  5. A "New Check" button lets the doctor reset and run another image
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QFileDialog, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QBrush

from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO

WHITE        = "#FFFFFF"
RED          = "#E74C3C"
TEXT_DARK    = "#1A1A2E"
TEXT_MID     = "#6B7280"
CARD_BORDER  = "#D9E4F5"
GREEN        = "#27AE60"

POSITIVE_BG  = "#D94558"
NEGATIVE_BG  = "#27AE60"
PRECANCER_BG = "#F2A427"

PRECANCER_CLR = "#EDEAFF"
STAGE1_CLR    = "#FFFD97"
STAGE2_CLR    = "#F9A379"
STAGE3_CLR    = "#FF658E"
CIRCLE_BORDER = "#858585"

IMG_H = 200


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(weight)
    return f


def _cover_pix(path: str, w: int, h: int, r: int = 14) -> QPixmap:
    pix = QPixmap(path)
    if pix.isNull():
        return QPixmap()
    scaled = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                         Qt.SmoothTransformation)
    ox = (scaled.width()  - w) // 2
    oy = (scaled.height() - h) // 2
    scaled = scaled.copy(ox, oy, w, h)
    result = QPixmap(w, h)
    result.fill(Qt.transparent)
    p = QPainter(result)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(0, 0, w, h, r, r)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, scaled)
    p.end()
    return result


def _make_pixmap(path: str, w: int, h: int) -> QPixmap:
    pix = QPixmap(path)
    if pix.isNull():
        ph = QPixmap(w, h)
        ph.fill(QColor("#CCCCCC"))
        return ph
    scaled = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                         Qt.SmoothTransformation)
    ox = (scaled.width()  - w) // 2
    oy = (scaled.height() - h) // 2
    scaled = scaled.copy(ox, oy, w, h)
    result = QPixmap(w, h)
    result.fill(Qt.transparent)
    p = QPainter(result)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(0, 0, w, h, 10, 10)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, scaled)
    p.end()
    return result


# ─────────────────────────────────────────────────────────────
#  SPINNER  (identical to new_examination.py)
# ─────────────────────────────────────────────────────────────
class _Spinner(QWidget):
    SIZE = 60
    PW   = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setStyleSheet("background:transparent;")
        self._angle = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)

    def start(self): self._t.start(16)
    def stop(self):  self._t.stop()

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, _):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m  = self.PW // 2 + 2
        sz = self.SIZE - m * 2
        rc = QRectF(m, m, sz, sz)
        p.setPen(QPen(QColor("#D9E4F5"), self.PW, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(rc)
        p.setPen(QPen(QColor(BLUE),      self.PW, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rc, -self._angle * 16, 100 * 16)
        p.end()


# ─────────────────────────────────────────────────────────────
#  LOADING OVERLAY
# ─────────────────────────────────────────────────────────────
class _LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background:rgba(241,247,255,210);")
        self.hide()

        vl = QVBoxLayout(self)
        vl.setAlignment(Qt.AlignCenter)
        vl.setSpacing(16)

        self._spinner = _Spinner()
        vl.addWidget(self._spinner, alignment=Qt.AlignCenter)

        self._title = QLabel("Running AI models…")
        self._title.setFont(_semi(14))
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(f"color:{BLUE}; background:transparent;")
        vl.addWidget(self._title)

        self._sub = QLabel("This may take a few seconds")
        self._sub.setFont(_semi(11, QFont.Weight.Normal))
        self._sub.setAlignment(Qt.AlignCenter)
        self._sub.setStyleSheet(f"color:{TEXT_MID}; background:transparent;")
        vl.addWidget(self._sub)

    def set_text(self, t: str): self._title.setText(t)

    def show_loading(self):
        self.show()
        self.raise_()
        self._spinner.start()

    def hide_loading(self):
        self._spinner.stop()
        self.hide()

    def resizeEvent(self, e):
        if self.parent():
            self.setGeometry(self.parent().rect())


# ─────────────────────────────────────────────────────────────
#  IMAGE TILE
# ─────────────────────────────────────────────────────────────
class _ImageTile(QWidget):
    def __init__(self, path: str, caption: str, parent=None):
        super().__init__(parent)
        self._path = path
        self.setStyleSheet("background:transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)

        self._lbl = QLabel()
        self._lbl.setFixedHeight(IMG_H)
        self._lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setStyleSheet(
            "background:#CCCCCC; border-radius:10px; border:none;")
        vl.addWidget(self._lbl)

        cap = QLabel(caption)
        cap.setFont(_semi(11, QFont.Weight.Normal))
        cap.setAlignment(Qt.AlignCenter)
        cap.setFixedHeight(22)
        cap.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent; border:none;")
        vl.addWidget(cap)

        self._lbl.resizeEvent = lambda e: self._render()

    def _render(self):
        w = self._lbl.width()
        h = self._lbl.height()
        if w > 0 and h > 0:
            self._lbl.setPixmap(_make_pixmap(self._path, w, h))
            self._lbl.setStyleSheet("background:transparent; border:none;")

    def set_path(self, path: str):
        self._path = path
        self._render()


# ─────────────────────────────────────────────────────────────
#  LEGEND DOT / ROW
# ─────────────────────────────────────────────────────────────
class _Dot(QWidget):
    def __init__(self, fill, border, size=26, parent=None):
        super().__init__(parent)
        self._fill   = QColor(fill)
        self._border = QColor(border)
        self.setFixedSize(size, size)
        self.setStyleSheet("background:transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = 2
        s = self.width()
        p.setPen(self._border)
        p.setBrush(QBrush(self._fill))
        p.drawEllipse(m, m, s - m * 2, s - m * 2)
        p.end()


class _LegendRow(QWidget):
    def __init__(self, fill, text, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        hl.addWidget(_Dot(fill, CIRCLE_BORDER))
        lbl = QLabel(text)
        lbl.setFont(_semi(11, QFont.Weight.Normal))
        lbl.setStyleSheet(
            f"color:{TEXT_DARK}; background:transparent; border:none;")
        hl.addWidget(lbl)
        hl.addStretch()


# ─────────────────────────────────────────────────────────────
#  UPLOAD PAGE  (step 1)
# ─────────────────────────────────────────────────────────────
class _UploadPage(QWidget):
    """Upload card + Show Result button."""

    run_requested = Signal(str)   # emits image path

    CARD_W = 280
    CARD_H = 280

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self._image_path = ""
        self._build_ui()

    def reset(self):
        self._image_path = ""
        self._show_placeholder()
        self._del_btn.hide()
        self._run_btn.setEnabled(False)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        # Title
        title = QLabel("Quick Check")
        title.setFont(_semi(18, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_DARK}; background:transparent;")
        outer.addWidget(title)

        sub = QLabel("Upload a cell image to run a general AI examination")
        sub.setFont(_semi(11, QFont.Weight.Normal))
        sub.setStyleSheet(f"color:{TEXT_MID}; background:transparent;")
        outer.addWidget(sub)

        outer.addSpacing(8)

        # Upload card
        card = QFrame()
        card.setObjectName("qcCard")
        card.setStyleSheet(f"""
            QFrame#qcCard {{
                background:{WHITE}; border-radius:16px;
                border:1px solid {CARD_BORDER};
            }}
        """)
        card.setFixedSize(self.CARD_W, self.CARD_H)
        card.setCursor(Qt.PointingHandCursor)
        card.mousePressEvent = lambda _: self._pick()

        self._img_lbl = QLabel(card)
        self._img_lbl.setGeometry(0, 0, self.CARD_W, self.CARD_H)
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setStyleSheet("background:transparent; border:none;")

        self._del_btn = QPushButton("✕", card)
        self._del_btn.setFixedSize(28, 28)
        self._del_btn.move(8, 8)
        self._del_btn.setCursor(Qt.PointingHandCursor)
        self._del_btn.setFont(_semi(11))
        self._del_btn.setStyleSheet(f"""
            QPushButton {{ background:{RED}; color:white;
                           border-radius:14px; border:none; }}
            QPushButton:hover {{ background:#C0392B; }}
        """)
        self._del_btn.clicked.connect(self._delete)
        self._del_btn.hide()
        self._del_btn.raise_()

        self._show_placeholder()

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(card)
        row1.addStretch()
        outer.addLayout(row1)

        # Show Result button
        self._run_btn = QPushButton("Show Result")
        self._run_btn.setFixedSize(self.CARD_W, 46)
        self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.setFont(_semi(13))
        self._run_btn.setEnabled(False)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; }}
            QPushButton:hover {{ background:#0D3E8A; }}
            QPushButton:disabled {{ background:#8AAFD4; }}
        """)
        self._run_btn.clicked.connect(self._run)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addWidget(self._run_btn)
        row2.addStretch()
        outer.addLayout(row2)

        outer.addStretch()

    def _show_placeholder(self):
        self._img_lbl.setPixmap(QPixmap())
        self._img_lbl.setText("Upload Image")
        self._img_lbl.setFont(_semi(14, QFont.Weight.Normal))
        self._img_lbl.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent; border:none;")

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cell Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)")
        if not path:
            return
        self._image_path = path
        pix = _cover_pix(path, self.CARD_W, self.CARD_H)
        if not pix.isNull():
            self._img_lbl.setPixmap(pix)
            self._img_lbl.setText("")
            self._img_lbl.setStyleSheet("background:transparent; border:none;")
        self._del_btn.show()
        self._del_btn.raise_()
        self._run_btn.setEnabled(True)

    def _delete(self):
        self._image_path = ""
        self._show_placeholder()
        self._del_btn.hide()
        self._run_btn.setEnabled(False)

    def _run(self):
        if self._image_path:
            self.run_requested.emit(self._image_path)


# ─────────────────────────────────────────────────────────────
#  RESULTS PAGE  (step 2)
# ─────────────────────────────────────────────────────────────
class _ResultsPage(QWidget):
    """Shows the 4-image grid + diagnostic conclusion.
    No Save / No Show Report — just a 'New Check' button."""

    new_check_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(14)

        # ── Header row ───────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Quick Check — Result")
        title.setFont(_semi(16, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_DARK}; background:transparent;")
        hdr.addWidget(title)

        hdr.addStretch()

        self._new_btn = QPushButton("New Check")
        self._new_btn.setFixedHeight(38)
        self._new_btn.setMinimumWidth(120)
        self._new_btn.setCursor(Qt.PointingHandCursor)
        self._new_btn.setFont(_semi(12))
        self._new_btn.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; padding: 0 16px; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        self._new_btn.clicked.connect(self.new_check_requested)
        hdr.addWidget(self._new_btn)

        outer.addLayout(hdr)

        # ── Main split ───────────────────────────────────────
        main_hl = QHBoxLayout()
        main_hl.setSpacing(16)

        # LEFT — 4-image grid
        left = QFrame()
        left.setObjectName("qcLCard")
        left.setStyleSheet(f"""
            QFrame#qcLCard {{ background:{WHITE}; border-radius:16px;
                              border:1px solid {CARD_BORDER}; }}
            QFrame#qcLCard QLabel  {{ border:none; background:transparent; }}
            QFrame#qcLCard QWidget {{ border:none; }}
        """)
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left.setMaximumWidth(620)

        lv = QVBoxLayout(left)
        lv.setContentsMargins(16, 16, 16, 16)
        lv.setSpacing(16)

        r1 = QHBoxLayout(); r1.setSpacing(16)
        self._t_orig = _ImageTile("", "Original Image")
        self._t_seg  = _ImageTile("", "Segmentation Image")
        r1.addWidget(self._t_orig)
        r1.addWidget(self._t_seg)
        lv.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(16)
        self._t_heat = _ImageTile("", "Why This Type")
        self._t_cls  = _ImageTile("", "Classification Image")
        r2.addWidget(self._t_heat)
        r2.addWidget(self._t_cls)
        lv.addLayout(r2)

        main_hl.addWidget(left, 3)

        # RIGHT — diagnosis panel (no save/report buttons)
        right = QFrame()
        right.setObjectName("qcRPanel")
        right.setStyleSheet(f"""
            QFrame#qcRPanel {{ background:{WHITE}; border-radius:16px;
                               border:1px solid {CARD_BORDER}; }}
            QFrame#qcRPanel QLabel  {{ border:none; background:transparent; }}
            QFrame#qcRPanel QWidget {{ border:none; }}
        """)
        right.setFixedWidth(230)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        rp = QVBoxLayout(right)
        rp.setContentsMargins(20, 24, 20, 24)
        rp.setSpacing(20)

        t = QLabel("Diagnostic Conclusion")
        t.setFont(_semi(14))
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        t.setStyleSheet(f"color:{TEXT_DARK}; background:transparent; border:none;")
        rp.addWidget(t)

        self._badge = QLabel()
        self._badge.setFont(_semi(13, QFont.Weight.Bold))
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setFixedHeight(40)
        self._badge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rp.addWidget(self._badge)

        self._stage_lbl = QLabel()
        self._stage_lbl.setFont(_semi(16, QFont.Weight.Bold))
        self._stage_lbl.setAlignment(Qt.AlignCenter)
        self._stage_lbl.setStyleSheet(
            f"color:{TEXT_DARK}; background:transparent; border:none;")
        rp.addWidget(self._stage_lbl)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{CARD_BORDER}; border:none;")
        rp.addWidget(div)

        kl = QLabel("Classification Image Key")
        kl.setFont(_semi(11, QFont.Weight.Normal))
        kl.setAlignment(Qt.AlignCenter)
        kl.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
        rp.addWidget(kl)

        for fill, text in [(PRECANCER_CLR, "PreCancer"),
                           (STAGE1_CLR,    "Cancer - stage 1"),
                           (STAGE2_CLR,    "Cancer - stage 2"),
                           (STAGE3_CLR,    "Cancer - stage 3")]:
            rp.addWidget(_LegendRow(fill, text))

        rp.addStretch()

        # Informational note at the bottom (no action buttons)
        note = QLabel("This result is not saved\nand not linked to any patient.")
        note.setFont(_semi(10, QFont.Weight.Normal))
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
        rp.addWidget(note)

        main_hl.addWidget(right, 0)
        outer.addLayout(main_hl, 1)

    def load_result(self, result: dict):
        self._t_orig.set_path(result.get("original_path",     ""))
        self._t_seg.set_path( result.get("segmentation_path", ""))
        self._t_heat.set_path(result.get("heatmap_path",      ""))
        self._t_cls.set_path( result.get("classified_path",   ""))

        status = result.get("status", "Negative")
        stage  = result.get("stage",  "")

        bg = (POSITIVE_BG  if status == "Positive"  else
              PRECANCER_BG  if status == "PreCancer" else
              NEGATIVE_BG)

        self._badge.setText(f"  {status}  ")
        self._badge.setStyleSheet(f"""
            background:{bg}; color:white; border-radius:10px; border:none;
            font-family:{CAIRO}; font-size:14px; font-weight:700;
        """)

        is_pos = (status == "Positive")
        self._stage_lbl.setVisible(is_pos)
        if is_pos:
            self._stage_lbl.setText(stage or "")


# ─────────────────────────────────────────────────────────────
#  QUICK CHECK CONTENT  (orchestrates the two pages)
# ─────────────────────────────────────────────────────────────
class QuickCheckContent(QWidget):
    PAGE_UPLOAD  = 0
    PAGE_RESULTS = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._runner = None
        self._build_ui()

    def reset(self):
        """Called whenever the user navigates to Quick Check from the sidebar."""
        self._upload_page.reset()
        self._stack.setCurrentIndex(self.PAGE_UPLOAD)
        self._overlay.hide_loading()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background:{BG_MAIN};")

        self._upload_page  = _UploadPage()
        self._results_page = _ResultsPage()

        self._stack.addWidget(self._upload_page)    # index 0
        self._stack.addWidget(self._results_page)   # index 1

        root.addWidget(self._stack)

        # Signals
        self._upload_page.run_requested.connect(self._run)
        self._results_page.new_check_requested.connect(self._reset_to_upload)

        # Loading overlay sits on top of the whole content widget
        self._overlay = _LoadingOverlay(self)
        self._overlay.setGeometry(self.rect())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._overlay.setGeometry(self.rect())

    # ── run pipeline ─────────────────────────────────────────
    def _run(self, image_path: str):
        from core.test_runner import ModelRunner

        self._overlay.show_loading()

        self._runner = ModelRunner(image_path)
        self._runner.progress.connect(self._on_progress)
        self._runner.finished.connect(self._on_finished)
        self._runner.start()

    _PROGRESS_LABELS = {
        5:   "Reading image…",
        10:  "Running segmentation model…",
        30:  "Segmentation complete — loading classifiers…",
        50:  "Classifiers loaded — analysing tissue…",
        65:  "Classification complete — building heatmap…",
        80:  "Heatmap ready — generating Grad-CAM…",
        100: "Finalising results…",
    }

    def _on_progress(self, pct: int):
        label = self._PROGRESS_LABELS.get(pct, f"Processing… {pct}%")
        self._overlay.set_text(label)

    def _on_finished(self, result: dict):
        self._overlay.hide_loading()

        if result.get("error"):
            # Show error on the upload page without leaving it
            self._upload_page._img_lbl.setPixmap(QPixmap())
            self._upload_page._img_lbl.setText("Error running models.\nSee console.")
            self._upload_page._img_lbl.setFont(_semi(11, QFont.Weight.Normal))
            self._upload_page._img_lbl.setStyleSheet(
                f"color:{RED}; background:transparent; border:none;")
            print("[QuickCheck] model error:\n", result["error"])
            return

        self._results_page.load_result(result)
        self._stack.setCurrentIndex(self.PAGE_RESULTS)

    def _reset_to_upload(self):
        self._upload_page.reset()
        self._stack.setCurrentIndex(self.PAGE_UPLOAD)


# ─────────────────────────────────────────────────────────────
#  QUICK CHECK SCREEN  (wraps MainLayout)
# ─────────────────────────────────────────────────────────────
class QuickCheckScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Quick Check", parent=parent)
        self._content = QuickCheckContent()
        self.set_content(self._content)

    def reset(self):
        """Called by AppManager when navigating here."""
        self._content.reset()

    def on_nav(self, label: str):
        pass