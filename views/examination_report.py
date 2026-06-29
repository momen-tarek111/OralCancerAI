"""
views/examination_report.py
────────────────────────────
Detailed Patient Report screen.

FIX 2: Breadcrumb navigates back to Examination Details (not Patient Details).
FIX 3: Export PDF / Print generate a proper structured document using
        ReportLab — patient info table + all 16 patch images with labels,
        NOT a widget screenshot.
"""

import os
import tempfile

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea, QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QFont, QPixmap, QPainter, QPainterPath, QColor, QBrush, QPen,
)

from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO

WHITE       = "#FFFFFF"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"

_PATCH_COLORS = {
    "normal":  "#27AE60",
    "osmf":    "#ADD8E6",
    "pdoscc":  "#FFFF00",
    "mdoscc":  "#FFA500",
    "wdoscc":  "#FF0000",
    "unknown": "#858585",
}

_PATCH_LABELS = {
    "normal":  "Normal",
    "osmf":    "PreCancer",
    "pdoscc":  "Cancer – Stage 1",
    "mdoscc":  "Cancer – Stage 2",
    "wdoscc":  "Cancer – Stage 3",
    "unknown": "Unknown",
}

# RGB tuples for ReportLab (0-255)
_PATCH_COLORS_RGB = {
    "normal":  (39, 174, 96),
    "osmf":    (173, 216, 230),
    "pdoscc":  (255, 255, 0),
    "mdoscc":  (255, 165, 0),
    "wdoscc":  (255, 0, 0),
    "unknown": (133, 133, 133),
}


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size); f.setWeight(weight); return f


def _make_pixmap(path: str, w: int, h: int) -> QPixmap:
    pix = QPixmap(path)
    if pix.isNull():
        ph = QPixmap(w, h); ph.fill(QColor("#CCCCCC")); return ph
    scaled = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    ox = (scaled.width() - w) // 2; oy = (scaled.height() - h) // 2
    scaled = scaled.copy(ox, oy, w, h)
    result = QPixmap(w, h); result.fill(Qt.transparent)
    p = QPainter(result); p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath(); clip.addRoundedRect(0, 0, w, h, 6, 6)
    p.setClipPath(clip); p.drawPixmap(0, 0, scaled); p.end()
    return result


# ── Coloured dot ──────────────────────────────────────────────
class _PredDot(QWidget):
    def __init__(self, hex_color: str, size: int = 14, parent=None):
        super().__init__(parent)
        self._color  = QColor(hex_color)
        self._border = QColor("#858585")
        self.setFixedSize(size, size)
        self.setStyleSheet("background:transparent;")

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        m = 1; s = self.width()
        p.setPen(QPen(self._border, 1)); p.setBrush(QBrush(self._color))
        p.drawEllipse(m, m, s - m * 2, s - m * 2); p.end()


# ── Single patch tile ─────────────────────────────────────────
class _PatchTile(QWidget):
    TILE_SIZE = 110

    def __init__(self, patch_np, index: int, prediction: str,
                 tmp_path: str = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(4, 4, 4, 4); vl.setSpacing(4)
        vl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        self._img_lbl = QLabel()
        self._img_lbl.setFixedSize(self.TILE_SIZE, self.TILE_SIZE)
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setStyleSheet(
            "background:#CCCCCC; border-radius:6px; border:none;")

        if tmp_path and os.path.exists(tmp_path):
            pix = _make_pixmap(tmp_path, self.TILE_SIZE, self.TILE_SIZE)
            self._img_lbl.setPixmap(pix)
            self._img_lbl.setStyleSheet("background:transparent; border:none;")
        elif patch_np is not None:
            try:
                from PIL import Image as PILImage
                img = PILImage.fromarray(patch_np)
                fd, tmp = tempfile.mkstemp(suffix=".png", prefix="htc_patch_")
                os.close(fd); img.save(tmp)
                pix = _make_pixmap(tmp, self.TILE_SIZE, self.TILE_SIZE)
                self._img_lbl.setPixmap(pix)
                self._img_lbl.setStyleSheet("background:transparent; border:none;")
            except Exception:
                pass

        vl.addWidget(self._img_lbl, 0, Qt.AlignHCenter)

        name_lbl = QLabel(f"Patch {index}")
        name_lbl.setFont(_semi(9, QFont.Weight.Normal))
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(
            f"color:{TEXT_DARK}; background:transparent; border:none;")
        vl.addWidget(name_lbl, 0, Qt.AlignHCenter)

        dot_row = QWidget(); dot_row.setStyleSheet("background:transparent;")
        dr = QHBoxLayout(dot_row)
        dr.setContentsMargins(0, 0, 0, 0); dr.setSpacing(5)
        dr.setAlignment(Qt.AlignHCenter)
        color = _PATCH_COLORS.get(prediction, _PATCH_COLORS["unknown"])
        dr.addWidget(_PredDot(color, size=12))
        pred_lbl = QLabel(_PATCH_LABELS.get(prediction, prediction.title()))
        pred_lbl.setFont(_semi(8, QFont.Weight.Normal))
        pred_lbl.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent; border:none;")
        dr.addWidget(pred_lbl)
        vl.addWidget(dot_row, 0, Qt.AlignHCenter)


# ── Info row ──────────────────────────────────────────────────
class _InfoRow(QWidget):
    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(self); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(0)
        lbl = QLabel(label)
        lbl.setFont(_semi(11, QFont.Weight.Normal))
        lbl.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
        lbl.setFixedWidth(140); hl.addWidget(lbl)
        val = QLabel(value or "—")
        val.setFont(_semi(11, QFont.Weight.DemiBold))
        val.setWordWrap(True)
        val.setStyleSheet(f"color:{TEXT_DARK}; background:transparent; border:none;")
        hl.addWidget(val, 1)


# ─────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────
class ExaminationReportContent(QWidget):
    go_back_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._exam        = {}
        self._patient     = {}
        self._manager_ref = None
        self._patient_id  = None
        # Cache for patch data so PDF can reuse them
        self._patches      = []   # list of numpy arrays or None
        self._predictions  = []   # list of label strings
        self._patch_paths  = []   # list of tmp PNG paths
        self._build_ui()

    def set_manager(self, m): self._manager_ref = m

    def load_report(self, exam: dict, patient: dict = None,
                    patient_id: int = None):
        self._exam       = exam or {}
        self._patient    = patient or {}
        self._patient_id = patient_id or exam.get("patient_id")
        # patch_labels is a list[16] of raw label strings stored by test_runner
        # e.g. ["normal","osmf","pdoscc",...].  If present, use directly.
        # Otherwise fall back to colour-sampling the classified_path overlay.
        stored_labels = self._exam.get("patch_labels") or []
        self._patches, self._predictions, self._patch_paths = \
            _extract_patches(
                original_path   = self._exam.get("original_path",   ""),
                classified_path = self._exam.get("classified_path", ""),
                patch_labels    = stored_labels,
            )
        self._refresh_ui()

    # ── Build UI ──────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16); outer.setSpacing(14)

        # Breadcrumb
        self._bc = QPushButton()
        self._bc.setCursor(Qt.PointingHandCursor)
        self._bc.setFont(_semi(13))
        self._bc.setStyleSheet(f"""
            QPushButton {{ color:{BLUE}; background:transparent;
                           border:none; text-align:left; padding:0; }}
            QPushButton:hover {{ color:#0D3E8A; }}
        """)
        self._bc.setFixedHeight(32)
        self._bc.clicked.connect(self._go_back)
        br = QHBoxLayout(); br.setContentsMargins(0, 0, 0, 0)
        br.addWidget(self._bc); br.addStretch()
        outer.addLayout(br)

        main_hl = QHBoxLayout(); main_hl.setSpacing(16)

        # LEFT panel
        left = QFrame(); left.setObjectName("leftCard")
        left.setStyleSheet(f"""
            QFrame#leftCard {{ background:{WHITE}; border-radius:16px;
                               border:1px solid {CARD_BORDER}; }}
            QFrame#leftCard QLabel  {{ border:none; background:transparent; }}
            QFrame#leftCard QWidget {{ border:none; }}
        """)
        left.setFixedWidth(270)
        left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        lv = QVBoxLayout(left); lv.setContentsMargins(20, 24, 20, 24); lv.setSpacing(0)

        title = QLabel("Detailed Patient Report")
        title.setFont(_semi(15, QFont.Weight.Bold)); title.setWordWrap(True)
        title.setStyleSheet(f"color:{TEXT_DARK}; background:transparent; border:none;")
        lv.addWidget(title)

        sub = QLabel("Diagnostic System Verification")
        sub.setFont(_semi(10, QFont.Weight.Normal))
        sub.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
        lv.addWidget(sub); lv.addSpacing(20)

        div1 = QFrame(); div1.setFixedHeight(1)
        div1.setStyleSheet(f"background:{CARD_BORDER}; border:none;")
        lv.addWidget(div1); lv.addSpacing(16)

        self._info_container = QWidget()
        self._info_container.setStyleSheet("background:transparent;")
        self._info_vl = QVBoxLayout(self._info_container)
        self._info_vl.setContentsMargins(0, 0, 0, 0); self._info_vl.setSpacing(12)
        lv.addWidget(self._info_container)
        lv.addStretch()

        div2 = QFrame(); div2.setFixedHeight(1)
        div2.setStyleSheet(f"background:{CARD_BORDER}; border:none;")
        lv.addWidget(div2); lv.addSpacing(16)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self._btn_export = QPushButton("Export  PDF")
        self._btn_export.setFixedHeight(42); self._btn_export.setCursor(Qt.PointingHandCursor)
        self._btn_export.setFont(_semi(11))
        self._btn_export.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; padding:0 12px; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        self._btn_export.clicked.connect(self._export_pdf)
        btn_row.addWidget(self._btn_export)

        self._btn_print = QPushButton("Print")
        self._btn_print.setFixedHeight(42); self._btn_print.setCursor(Qt.PointingHandCursor)
        self._btn_print.setFont(_semi(11))
        self._btn_print.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; padding:0 22px; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        self._btn_print.clicked.connect(self._print_report)
        btn_row.addWidget(self._btn_print)
        lv.addLayout(btn_row)

        main_hl.addWidget(left)

        # RIGHT panel — patch grid
        right_outer = QFrame(); right_outer.setObjectName("rightCard")
        right_outer.setStyleSheet(f"""
            QFrame#rightCard {{ background:{WHITE}; border-radius:16px;
                                border:1px solid {CARD_BORDER}; }}
            QFrame#rightCard QLabel  {{ border:none; background:transparent; }}
            QFrame#rightCard QWidget {{ border:none; }}
        """)
        right_outer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rv = QVBoxLayout(right_outer); rv.setContentsMargins(20, 20, 20, 20); rv.setSpacing(12)

        patch_title = QLabel("Cell Image Split Matrix  (16 Patches – 4×4)")
        patch_title.setFont(_semi(13, QFont.Weight.Bold))
        patch_title.setStyleSheet(
            f"color:{TEXT_DARK}; background:transparent; border:none;")
        rv.addWidget(patch_title)

        div3 = QFrame(); div3.setFixedHeight(1)
        div3.setStyleSheet(f"background:{CARD_BORDER}; border:none;")
        rv.addWidget(div3)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background:transparent; border:none; }"
            "QScrollBar:vertical { width:8px; background:#F0F4FA; border-radius:4px; }"
            "QScrollBar::handle:vertical { background:#C5D3E8; border-radius:4px; min-height:30px; }")

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background:transparent;")
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(8); self._grid_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._grid_widget)
        rv.addWidget(scroll, 1)

        main_hl.addWidget(right_outer, 1)
        outer.addLayout(main_hl, 1)

    # ── Refresh ───────────────────────────────────────────────
    def _refresh_ui(self):
        name = self._exam.get("patient_name", "Patient")
        date = self._exam.get("date", "")
        self._bc.setText(
            f"< Patients / {name} / {date} / Report" if date
            else f"< Patients / {name} / Report")

        # Clear info rows
        for i in reversed(range(self._info_vl.count())):
            w = self._info_vl.itemAt(i).widget()
            if w: w.setParent(None)

        status = self._exam.get("status", "")
        stage  = self._exam.get("stage",  "")
        diag   = f"{status}  {stage}".strip() if status else "—"

        for label, val in [
            ("Patient Name:",      self._exam.get("patient_name", "")),
            ("Examination Date:",  self._exam.get("date", "")),
            ("Age:",               self._patient.get("age",  "")),
            ("Gender:",            self._patient.get("gender", "")),
            ("Primary Diagnosis:", diag),
            ("Analyzing Clinician:", self._exam.get("doctor_name", "")),
        ]:
            self._info_vl.addWidget(_InfoRow(label, val))

        # Rebuild patch grid
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        for idx in range(16):
            patch_np = self._patches[idx]   if idx < len(self._patches)   else None
            pred     = self._predictions[idx] if idx < len(self._predictions) else "unknown"
            ppath    = self._patch_paths[idx] if idx < len(self._patch_paths) else None
            tile = _PatchTile(patch_np, index=idx + 1, prediction=pred, tmp_path=ppath)
            self._grid_layout.addWidget(tile, idx // 4, idx % 4)

    # ── PDF / Print ───────────────────────────────────────────
    def _export_pdf(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        patient_name = self._exam.get("patient_name", "patient")
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_"
                            for c in patient_name).strip() or "patient"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report as PDF",
            f"report_{safe_name}.pdf",
            "PDF Files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        ok, msg = _build_pdf(path, self._exam, self._patient,
                             self._patch_paths, self._predictions)
        if not ok:
            QMessageBox.critical(self, "Export Failed",
                f"Could not save PDF:\n\n{msg}\n\n"
                "Ensure reportlab is installed:\n"
                "    pip install reportlab")

    def _print_report(self):
        """Build a tmp PDF then open the OS print dialog."""
        import subprocess, platform
        from PySide6.QtWidgets import QMessageBox

        fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf", prefix="htc_report_")
        os.close(fd)
        ok, msg = _build_pdf(tmp_pdf, self._exam, self._patient,
                             self._patch_paths, self._predictions)
        if not ok:
            QMessageBox.critical(self, "Print Failed",
                f"Could not generate PDF for printing:\n\n{msg}\n\n"
                "Ensure reportlab is installed:\n"
                "    pip install reportlab")
            return

        try:
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
            from PySide6.QtGui import QPainter as _QP
            printer = QPrinter(QPrinter.HighResolution)
            dlg = QPrintDialog(printer, self)
            if dlg.exec() == QPrintDialog.Accepted:
                try:
                    from pdf2image import convert_from_path
                    pages = convert_from_path(tmp_pdf, dpi=150)
                    painter = _QP(printer)
                    pr = printer.pageRect(QPrinter.DevicePixel)
                    for i, page in enumerate(pages):
                        if i > 0: printer.newPage()
                        fd2, ptmp = tempfile.mkstemp(suffix=".png")
                        os.close(fd2); page.save(ptmp)
                        pix = QPixmap(ptmp).scaled(
                            int(pr.width()), int(pr.height()),
                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        painter.drawPixmap(0, 0, pix)
                    painter.end()
                except ImportError:
                    # pdf2image not installed — hand off to OS
                    if platform.system() == "Windows":
                        os.startfile(tmp_pdf, "print")
                    else:
                        subprocess.run(["lpr", tmp_pdf])
        except Exception as e:
            print(f"[ExaminationReport] print error: {e}")

    # ── Back → Examination Details ────────────────────────────
    def _go_back(self):
        """Always return to Examination Details, never Patient Details."""
        if self._manager_ref:
            # Preferred: navigate directly to examination_details with stored data
            if hasattr(self._manager_ref, "navigate_to_examination_details_from_report"):
                self._manager_ref.navigate_to_examination_details_from_report()
            elif hasattr(self._manager_ref, "navigate_to_examination_details_back"):
                self._manager_ref.navigate_to_examination_details_back()
            elif hasattr(self._manager_ref, "go_back"):
                self._manager_ref.go_back()
        else:
            self.go_back_signal.emit()


# ─────────────────────────────────────────────────────────────
#  Patch extraction — reads predictions from classified_path colours
# ─────────────────────────────────────────────────────────────

# The colours painted by test_runner Step 4 (_COLOR dict):
#   osmf   → (173, 216, 230)  light blue
#   pdoscc → (255, 255,   0)  yellow
#   mdoscc → (255, 165,   0)  orange
#   wdoscc → (255,   0,   0)  red
#   normal → no colour applied (pixels stay close to original)
#
# Strategy per patch:
#   1. Look at the classified_path region for that patch.
#   2. Count pixels that are "close" to each colour target.
#   3. If any colour has enough coloured pixels  → that label wins.
#   4. If no colour matches  → "normal" (the patch was not painted).

# Colour targets in RGB — must match _COLOR in test_runner exactly
_CLS_TARGETS = {
    "osmf":   (173, 216, 230),
    "pdoscc": (255, 255,   0),
    "mdoscc": (255, 165,   0),
    "wdoscc": (255,   0,   0),
}
_CLS_THRESHOLD = 30    # per-channel tolerance for colour matching
_MIN_FRAC      = 0.02  # patch must have ≥2 % coloured pixels to count


def _color_distance(pixel_rgb, target_rgb):
    """Max per-channel distance between pixel and target."""
    return max(abs(int(pixel_rgb[c]) - int(target_rgb[c])) for c in range(3))


def _dominant_label_from_classified(cls_patch):
    """
    Given a numpy (H,W,3) RGB crop of the classified image,
    return the label whose colour covers the most pixels,
    or "normal" if no colour is detected above the threshold.
    """
    import numpy as np
    h, w = cls_patch.shape[:2]
    total = h * w
    if total == 0:
        return "normal"

    best_label = "normal"
    best_count = int(total * _MIN_FRAC)  # minimum to be considered

    for label, target in _CLS_TARGETS.items():
        t = np.array(target, dtype=np.int32)
        diff = np.max(np.abs(cls_patch.astype(np.int32) - t), axis=2)
        count = int(np.sum(diff <= _CLS_THRESHOLD))
        if count > best_count:
            best_count = count
            best_label = label

    return best_label


def _extract_patches(original_path: str, classified_path: str = "",
                     patch_labels: list = None):
    """
    Split the original image into a 4×4 grid of 16 patches.

    Prediction priority:
      1. patch_labels  — list[16] stored by test_runner (most accurate)
      2. colour-sample classified_path overlay (fallback)
      3. "unknown"     (if neither source available)

    Returns:
        patches     : list[16] numpy RGB arrays (or None)
        predictions : list[16] label strings
        tmp_paths   : list[16] temp PNG file paths for the patches
    """
    patches     = [None]  * 16
    predictions = ["unknown"] * 16
    tmp_paths   = [""] * 16

    if not original_path or not os.path.exists(original_path):
        return patches, predictions, tmp_paths

    try:
        import cv2
        import numpy as np

        # ── Load original image for patch thumbnails ──────────
        orig_bgr = cv2.imread(original_path)
        if orig_bgr is None:
            return patches, predictions, tmp_paths
        orig_rgb = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB)
        h, w     = orig_rgb.shape[:2]
        ph, pw   = h // 4, w // 4

        # ── Load classified image for colour sampling ─────────
        cls_rgb = None
        if classified_path and os.path.exists(classified_path):
            cls_bgr = cv2.imread(classified_path)
            if cls_bgr is not None:
                cls_rgb = cv2.cvtColor(cls_bgr, cv2.COLOR_BGR2RGB)
                # Resize to match original if needed
                if cls_rgb.shape[:2] != (h, w):
                    cls_rgb = cv2.resize(cls_rgb, (w, h),
                                         interpolation=cv2.INTER_LINEAR)

        # ── Extract each patch ────────────────────────────────
        from PIL import Image as PILImage
        for idx in range(16):
            row = idx // 4
            col = idx % 4
            y1, y2 = row * ph, (row + 1) * ph
            x1, x2 = col * pw, (col + 1) * pw

            patch = orig_rgb[y1:y2, x1:x2]
            patches[idx] = patch

            # Save patch thumbnail to a temp PNG
            try:
                fd, tmp = tempfile.mkstemp(suffix=".png", prefix="htc_patch_")
                os.close(fd)
                PILImage.fromarray(patch).save(tmp)
                tmp_paths[idx] = tmp
            except Exception:
                pass

            # Derive prediction — priority order:
            # 1. Stored label from test_runner (exact, no image needed)
            if patch_labels and idx < len(patch_labels) and patch_labels[idx]:
                predictions[idx] = patch_labels[idx]
            # 2. Colour-sample the classified overlay
            elif cls_rgb is not None:
                cls_patch        = cls_rgb[y1:y2, x1:x2]
                predictions[idx] = _dominant_label_from_classified(cls_patch)
            # 3. No source available
            else:
                predictions[idx] = "unknown"

    except Exception as e:
        print(f"[_extract_patches] error: {e}")

    return patches, predictions, tmp_paths


# ─────────────────────────────────────────────────────────────
#  ReportLab PDF builder  — returns (True, "") or (False, error_msg)
# ─────────────────────────────────────────────────────────────
def _build_pdf(output_path: str, exam: dict, patient: dict,
               patch_paths: list, predictions: list):
    """
    Build a fully structured PDF.
    Returns (True, "") on success, (False, error_message) on failure.
    Requires: pip install reportlab
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            Image as RLImage, HRFlowable,
        )
        from reportlab.graphics.shapes import Drawing, Circle, String
        from reportlab.graphics import renderPDF

        W, H = A4
        doc  = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=1.8*cm, rightMargin=1.8*cm,
            topMargin=1.5*cm,  bottomMargin=1.5*cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("ReportTitle",
            fontSize=18, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1A1A2E"),
            leading=24, spaceAfter=10, spaceBefore=0)
        sub_style = ParagraphStyle("ReportSub",
            fontSize=10, fontName="Helvetica",
            textColor=colors.HexColor("#6B7280"),
            leading=14, spaceBefore=8, spaceAfter=20)
        label_style = ParagraphStyle("InfoLabel",
            fontSize=10, fontName="Helvetica",
            textColor=colors.HexColor("#6B7280"))
        value_style = ParagraphStyle("InfoValue",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1A1A2E"))
        section_style = ParagraphStyle("Section",
            fontSize=12, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1A1A2E"), spaceBefore=14, spaceAfter=6)
        patch_name_style = ParagraphStyle("PatchName",
            fontSize=8, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1A1A2E"), alignment=TA_CENTER)
        patch_pred_style = ParagraphStyle("PatchPred",
            fontSize=7, fontName="Helvetica",
            textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER)

        story = []

        # ── Header ───────────────────────────────────────────
        story.append(Paragraph("Detailed Patient Report", title_style))
        story.append(Paragraph("Diagnostic System Verification — Hidden Truth of Cells", sub_style))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#D9E4F5"), spaceAfter=12))

        # ── Patient Info Table ───────────────────────────────
        story.append(Paragraph("Patient Information", section_style))

        status = exam.get("status", "")
        stage  = exam.get("stage",  "")
        diag   = f"{status}  {stage}".strip() if status else "—"

        info_rows = [
            ("Patient Name",      exam.get("patient_name", "—")),
            ("Examination Date",  exam.get("date", "—")),
            ("Age",               patient.get("age", "—") or "—"),
            ("Gender",            patient.get("gender", "—") or "—"),
            ("Primary Diagnosis", diag or "—"),
            ("Analyzing Clinician", exam.get("doctor_name", "—") or "—"),
        ]

        tbl_data = [[Paragraph(l, label_style), Paragraph(v, value_style)]
                    for l, v in info_rows]

        info_table = Table(tbl_data, colWidths=[5*cm, 11*cm])
        info_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#F7F9FC"), colors.white]),
            ("BOX",         (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E4F5")),
            ("INNERGRID",   (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E4F5")),
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",(0, 0), (-1, -1), 10),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#D9E4F5"), spaceAfter=6))

        # ── Patch Grid ───────────────────────────────────────
        story.append(Paragraph("Cell Image Split Matrix (16 Patches – 4×4)", section_style))

        COLS       = 4
        PATCH_W    = 3.8 * cm   # image width in PDF
        PATCH_H    = 3.8 * cm
        COL_W      = PATCH_W + 0.3 * cm

        grid_data  = []
        row_cells  = []

        for idx in range(16):
            pred  = predictions[idx] if idx < len(predictions) else "unknown"
            ppath = patch_paths[idx] if idx < len(patch_paths) else ""
            label = _PATCH_LABELS.get(pred, pred.title())
            rgb   = _PATCH_COLORS_RGB.get(pred, (133, 133, 133))
            hex_c = "#{:02X}{:02X}{:02X}".format(*rgb)

            cell_parts = []

            # Image
            if ppath and os.path.exists(ppath):
                try:
                    img_rl = RLImage(ppath, width=PATCH_W, height=PATCH_H)
                    cell_parts.append(img_rl)
                except Exception:
                    cell_parts.append(Spacer(PATCH_W, PATCH_H))
            else:
                cell_parts.append(Spacer(PATCH_W, PATCH_H))

            cell_parts.append(Spacer(1, 2))
            cell_parts.append(Paragraph(f"Patch {idx + 1}", patch_name_style))

            # Coloured dot inline with label using a tiny Drawing
            dot_size   = 8
            dot_draw   = Drawing(dot_size + 4, dot_size + 4)
            dot_draw.add(Circle(dot_size/2 + 2, dot_size/2 + 2,
                                dot_size/2,
                                fillColor=colors.HexColor(hex_c),
                                strokeColor=colors.HexColor("#858585"),
                                strokeWidth=0.5))

            pred_para  = Paragraph(label, patch_pred_style)

            # Wrap dot + label in a mini table
            dot_row_tbl = Table([[dot_draw, pred_para]],
                                colWidths=[dot_size + 6, PATCH_W - dot_size - 6])
            dot_row_tbl.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING",   (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 1),
                ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ]))
            cell_parts.append(dot_row_tbl)

            # Wrap cell_parts in a 1-col table for padding
            cell_tbl = Table([[p] for p in cell_parts],
                             colWidths=[PATCH_W])
            cell_tbl.setStyle(TableStyle([
                ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",   (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
                ("LEFTPADDING",  (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("BOX",          (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E4F5")),
                ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
                ("ROUNDEDCORNERS", [4]),
            ]))

            row_cells.append(cell_tbl)

            if len(row_cells) == COLS:
                grid_data.append(row_cells)
                row_cells = []

        if row_cells:
            # Pad last row
            while len(row_cells) < COLS:
                row_cells.append(Spacer(COL_W, 1))
            grid_data.append(row_cells)

        grid_table = Table(grid_data,
                           colWidths=[COL_W] * COLS,
                           rowHeights=None)
        grid_table.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(grid_table)

        doc.build(story)
        print(f"[ExaminationReport] PDF saved to {output_path}")
        return True, ""

    except ImportError as e:
        msg = (f"reportlab is not installed.\n"
               f"Run:  pip install reportlab\n\nDetail: {e}")
        print(f"[ExaminationReport] {msg}")
        return False, msg
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ExaminationReport] _build_pdf error:\n{tb}")
        return False, str(e)


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class ExaminationReportScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Patients", parent=parent)
        self._content = ExaminationReportContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self.set_content(self._content)

    def load_report(self, exam: dict, patient: dict = None,
                    patient_id: int = None):
        self._content.load_report(exam, patient, patient_id)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass