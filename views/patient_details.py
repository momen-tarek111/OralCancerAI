"""
views/patient_details.py
─────────────────────────
Patient Details screen.
Personal information loaded from patients table.
Medical Information cards loaded from examinations table.
If no examinations exist → "No examination data available yet." message.

FIX 1: active_page="Patients" so sidebar stays highlighted.
FIX 2: _refresh_ui() only called after real data is loaded in load_patient().
FIX 3: _load_patient() safely handles missing email column on Patient model.
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea, QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QIcon

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
ORANGE      = "#F2A427"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"
ARROW_BG    = "#D4E2F7"

SCROLLBAR_STYLE = f"""
    QScrollArea {{ border:none; background:transparent; }}
    QScrollBar:vertical {{
        background:#F1F7FF; width:8px; border-radius:4px; margin:0;
    }}
    QScrollBar::handle:vertical {{
        background:#C8D8F0; border-radius:4px; min-height:30px;
    }}
    QScrollBar::handle:vertical:hover {{ background:{BLUE}; }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{ height:0px; }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical  {{ background:none; }}
"""


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size); f.setWeight(weight); return f


def _status_color(status: str) -> str:
    return (RED    if status == "Positive"  else
            GREEN  if status == "Negative"  else
            ORANGE if status == "PreCancer" else TEXT_MID)


# ─────────────────────────────────────────────────────────────
#  DB HELPERS
# ─────────────────────────────────────────────────────────────
def _load_patient(patient_id: int) -> dict:
    try:
        from core.database import SessionLocal
        from models.patient import Patient as PatientModel
        session = SessionLocal()
        p = session.get(PatientModel, patient_id)
        session.close()
        if not p:
            return {}

        doctor_name = "—"
        added_by = getattr(p, "added_by", None)
        if added_by:
            try:
                from core.database import SessionLocal as SL
                from models.user import ApplicationUser
                s2 = SL()
                doc = s2.get(ApplicationUser, added_by)
                s2.close()
                if doc:
                    doctor_name = getattr(doc, "username", "") or "—"
            except Exception:
                pass

        return {
            "name":     getattr(p, "full_name",           "") or "",
            "email":    getattr(p, "email",               "") or "",
            "address":  getattr(p, "address",             "") or "",
            "phone":    getattr(p, "phone_number",        "") or "",
            "age":      str(p.age) if getattr(p, "age", None) else "",
            "gender":   getattr(p, "gender",              "") or "",
            "added_by": doctor_name,
            "notes":    getattr(p, "medical_information", "") or "",
        }
    except Exception as e:
        print(f"[patient_details] _load_patient error: {e}")
        return {}


def _load_examinations(patient_id: int) -> list:
    """Load all examinations for this patient, newest first."""
    try:
        from core.database import SessionLocal
        from models.examination import Examination, decode_patch_labels  # ← ADDED
        session = SessionLocal()
        exams = (session.query(Examination)
                 .filter(Examination.patient_id == patient_id)
                 .order_by(Examination.created_at.desc())
                 .all())
        session.close()
        result = []
        for e in exams:
            created = e.created_at
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created[:19])
                except Exception:
                    created = None
            date_str = created.strftime("%d %b %Y") if created else "—"
            result.append({
                "exam_id":           e.id,
                "date":              date_str,
                "status":            e.status or "—",
                "stage":             e.stage  or "",
                "original_path":     e.original_image     or "",
                "segmentation_path": e.segmentation_image or "",
                "heatmap_path":      e.heatmap_image      or "",
                "classified_path":   e.classified_image   or "",
                "patch_labels":      decode_patch_labels(  # ← ADDED
                                         getattr(e, "patch_labels", None)),
            })
        return result
    except Exception as e:
        print(f"[patient_details] _load_examinations error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
#  SECTION HEADER
# ─────────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        inner.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(4)
        lbl = QLabel(title); lbl.setFont(_semi(13))
        lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        lbl.setStyleSheet(
            f"color:{TEXT_DARK}; background:transparent; border:none;")
        vl.addWidget(lbl)
        line = QFrame(); line.setFixedHeight(2)
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.setStyleSheet(f"background:{BLUE}; border:none;")
        vl.addWidget(line)
        outer.addWidget(inner); outer.addStretch()


# ─────────────────────────────────────────────────────────────
#  INFO PAIR
# ─────────────────────────────────────────────────────────────
def _info_pair(label: str, value: str) -> QWidget:
    w = QWidget(); w.setStyleSheet("background:transparent; border:none;")
    hl = QHBoxLayout(w); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(6)

    lbl = QLabel(label)
    lbl.setFont(_semi(12, QFont.Weight.Normal))
    lbl.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
    lbl.setFixedWidth(80)

    sep = QLabel(":")
    sep.setFont(_semi(12, QFont.Weight.Normal))
    sep.setStyleSheet(f"color:{TEXT_MID}; background:transparent; border:none;")
    sep.setFixedWidth(10)

    val = QLabel(value or "—")
    val.setFont(_semi(12, QFont.Weight.Bold))
    val.setStyleSheet(
        f"color:{TEXT_DARK}; background:transparent; border:none;")
    val.setWordWrap(True)

    hl.addWidget(lbl); hl.addWidget(sep); hl.addWidget(val, 1)
    return w


# ─────────────────────────────────────────────────────────────
#  EXAM CARD
# ─────────────────────────────────────────────────────────────
class ExamCard(QFrame):
    detail_clicked = Signal(dict)

    IMG_H = 170

    def __init__(self, exam: dict, parent=None):
        super().__init__(parent)
        self._exam = exam; self._raw_pix = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{ background:{WHITE}; border-radius:14px;
                      border:1px solid {CARD_BORDER}; }}
        """)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 12); vl.setSpacing(0)

        self._img_container = QWidget()
        self._img_container.setFixedHeight(self.IMG_H)
        self._img_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._img_container.setStyleSheet("background:transparent;")

        self._img_lbl = QLabel(self._img_container)
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setScaledContents(False)
        self._img_lbl.setStyleSheet(
            "background:#C8A0C8; border-radius:14px; border:none;")

        self._arrow = QPushButton("›", self._img_container)
        self._arrow.setFixedSize(28, 28)
        self._arrow.setCursor(Qt.PointingHandCursor)
        self._arrow.setFont(_semi(16))
        self._arrow.setStyleSheet(f"""
            QPushButton {{ background:{ARROW_BG}; color:{BLUE};
                           border-radius:8px; border:none; }}
            QPushButton:hover {{ background:#B8CCF0; }}
        """)
        self._arrow.clicked.connect(
            lambda: self.detail_clicked.emit(self._exam))

        orig = exam.get("original_path", "")
        pix  = QPixmap(orig) if orig else QPixmap()
        if not pix.isNull():
            self._raw_pix = pix

        self._img_container.resizeEvent = self._on_resize
        vl.addWidget(self._img_container)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(10, 8, 10, 0); bottom.setSpacing(8)

        date_lbl = QLabel(exam.get("date", ""))
        date_lbl.setFont(_semi(10, QFont.Weight.Normal))
        date_lbl.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent; border:none;")
        bottom.addWidget(date_lbl); bottom.addStretch()

        status = exam.get("status", "")
        badge  = QLabel(f"  {status}  ")
        badge.setFont(_semi(9)); badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(22)
        badge.setStyleSheet(
            f"background:{_status_color(status)}; color:white;"
            f"border-radius:11px; border:none; padding:0 4px;")
        bottom.addWidget(badge)
        vl.addLayout(bottom)

    def _on_resize(self, event):
        w = self._img_container.width()
        h = self._img_container.height()
        self._img_lbl.setGeometry(0, 0, w, h)
        self._render(w, h)
        self._arrow.move(w - self._arrow.width() - 8, 8)

    def _render(self, w: int, h: int):
        if w <= 0 or h <= 0: return
        if self._raw_pix and not self._raw_pix.isNull():
            scaled = self._raw_pix.scaled(
                w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            ox = (scaled.width() - w) // 2
            oy = (scaled.height() - h) // 2
            scaled = scaled.copy(ox, oy, w, h)
            result = QPixmap(w, h); result.fill(Qt.transparent)
            p = QPainter(result); p.setRenderHint(QPainter.Antialiasing)
            clip = QPainterPath()
            clip.addRoundedRect(0, 0, w, h, 14, 14)
            p.setClipPath(clip); p.drawPixmap(0, 0, scaled); p.end()
            self._img_lbl.setPixmap(result)
            self._img_lbl.setStyleSheet("background:transparent; border:none;")
        else:
            self._img_lbl.setStyleSheet(
                "background:#C8A0C8; border-radius:14px; border:none;")


# ─────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────
class PatientDetailsContent(QWidget):
    go_back_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._patient_id  = None
        self._patient     = {}
        self._exams       = []
        self._manager_ref = None
        self._build_ui()

    def set_manager(self, m): self._manager_ref = m

    def load_patient(self, patient_id: int):
        self._patient_id = patient_id
        self._patient    = _load_patient(patient_id)
        self._exams      = _load_examinations(patient_id)
        self._refresh_ui()

    # ── Build UI ──────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16); outer.setSpacing(14)

        top_bar = QHBoxLayout(); top_bar.setSpacing(0)
        self._back_btn = QPushButton("< Patients / Patient")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setFont(_semi(13))
        self._back_btn.setStyleSheet(f"""
            QPushButton {{ color:{BLUE}; background:transparent;
                border:none; text-align:left; padding:0; }}
            QPushButton:hover {{ color:#0D3E8A; }}
        """)
        self._back_btn.setFixedHeight(32)
        self._back_btn.clicked.connect(self._cancel)
        top_bar.addWidget(self._back_btn); top_bar.addStretch()

        new_btn = QPushButton("New Examination")
        new_btn.setFixedHeight(38); new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setFont(_semi(12))
        new_btn.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                border-radius:10px; border:none; padding:0 18px; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        new_btn.clicked.connect(self._open_new_exam)
        top_bar.addWidget(new_btn); top_bar.addSpacing(10)

        del_btn = QPushButton()
        del_btn.setFixedHeight(38); del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFont(_semi(12))
        del_btn.setStyleSheet(f"""
            QPushButton {{ background:{WHITE}; color:{RED};
                border-radius:10px; border:1px solid {RED};
                padding:0 16px; }}
            QPushButton:hover {{ background:#FFF3F3; }}
        """)
        trash_pix = QPixmap(resource_path("assets/trash.png"))
        if not trash_pix.isNull():
            del_btn.setIcon(QIcon(trash_pix.scaled(
                16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            del_btn.setText("  Delete Patient")
        else:
            del_btn.setText("🗑  Delete Patient")
        top_bar.addWidget(del_btn)
        outer.addLayout(top_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLLBAR_STYLE)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_w = QWidget(); scroll_w.setStyleSheet("background:transparent;")
        self._scroll_vl = QVBoxLayout(scroll_w)
        self._scroll_vl.setContentsMargins(0, 0, 8, 0); self._scroll_vl.setSpacing(20)

        self._info_card = QFrame()
        self._info_card.setObjectName("infoCard")
        self._info_card.setStyleSheet(f"""
            QFrame#infoCard {{ background:{WHITE}; border-radius:16px;
                border:1px solid {CARD_BORDER}; }}
            QFrame#infoCard QLabel  {{ border:none; background:transparent; }}
            QFrame#infoCard QWidget {{ border:none; }}
        """)
        info_vl = QVBoxLayout(self._info_card)
        info_vl.setContentsMargins(24, 20, 24, 20); info_vl.setSpacing(14)
        info_vl.addWidget(SectionHeader("Personal Information"))

        self._info_grid = QHBoxLayout(); self._info_grid.setSpacing(40)
        self._left_col  = QVBoxLayout(); self._left_col.setSpacing(10)
        self._right_col = QVBoxLayout(); self._right_col.setSpacing(10)
        self._info_grid.addLayout(self._left_col,  1)
        self._info_grid.addLayout(self._right_col, 1)
        info_vl.addLayout(self._info_grid)

        update_row = QHBoxLayout(); update_row.addStretch()
        update_btn = QPushButton("Update Information")
        update_btn.setFixedHeight(40); update_btn.setCursor(Qt.PointingHandCursor)
        update_btn.setFont(_semi(12))
        update_btn.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                border-radius:10px; border:none; padding:0 18px; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        update_row.addWidget(update_btn)
        info_vl.addLayout(update_row)
        self._scroll_vl.addWidget(self._info_card)

        self._medical_card = QFrame()
        self._medical_card.setObjectName("medCard")
        self._medical_card.setStyleSheet(f"""
            QFrame#medCard {{ background:{WHITE}; border-radius:16px;
                border:1px solid {CARD_BORDER}; }}
            QFrame#medCard QLabel  {{ border:none; background:transparent; }}
            QFrame#medCard QWidget {{ border:none; }}
        """)
        med_vl = QVBoxLayout(self._medical_card)
        med_vl.setContentsMargins(24, 20, 24, 20); med_vl.setSpacing(16)
        med_vl.addWidget(SectionHeader("Medical Information"))

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background:transparent;")
        self._exam_grid = QGridLayout(self._grid_widget)
        self._exam_grid.setSpacing(16); self._exam_grid.setContentsMargins(0, 0, 0, 0)
        for c in range(3):
            self._exam_grid.setColumnStretch(c, 1)
        med_vl.addWidget(self._grid_widget)

        self._no_exam_lbl = QLabel("No examination data available yet.")
        self._no_exam_lbl.setFont(_semi(12, QFont.Weight.Normal))
        self._no_exam_lbl.setAlignment(Qt.AlignCenter)
        self._no_exam_lbl.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent; padding:32px;")
        med_vl.addWidget(self._no_exam_lbl)

        self._scroll_vl.addWidget(self._medical_card)
        self._scroll_vl.addStretch()

        scroll.setWidget(scroll_w)
        outer.addWidget(scroll, 1)

    # ── Refresh ───────────────────────────────────────────────
    def _refresh_ui(self):
        p    = self._patient
        name = p.get("name", "") or "Patient"

        self._back_btn.setText(f"< Patients / {name}")

        for col in [self._left_col, self._right_col]:
            while col.count():
                item = col.takeAt(0)
                if item.widget(): item.widget().setParent(None)

        for label, key in [("Name",    "name"),
                            ("Address", "address"),
                            ("Phone",   "phone"),
                            ("Age",     "age")]:
            self._left_col.addWidget(_info_pair(label, p.get(key, "") or "—"))

        for label, key in [("Gender",   "gender"),
                            ("Added By", "added_by"),
                            ("Notes",    "notes")]:
            self._right_col.addWidget(_info_pair(label, p.get(key, "") or "—"))

        while self._exam_grid.count():
            item = self._exam_grid.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        if not self._exams:
            self._grid_widget.hide()
            self._no_exam_lbl.show()
        else:
            self._no_exam_lbl.hide()
            self._grid_widget.show()
            for i, exam in enumerate(self._exams):
                card = ExamCard(exam)
                card.detail_clicked.connect(self._open_exam)
                self._exam_grid.addWidget(card, i // 3, i % 3)

    # ── Navigation helpers ────────────────────────────────────
    def _find_manager(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, "_manager") and parent._manager:
                return parent._manager
            parent = (parent.parent()
                      if hasattr(parent, "parent") else None)
        return None

    def _cancel(self):
        if self._manager_ref and hasattr(self._manager_ref, "navigate_to"):
            self._manager_ref.navigate_to("Patients")
        else:
            self.go_back_signal.emit()

    def _open_new_exam(self):
        mgr = self._find_manager()
        if mgr and hasattr(mgr, "navigate_to_new_examination"):
            mgr.navigate_to_new_examination(
                self._patient_id,
                self._patient.get("name", "Patient"))

    def _open_exam(self, exam: dict):
        mgr = self._find_manager()
        if mgr and hasattr(mgr, "navigate_to_examination_details"):
            exam_data = dict(exam)
            exam_data["patient_name"] = self._patient.get("name", "Patient")
            mgr.navigate_to_examination_details(exam_data, self._patient_id)


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class PatientDetailsScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="", parent=parent)
        self._content = PatientDetailsContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self.set_content(self._content)

    def load_patient(self, patient_id: int):
        self._content.load_patient(patient_id)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "navigate_to"):
            self._manager.navigate_to("Patients")
        elif self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass