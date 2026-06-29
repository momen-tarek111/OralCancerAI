"""
views/add_patient.py
────────────────────
Add Patient screen. Extends MainLayout.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QSizePolicy, QTextEdit, QApplication,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from core.database import SessionLocal
from models.patient import Patient

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"


def _semi(size: int) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(QFont.Weight.DemiBold)
    return f


def _field_style(error: bool = False) -> str:
    border = RED if error else "#C8D8F0"
    focus  = RED if error else BLUE
    return f"""
        QLineEdit, QTextEdit {{
            border: 1px solid {border};
            border-radius: 10px;
            background: {WHITE};
            padding: 8px 12px;
            color: {TEXT_DARK};
            font-family: {CAIRO};
            font-size: 12px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {focus};
        }}
    """


class GenderDropdown(QWidget):
    value_changed = Signal(str)
    OPTIONS = ["Select Gender", "Male", "Female"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = "Select Gender"
        self.setFixedHeight(44)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn_frame = QFrame()
        self._btn_frame.setFixedHeight(44)
        self._btn_frame.setCursor(Qt.PointingHandCursor)
        self._apply_frame_style(False)

        hl = QHBoxLayout(self._btn_frame)
        hl.setContentsMargins(14, 0, 14, 0)

        self._text_lbl = QLabel(self._selected); self._text_lbl.setFont(_semi(12))
        self._text_lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent; border: none;")
        self._text_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._arrow_lbl = QLabel("▾"); self._arrow_lbl.setFont(QFont(CAIRO, 12))
        self._arrow_lbl.setStyleSheet(f"color: {BLUE}; background: transparent; border: none;")
        self._arrow_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        hl.addWidget(self._text_lbl, 1); hl.addWidget(self._arrow_lbl)

        self._btn_frame.mousePressEvent = lambda e: self._toggle()
        self._text_lbl.mousePressEvent  = lambda e: self._toggle()
        self._arrow_lbl.mousePressEvent = lambda e: self._toggle()
        layout.addWidget(self._btn_frame)

        self._popup = QFrame()
        self._popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self._popup.setStyleSheet(f"QFrame {{ background: {WHITE}; border: 1px solid #C8D8F0; border-radius: 12px; }}")
        popup_vl = QVBoxLayout(self._popup)
        popup_vl.setContentsMargins(6, 6, 6, 6); popup_vl.setSpacing(2)

        for opt in self.OPTIONS[1:]:
            b = QPushButton(opt); b.setFixedHeight(36); b.setCursor(Qt.PointingHandCursor)
            b.setFont(_semi(11))
            b.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {TEXT_DARK}; border: none;
                               border-radius: 8px; text-align: left; padding-left: 12px; }}
                QPushButton:hover {{ background: #EEF4FF; color: {BLUE}; }}
            """)
            b.clicked.connect(lambda _, o=opt: self._select(o))
            popup_vl.addWidget(b)

        self._popup.adjustSize()
        self._open = False

    def _apply_frame_style(self, focused: bool):
        border = BLUE if focused else "#C8D8F0"
        self._btn_frame.setStyleSheet(f"""
            QFrame {{ background: {WHITE}; border: 1px solid {border}; border-radius: 10px; }}
            QFrame:hover {{ border: 1px solid {BLUE}; }}
        """)

    def _toggle(self):
        if self._open:
            self._popup.hide(); self._open = False
            self._apply_frame_style(False); self._arrow_lbl.setText("▾")
        else:
            pos = self._btn_frame.mapToGlobal(self._btn_frame.rect().bottomLeft())
            self._popup.move(pos); self._popup.setFixedWidth(self._btn_frame.width())
            self._popup.show(); self._open = True
            self._apply_frame_style(True); self._arrow_lbl.setText("▴")

    def _select(self, opt: str):
        self._selected = opt; self._text_lbl.setText(opt)
        self._text_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._popup.hide(); self._open = False
        self._apply_frame_style(False); self._arrow_lbl.setText("▾")
        self.value_changed.emit(opt)

    def currentText(self) -> str:
        return self._selected

    def reset(self):
        self._selected = "Select Gender"; self._text_lbl.setText("Select Gender")
        self._text_lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent; border: none;")
        self._apply_frame_style(False)


class SavePatientWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, data: dict):
        super().__init__(); self._data = data

    def run(self):
        try:
            session = SessionLocal()
            patient = Patient(
                full_name           = self._data["full_name"],
                age                 = self._data["age"],
                gender              = self._data["gender"],
                phone_number        = self._data["phone"],
                address             = self._data["address"],
                medical_information = self._data["medical_info"],
                added_by            = self._data.get("added_by"),
            )
            session.add(patient); session.commit(); session.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class AddPatientContent(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._thread = None; self._worker = None
        self._current_user_id = None
        self._manager_ref = None
        self._build_ui()

    def set_manager(self, manager):
        self._manager_ref = manager

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24); outer.setSpacing(16)

        # Clickable back button
        back_btn = QPushButton("< Add Patient")
        back_btn.setFont(_semi(13)); back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                color: {BLUE}; background: transparent;
                border: none; text-align: left; padding: 0;
            }}
            QPushButton:hover {{ color: #0D3E8A; }}
        """)
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self._go_back)
        back_row = QHBoxLayout(); back_row.setContentsMargins(0,0,0,0)
        back_row.addWidget(back_btn); back_row.addStretch()
        outer.addLayout(back_row)

        # White card
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {WHITE}; border-radius: 18px; border: 1px solid {CARD_BORDER}; }}")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card, 1)

        card_vl = QVBoxLayout(card)
        card_vl.setContentsMargins(28, 24, 28, 24); card_vl.setSpacing(16)

        # Header
        header_row = QHBoxLayout(); header_row.setSpacing(16)
        icon_lbl = QLabel(); icon_lbl.setFixedSize(72, 72); icon_lbl.setAlignment(Qt.AlignCenter)
        pix = QPixmap(resource_path("assets/patient_avatar.png"))
        if not pix.isNull():
            size = 72
            pix = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            if pix.width() > size or pix.height() > size:
                x=(pix.width()-size)//2; y=(pix.height()-size)//2
                pix = pix.copy(x, y, size, size)
            result = QPixmap(size, size); result.fill(Qt.transparent)
            painter = QPainter(result); painter.setRenderHint(QPainter.Antialiasing)
            clip = QPainterPath(); clip.addEllipse(0, 0, size, size)
            painter.setClipPath(clip); painter.drawPixmap(0, 0, pix); painter.end()
            icon_lbl.setPixmap(result)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
        else:
            icon_lbl.setText("👤"); icon_lbl.setFont(QFont(CAIRO, 32))
            icon_lbl.setStyleSheet("background: #EEF4FF; border-radius: 36px; border: 2px solid #C8D8F0;")

        title_lbl = QLabel("Add New Patient"); title_lbl.setFont(_semi(18))
        title_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent;")
        header_row.addWidget(icon_lbl); header_row.addWidget(title_lbl); header_row.addStretch()
        card_vl.addLayout(header_row)

        div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background: {CARD_BORDER};")
        card_vl.addWidget(div)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(_semi(11)); self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {RED}; background: transparent; border: none;")
        self._status_lbl.hide(); card_vl.addWidget(self._status_lbl)

        # Form
        self._form_frame = QFrame()
        self._form_frame.setStyleSheet(f"QFrame {{ background: #F7FAFF; border-radius: 14px; border: 1px solid {CARD_BORDER}; }}")
        form_h = QHBoxLayout(self._form_frame)
        form_h.setContentsMargins(0,0,0,0); form_h.setSpacing(0)

        left_col = QVBoxLayout(); left_col.setContentsMargins(20,20,16,20); left_col.setSpacing(14)
        left_title = QLabel("Personal Information"); left_title.setFont(_semi(13))
        left_title.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        left_col.addWidget(left_title)

        self._name = self._make_field("Full Name", "Enter Full Name")
        left_col.addLayout(self._name[0])

        ag_row = QHBoxLayout(); ag_row.setSpacing(12)
        self._age = self._make_field("Age", "Enter Age")
        ag_row.addLayout(self._age[0])
        gender_col = QVBoxLayout(); gender_col.setSpacing(4)
        g_lbl = QLabel("Gender"); g_lbl.setFont(_semi(11))
        g_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._gender = GenderDropdown()
        gender_col.addWidget(g_lbl); gender_col.addWidget(self._gender)
        ag_row.addLayout(gender_col)
        left_col.addLayout(ag_row)

        self._phone = self._make_field("Phone Number", "Enter Phone Number")
        left_col.addLayout(self._phone[0])
        self._address = self._make_field("Address", "Enter Address")
        left_col.addLayout(self._address[0])
        left_col.addStretch()
        form_h.addLayout(left_col, 1)

        vdiv = QFrame(); vdiv.setFixedWidth(1); vdiv.setStyleSheet(f"background: {CARD_BORDER};")
        form_h.addWidget(vdiv)

        right_col = QVBoxLayout(); right_col.setContentsMargins(16,20,20,20); right_col.setSpacing(14)
        right_title = QLabel("Notes"); right_title.setFont(_semi(13))
        right_title.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        right_col.addWidget(right_title)
        self._medical = QTextEdit()
        self._medical.setPlaceholderText("Enter medical information, history, notes...")
        self._medical.setFont(_semi(11)); self._medical.setStyleSheet(_field_style())
        right_col.addWidget(self._medical, 1)
        form_h.addLayout(right_col, 1)
        card_vl.addWidget(self._form_frame, 1)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.addStretch()
        self._save_btn = QPushButton("Save Patient")
        self._save_btn.setFixedSize(160, 48); self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFont(_semi(13))
        self._save_btn.setStyleSheet(f"""
            QPushButton {{ background: {BLUE}; color: white; border-radius: 10px; border: none; }}
            QPushButton:hover {{ background: #0D3E8A; }}
            QPushButton:disabled {{ background: #8AAFD4; }}
        """)
        self._save_btn.clicked.connect(self._submit)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(120, 48); cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(_semi(13))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: {WHITE}; color: {TEXT_DARK}; border-radius: 10px; border: 1px solid {CARD_BORDER}; }}
            QPushButton:hover {{ background: #F0F4FF; }}
        """)
        cancel_btn.clicked.connect(self.reset_form)
        btn_row.addWidget(self._save_btn); btn_row.addSpacing(12); btn_row.addWidget(cancel_btn)
        card_vl.addLayout(btn_row)

    def _make_field(self, label: str, placeholder: str):
        col = QVBoxLayout(); col.setSpacing(4)
        lbl = QLabel(label); lbl.setFont(_semi(11))
        lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        inp = QLineEdit(); inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(42); inp.setFont(_semi(11)); inp.setStyleSheet(_field_style())
        col.addWidget(lbl); col.addWidget(inp)
        return col, inp

    def _set_error(self, msg: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {RED}; background: transparent; border: none;")
        self._status_lbl.show()
        self._form_frame.setStyleSheet(f"QFrame {{ background: #F7FAFF; border-radius: 14px; border: 2px solid {RED}; }}")

    def _clear_error(self):
        self._status_lbl.hide()
        self._form_frame.setStyleSheet(f"QFrame {{ background: #F7FAFF; border-radius: 14px; border: 1px solid {CARD_BORDER}; }}")

    def _set_loading(self, loading: bool):
        self._save_btn.setEnabled(not loading)
        self._save_btn.setText("  ⏳  Saving..." if loading else "Save Patient")

    def _go_back(self):
        if self._manager_ref and hasattr(self._manager_ref, "go_back"):
            self._manager_ref.go_back()

    def _submit(self):
        self._clear_error()
        full_name = self._name[1].text().strip(); age = self._age[1].text().strip()
        gender = self._gender.currentText(); phone = self._phone[1].text().strip()
        address = self._address[1].text().strip(); medical_info = self._medical.toPlainText().strip()

        if not full_name: self._set_error("Full Name is required."); return
        if gender == "Select Gender": self._set_error("Please select a gender."); return

        data = {"full_name": full_name, "age": age, "gender": gender,
                "phone": phone, "address": address, "medical_info": medical_info,
                "added_by": self._current_user_id}

        self._set_loading(True)
        self._thread = QThread()
        self._worker = SavePatientWorker(data)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_finished(self, success: bool, msg: str):
        self._set_loading(False)
        if success:
            self.reset_form()
            self._status_lbl.setText("✔  Patient added successfully!")
            self._status_lbl.setStyleSheet(f"color: {GREEN}; background: transparent; border: none;")
            self._status_lbl.show()
            QTimer.singleShot(1500, self._status_lbl.hide)
        else:
            self._set_error(f"Error: {msg}")

    def set_current_user(self, user_id: int):
        self._current_user_id = user_id

    def reset_form(self):
        self._name[1].clear(); self._age[1].clear()
        self._phone[1].clear(); self._address[1].clear()
        self._medical.clear(); self._gender.reset()
        self._clear_error(); self._status_lbl.hide()


class AddPatientScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Add Patient", parent=parent)
        self._content = AddPatientContent()
        self._content.set_manager(manager)   # pass manager for back navigation
        self.set_content(self._content)

    def set_user(self, user):
        super().set_user(user)
        self._content.set_current_user(user.id)

    def reset_on_enter(self):
        self._content.reset_form()

    def on_nav(self, label: str):
        pass