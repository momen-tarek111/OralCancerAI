"""
views/examination_details.py
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QBrush

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO

WHITE       = "#FFFFFF"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"
GREEN       = "#27AE60"

POSITIVE_BG   = "#D94558"
NEGATIVE_BG   = "#27AE60"
PRECANCER_BG  = "#F2A427"
PRECANCER_CLR = "#EDEAFF"
STAGE1_CLR    = "#FFFD97"
STAGE2_CLR    = "#F9A379"
STAGE3_CLR    = "#FF658E"
CIRCLE_BORDER = "#858585"

IMG_H = 200

DEMO_EXAM = {
    "patient_name":      "Amira Hassan",
    "date":              "15 Apr 2025",
    "status":            "Positive",
    "stage":             "Stage 2",
    "original_path":     resource_path("assets/original_image.png"),
    "segmentation_path": resource_path("assets/segmentation_image.png"),
    "heatmap_path":      resource_path("assets/why_type_image.png"),
    "classified_path":   resource_path("assets/classification_image.png"),
    "patient_id":        None,
    "doctor_id":         None,
    "exam_id":           None,
}


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(weight)
    return f


def _make_pixmap(path: str, w: int, h: int) -> QPixmap:
    pix = QPixmap(path)
    if pix.isNull():
        ph = QPixmap(w, h); ph.fill(QColor("#CCCCCC")); return ph
    scaled = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                         Qt.SmoothTransformation)
    ox = (scaled.width() - w) // 2; oy = (scaled.height() - h) // 2
    scaled = scaled.copy(ox, oy, w, h)
    result = QPixmap(w, h); result.fill(Qt.transparent)
    p = QPainter(result); p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath(); clip.addRoundedRect(0, 0, w, h, 10, 10)
    p.setClipPath(clip); p.drawPixmap(0, 0, scaled); p.end()
    return result


class ImageTile(QWidget):
    def __init__(self, path: str, caption: str, parent=None):
        super().__init__(parent)
        self._path = path
        self.setStyleSheet("background:transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(6)
        self._lbl = QLabel()
        self._lbl.setFixedHeight(IMG_H)
        self._lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setStyleSheet(
            "background:#CCCCCC; border-radius:10px; border:none;")
        vl.addWidget(self._lbl)
        cap = QLabel(caption)
        cap.setFont(_semi(11, QFont.Weight.Normal))
        cap.setAlignment(Qt.AlignCenter); cap.setFixedHeight(22)
        cap.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent; border:none;")
        vl.addWidget(cap)
        self._lbl.resizeEvent = lambda e: self._render()

    def _render(self):
        w = self._lbl.width(); h = self._lbl.height()
        if w > 0 and h > 0:
            self._lbl.setPixmap(_make_pixmap(self._path, w, h))
            self._lbl.setStyleSheet("background:transparent; border:none;")

    def set_path(self, path: str):
        self._path = path; self._render()


class _Dot(QWidget):
    def __init__(self, fill, border, size=26, parent=None):
        super().__init__(parent)
        self._fill = QColor(fill); self._border = QColor(border)
        self.setFixedSize(size, size); self.setStyleSheet("background:transparent;")
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        m=2; s=self.width()
        p.setPen(self._border); p.setBrush(QBrush(self._fill))
        p.drawEllipse(m, m, s-m*2, s-m*2); p.end()

class LegendRow(QWidget):
    def __init__(self, fill, text, parent=None):
        super().__init__(parent); self.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(self); hl.setContentsMargins(0,0,0,0); hl.setSpacing(10)
        hl.addWidget(_Dot(fill, CIRCLE_BORDER))
        lbl = QLabel(text); lbl.setFont(_semi(11, QFont.Weight.Normal))
        lbl.setStyleSheet(f"color:{TEXT_DARK}; background:transparent; border:none;")
        hl.addWidget(lbl); hl.addStretch()


class ExaminationDetailsContent(QWidget):
    go_back_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._exam        = dict(DEMO_EXAM)
        self._mode        = "view"
        self._manager_ref = None
        self._patient_id  = None
        self._saved       = False
        self._build_ui()

    def set_manager(self, m): self._manager_ref = m

    def load_exam(self, data: dict, patient_id: int = None):
        self._exam       = data if data else dict(DEMO_EXAM)
        self._patient_id = patient_id or data.get("patient_id")
        self._mode = "view"; self._saved = True
        self._refresh_ui()

    def load_new_result(self, result: dict):
        self._exam = {
            "patient_name":      result.get("patient_name", "Patient"),
            "date":              result.get("date", ""),
            "status":            result.get("status", ""),
            "stage":             result.get("stage",  ""),
            "original_path":     result.get("original_path",     ""),
            "segmentation_path": result.get("segmentation_path", ""),
            "heatmap_path":      result.get("heatmap_path",      ""),
            "classified_path":   result.get("classified_path",   ""),
            "patch_labels":      result.get("patch_labels",      []),
            "patient_id":        result.get("patient_id"),
            "doctor_id":         result.get("doctor_id"),
            "exam_id":           None,
        }
        self._patient_id = result.get("patient_id")
        self._mode = "new"; self._saved = False
        self._refresh_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(14)

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
        self._update_bc()
        br = QHBoxLayout(); br.setContentsMargins(0,0,0,0)
        br.addWidget(self._bc); br.addStretch()
        outer.addLayout(br)

        # Main split
        main_hl = QHBoxLayout(); main_hl.setSpacing(16)

        # LEFT card
        left = QFrame(); left.setObjectName("lCard")
        left.setStyleSheet(f"""
            QFrame#lCard {{ background:{WHITE}; border-radius:16px;
                            border:1px solid {CARD_BORDER}; }}
            QFrame#lCard QLabel  {{ border:none; background:transparent; }}
            QFrame#lCard QWidget {{ border:none; }}
        """)
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left.setMaximumWidth(620)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(16, 16, 16, 16); lv.setSpacing(16)

        r1 = QHBoxLayout(); r1.setSpacing(16)
        self._t_orig = ImageTile(self._exam.get("original_path",""),     "Original Image")
        self._t_seg  = ImageTile(self._exam.get("segmentation_path",""), "Segmentation Image")
        r1.addWidget(self._t_orig); r1.addWidget(self._t_seg)
        lv.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(16)
        self._t_heat = ImageTile(self._exam.get("heatmap_path",""),    "why this type")
        self._t_cls  = ImageTile(self._exam.get("classified_path",""), "Classification Image")
        r2.addWidget(self._t_heat); r2.addWidget(self._t_cls)
        lv.addLayout(r2)

        main_hl.addWidget(left, 3)

        # RIGHT panel
        right = QFrame(); right.setObjectName("rPanel")
        right.setStyleSheet(f"""
            QFrame#rPanel {{ background:{WHITE}; border-radius:16px;
                             border:1px solid {CARD_BORDER}; }}
            QFrame#rPanel QLabel  {{ border:none; background:transparent; }}
            QFrame#rPanel QWidget {{ border:none; }}
        """)
        right.setFixedWidth(230)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        rp = QVBoxLayout(right)
        rp.setContentsMargins(20, 24, 20, 24); rp.setSpacing(20)

        t = QLabel("Diagnostic Conclusion")
        t.setFont(_semi(14)); t.setAlignment(Qt.AlignCenter)
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

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet(f"background:{CARD_BORDER}; border:none;")
        rp.addWidget(div)

        kl = QLabel("Classification Image Key")
        kl.setFont(_semi(11, QFont.Weight.Normal)); kl.setAlignment(Qt.AlignCenter)
        kl.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
        rp.addWidget(kl)

        for fill, text in [(PRECANCER_CLR,"PreCancer"),
                           (STAGE1_CLR,"Cancer - stage 1"),
                           (STAGE2_CLR,"Cancer - stage 2"),
                           (STAGE3_CLR,"Cancer - stage 3")]:
            rp.addWidget(LegendRow(fill, text))

        rp.addStretch()

        self._view_report = QPushButton("Show Report")
        self._view_report.setFixedHeight(44)
        self._view_report.setCursor(Qt.PointingHandCursor)
        self._view_report.setFont(_semi(12))
        self._view_report.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        self._view_report.clicked.connect(self._open_report)
        rp.addWidget(self._view_report)

        main_hl.addWidget(right, 0)
        outer.addLayout(main_hl, 1)

        # ── Bottom bar (new mode) ─────────────────────────────
        # Mirror the main_hl split exactly:
        #   left spacer (stretch=3, maxWidth=620) | gap 16px | right buttons (fixed 230px)
        # This places the buttons precisely under the right panel.
        RIGHT_W = 230   # must match right.setFixedWidth above

        self._bb = QWidget()
        self._bb.setStyleSheet("background:transparent;")
        bb_hl = QHBoxLayout(self._bb)
        bb_hl.setContentsMargins(0, 6, 0, 0)
        bb_hl.setSpacing(0)   # spacing handled manually below

        # Invisible left spacer — expands just like the left image card
        bb_spacer = QWidget()
        bb_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bb_spacer.setMaximumWidth(620)
        bb_spacer.setStyleSheet("background:transparent;")
        bb_hl.addWidget(bb_spacer, 3)

        # 16px gap between image card and right panel
        bb_hl.addSpacing(16)

        # Right-side container — fixed width = right panel width
        right_btns = QWidget()
        right_btns.setFixedWidth(RIGHT_W)
        right_btns.setStyleSheet("background:transparent;")
        rb_hl = QHBoxLayout(right_btns)
        rb_hl.setContentsMargins(0, 0, 0, 0)
        rb_hl.setSpacing(12)

        self._saved_lbl = QLabel("✔  Result saved!")
        self._saved_lbl.setFont(_semi(11))
        self._saved_lbl.setStyleSheet(
            f"color:{GREEN}; background:transparent; border:none;")
        self._saved_lbl.hide()
        rb_hl.addWidget(self._saved_lbl)

        # Each button gets equal stretch so together they fill the 230px panel
        self._save_btn = QPushButton("Save Result")
        self._save_btn.setFixedHeight(44)
        self._save_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFont(_semi(12))
        self._save_btn.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        self._save_btn.clicked.connect(self._save_result)
        rb_hl.addWidget(self._save_btn, 1)

        self._new_report = QPushButton("Show Report")
        self._new_report.setFixedHeight(44)
        self._new_report.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._new_report.setCursor(Qt.PointingHandCursor)
        self._new_report.setFont(_semi(12))
        self._new_report.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                           border-radius:10px; border:none; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        self._new_report.clicked.connect(self._open_report)
        rb_hl.addWidget(self._new_report, 1)

        bb_hl.addWidget(right_btns)

        self._bb.hide()
        outer.addWidget(self._bb)

        self._refresh_ui()

    def _refresh_ui(self):
        self._update_bc()
        status = self._exam.get("status", "Negative")
        stage  = self._exam.get("stage",  "")

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

        self._t_orig.set_path(self._exam.get("original_path",     ""))
        self._t_seg.set_path( self._exam.get("segmentation_path", ""))
        self._t_heat.set_path(self._exam.get("heatmap_path",      ""))
        self._t_cls.set_path( self._exam.get("classified_path",   ""))

        is_new = (self._mode == "new")
        self._view_report.setVisible(not is_new)
        self._bb.setVisible(is_new)
        if is_new:
            self._save_btn.setVisible(not self._saved)
            self._saved_lbl.setVisible(False)

    def _save_result(self):
        try:
            from core.database import SessionLocal
            from models.examination import Examination, save_exam_image

            exam_date    = datetime.now()
            patient_name = self._exam.get("patient_name", "unknown")

            o = save_exam_image(patient_name, exam_date,
                                self._exam.get("original_path",     ""), "original")
            s = save_exam_image(patient_name, exam_date,
                                self._exam.get("segmentation_path", ""), "segmentation")
            h = save_exam_image(patient_name, exam_date,
                                self._exam.get("heatmap_path",      ""), "heatmap")
            c = save_exam_image(patient_name, exam_date,
                                self._exam.get("classified_path",   ""), "classified")

            from models.examination import encode_patch_labels
            session = SessionLocal()
            row = Examination(
                patient_id         = self._exam.get("patient_id"),
                doctor_id          = self._exam.get("doctor_id"),
                original_image     = o,
                segmentation_image = s,
                heatmap_image      = h,
                classified_image   = c,
                status             = self._exam.get("status", ""),
                stage              = self._exam.get("stage",  ""),
                patch_labels       = encode_patch_labels(
                                         self._exam.get("patch_labels", [])),
                created_at         = exam_date,
            )
            session.add(row)
            session.commit()
            self._exam["exam_id"] = row.id
            session.close()
        except Exception as e:
            print(f"[ExaminationDetails] _save_result error: {e}")

        self._saved = True
        self._save_btn.hide()
        self._saved_lbl.show()
        QTimer.singleShot(2000, self._saved_lbl.hide)

    def _update_bc(self):
        name = self._exam.get("patient_name", "Patient")
        date = self._exam.get("date", "")
        self._bc.setText(
            f"< Patients / {name} / {date}" if date
            else f"< Patients / {name}")

    def _go_back(self):
        if self._manager_ref and hasattr(
                self._manager_ref, "navigate_to_patient_details"):
            self._manager_ref.navigate_to_patient_details(self._patient_id)
        elif self._manager_ref and hasattr(self._manager_ref, "go_back"):
            self._manager_ref.go_back()
        else:
            self.go_back_signal.emit()

    def _open_report(self):
        if self._manager_ref and hasattr(
                self._manager_ref, "navigate_to_examination_report"):

            patient_info = {}
            pid = self._patient_id or self._exam.get("patient_id")
            if pid:
                try:
                    from core.database import SessionLocal
                    from models.patient import Patient
                    session = SessionLocal()
                    pat = session.get(Patient, pid)
                    session.close()
                    if pat:
                        patient_info = {
                            "age":    pat.age    or "",
                            "gender": pat.gender or "",
                        }
                except Exception as e:
                    print(f"[ExaminationDetails] _open_report fetch error: {e}")

            exam_copy = dict(self._exam)
            if self._manager_ref._current_user:
                u = self._manager_ref._current_user
                name = u.username
                if not name.lower().startswith("dr"):
                    name = f"Dr. {name}"
                exam_copy["doctor_name"] = name

            self._manager_ref.navigate_to_examination_report(
                exam_copy, patient_info, self._patient_id
            )


class ExaminationDetailsScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Patients", parent=parent)
        self._content = ExaminationDetailsContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self.set_content(self._content)

    def load_exam(self, data: dict, patient_id: int = None):
        self._content.load_exam(data, patient_id)

    def load_new_result(self, result: dict):
        self._content.load_new_result(result)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass