"""
views/new_examination.py
─────────────────────────
New Examination screen.

Flow:
  1. Doctor clicks the upload card → picks a cell image
  2. Image shown in the card; a red ✕ button appears top-left to remove it
  3. Doctor clicks "Show Result" → AI pipeline runs in background
  4. Animated spinner overlay covers the screen during inference
  5. On completion → navigates to Examination Details (new mode)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor

from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"


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


# ─────────────────────────────────────────────────────────────
#  SPINNER
# ─────────────────────────────────────────────────────────────
class _Spinner(QWidget):
    SIZE = 60; PW = 6

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
        p.setPen(QPen(QColor(BLUE),     self.PW, Qt.SolidLine, Qt.RoundCap))
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
        self._sub.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent;")
        vl.addWidget(self._sub)

    def set_text(self, t: str): self._title.setText(t)

    def show_loading(self):
        self.show(); self.raise_(); self._spinner.start()

    def hide_loading(self):
        self._spinner.stop(); self.hide()

    def resizeEvent(self, e):
        if self.parent():
            self.setGeometry(self.parent().rect())


# ─────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────
class NewExaminationContent(QWidget):
    go_back_signal = Signal()
    result_ready   = Signal(dict)

    CARD_W = 280
    CARD_H = 280

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image_path   = ""
        self._patient_id   = None
        self._patient_name = "Patient"
        self._manager_ref  = None
        self._runner       = None
        self._build_ui()

    def set_manager(self, m): self._manager_ref = m

    def set_patient(self, patient_id: int, patient_name: str):
        self._patient_id   = patient_id
        self._patient_name = patient_name
        self._update_bc()

    def reset(self):
        self._image_path = ""
        self._show_placeholder()
        self._del_btn.hide()
        self._run_btn.setEnabled(False)
        self._overlay.hide_loading()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(14)

        # Breadcrumb
        self._bc_btn = QPushButton()
        self._bc_btn.setCursor(Qt.PointingHandCursor)
        self._bc_btn.setFont(_semi(13))
        self._bc_btn.setStyleSheet(f"""
            QPushButton {{ color:{BLUE}; background:transparent;
                           border:none; text-align:left; padding:0; }}
            QPushButton:hover {{ color:#0D3E8A; }}
        """)
        self._bc_btn.setFixedHeight(32)
        self._bc_btn.clicked.connect(self._cancel)
        self._update_bc()

        br = QHBoxLayout()
        br.setContentsMargins(0, 0, 0, 0)
        br.addWidget(self._bc_btn); br.addStretch()
        outer.addLayout(br)

        # Upload card
        card = QFrame()
        card.setObjectName("upCard")
        card.setStyleSheet(f"""
            QFrame#upCard {{
                background:{WHITE}; border-radius:16px;
                border:1px solid {CARD_BORDER};
            }}
        """)
        card.setFixedSize(self.CARD_W, self.CARD_H)
        card.setCursor(Qt.PointingHandCursor)
        card.mousePressEvent = lambda _: self._pick()

        # Image label
        self._img_lbl = QLabel(card)
        self._img_lbl.setGeometry(0, 0, self.CARD_W, self.CARD_H)
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setStyleSheet("background:transparent; border:none;")

        # Delete button — top-left, hidden until image loaded
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
        row1.addWidget(card); row1.addStretch()
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
        row2.addWidget(self._run_btn); row2.addStretch()
        outer.addLayout(row2)

        outer.addStretch()

        # Loading overlay
        self._overlay = _LoadingOverlay(self)
        self._overlay.setGeometry(self.rect())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._overlay.setGeometry(self.rect())

    # ── image helpers ─────────────────────────────────────────
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
            self._img_lbl.setStyleSheet(
                "background:transparent; border:none;")
        self._del_btn.show(); self._del_btn.raise_()
        self._run_btn.setEnabled(True)

    def _delete(self):
        self._image_path = ""
        self._show_placeholder()
        self._del_btn.hide()
        self._run_btn.setEnabled(False)

    # ── run ───────────────────────────────────────────────────
    def _run(self):
        if not self._image_path:
            return
        from core.test_runner import ModelRunner

        self._overlay.show_loading()
        self._run_btn.setEnabled(False)

        self._runner = ModelRunner(self._image_path)
        self._runner.progress.connect(self._on_progress)
        self._runner.finished.connect(self._on_finished)
        self._runner.start()

    _PROGRESS_LABELS = {
        5:  "Reading image…",
        10: "Running segmentation model…",
        30: "Segmentation complete — loading classifiers…",
        50: "Classifiers loaded — analysing tissue…",
        65: "Classification complete — building heatmap…",
        80: "Heatmap ready — generating Grad-CAM…",
        100:"Finalising results…",
    }

    def _on_progress(self, pct: int):
        label = self._PROGRESS_LABELS.get(pct, f"Processing… {pct}%")
        self._overlay.set_text(label)

    def _on_finished(self, result: dict):
        self._overlay.hide_loading()
        self._run_btn.setEnabled(True)

        if result.get("error"):
            self._img_lbl.setPixmap(QPixmap())
            self._img_lbl.setText(f"Error running models.\nSee console.")
            self._img_lbl.setFont(_semi(11, QFont.Weight.Normal))
            self._img_lbl.setStyleSheet(
                f"color:{RED}; background:transparent; border:none;")
            print("[NewExamination] model error:\n", result["error"])
            return

        import datetime
        result["patient_id"]   = self._patient_id
        result["patient_name"] = self._patient_name
        result["date"] = datetime.datetime.now().strftime("%d %b %Y")

        self.result_ready.emit(result)

    # ── navigation ────────────────────────────────────────────
    def _update_bc(self):
        self._bc_btn.setText(
            f"< Patients / {self._patient_name} / New Examination")

    def _cancel(self):
        if self._manager_ref and hasattr(
                self._manager_ref, "navigate_to_patient_details"):
            self._manager_ref.navigate_to_patient_details(self._patient_id)
        else:
            self.go_back_signal.emit()


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class NewExaminationScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Patients", parent=parent)
        self._content = NewExaminationContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self._content.result_ready.connect(self._on_result)
        self.set_content(self._content)

    def set_patient(self, patient_id: int, patient_name: str):
        self._content.set_patient(patient_id, patient_name)
        self._content.reset()

    def _on_result(self, result: dict):
        if self._manager and hasattr(
                self._manager, "navigate_to_examination_details_new"):
            self._manager.navigate_to_examination_details_new(result)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass