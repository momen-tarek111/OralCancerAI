"""
views/add_doctor.py
────────────────────
Add Doctor screen. Extends MainLayout so it shares the sidebar/navbar.
"""

import os
import shutil
import re
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QFileDialog, QSizePolicy, QComboBox,
    QApplication, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QPixmap, QIcon, QCursor, QPainter, QPainterPath

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from core.database import SessionLocal, APP_FOLDER
from models.user import ApplicationUser
from core.security import hash_password

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"

DEFAULT_IMAGE   = resource_path("assets/profile.png")
DOCTOR_IMG_DIR  = os.path.join(APP_FOLDER, "Doctor Images")


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(weight)
    return f


def _doctor_image_filename(doctor_name: str, src_path: str) -> str:
    base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", (doctor_name or "").strip())
    base_name = base_name.strip("_") or "doctor"
    ext = os.path.splitext(src_path)[1].lower() or ".png"
    return f"{base_name}_{uuid.uuid4().hex}{ext}"


def _field_style(error: bool = False) -> str:
    border_color = RED if error else "#C8D8F0"
    focus_color  = RED if error else BLUE
    return f"""
        QLineEdit {{
            border: 1px solid {border_color};
            border-radius: 10px;
            background: {WHITE};
            padding: 0 12px;
            color: {TEXT_DARK};
            font-family: {CAIRO};
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 2px solid {focus_color};
        }}
    """


class CustomDropdown(QWidget):
    value_changed = Signal(str)

    def __init__(self, options: list, parent=None):
        super().__init__(parent)
        self._options  = options
        self._selected = options[0] if options else ""
        self.setFixedHeight(44)
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btn_frame = QFrame()
        self._btn_frame.setFixedHeight(44)
        self._btn_frame.setCursor(Qt.PointingHandCursor)
        self._btn_frame.setStyleSheet(f"""
            QFrame {{ background: {WHITE}; border: 1px solid #C8D8F0; border-radius: 10px; }}
            QFrame:hover {{ border: 1px solid {BLUE}; }}
        """)
        btn_hl = QHBoxLayout(self._btn_frame)
        btn_hl.setContentsMargins(14, 0, 14, 0)
        btn_hl.setSpacing(0)

        self._text_lbl = QLabel(self._selected)
        self._text_lbl.setFont(_semi(12))
        self._text_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._text_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._arrow_lbl = QLabel("▾")
        self._arrow_lbl.setFont(QFont(CAIRO, 12))
        self._arrow_lbl.setStyleSheet(f"color: {BLUE}; background: transparent; border: none;")
        self._arrow_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        btn_hl.addWidget(self._text_lbl, 1)
        btn_hl.addWidget(self._arrow_lbl)

        self._btn_frame.mousePressEvent = lambda e: self._toggle_popup()
        self._text_lbl.mousePressEvent  = lambda e: self._toggle_popup()
        self._arrow_lbl.mousePressEvent = lambda e: self._toggle_popup()

        layout.addWidget(self._btn_frame)
        self._btn = self._btn_frame

        self._popup = QFrame()
        self._popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self._popup.setStyleSheet(f"QFrame {{ background: {WHITE}; border: 1px solid #C8D8F0; border-radius: 12px; }}")
        popup_vl = QVBoxLayout(self._popup)
        popup_vl.setContentsMargins(6, 6, 6, 6)
        popup_vl.setSpacing(2)

        for opt in options:
            item_btn = QPushButton(opt)
            item_btn.setFixedHeight(38)
            item_btn.setCursor(Qt.PointingHandCursor)
            item_btn.setFont(_semi(12))
            item_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {TEXT_DARK}; border: none;
                               border-radius: 8px; text-align: left; padding-left: 12px; }}
                QPushButton:hover {{ background: #EEF4FF; color: {BLUE}; }}
            """)
            item_btn.clicked.connect(lambda _, o=opt: self._select(o))
            popup_vl.addWidget(item_btn)

        self._popup.adjustSize()
        self._popup_open = False
        self._update_style(False)

    def _update_btn_text(self):
        if hasattr(self, '_text_lbl'):
            self._text_lbl.setText(self._selected)

    def _update_style(self, open_: bool):
        border = BLUE if open_ else "#C8D8F0"
        if hasattr(self, '_btn_frame'):
            self._btn_frame.setStyleSheet(f"""
                QFrame {{ background: {WHITE}; border: 1px solid {border}; border-radius: 10px; }}
                QFrame:hover {{ border: 1px solid {BLUE}; }}
            """)
            if hasattr(self, '_arrow_lbl'):
                self._arrow_lbl.setText("▴" if open_ else "▾")

    def _toggle_popup(self):
        if self._popup_open:
            self._popup.hide(); self._popup_open = False; self._update_style(False)
        else:
            pos = self._btn.mapToGlobal(self._btn.rect().bottomLeft())
            self._popup.move(pos)
            self._popup.setFixedWidth(self._btn.width())
            self._popup.show(); self._popup_open = True; self._update_style(True)

    def _select(self, option: str):
        self._selected = option; self._update_btn_text()
        self._popup.hide(); self._popup_open = False; self._update_style(False)
        self.value_changed.emit(option)

    def currentText(self) -> str:
        return self._selected

    def setCurrentIndex(self, idx: int):
        if 0 <= idx < len(self._options):
            self._selected = self._options[idx]
            self._update_btn_text()


class AddDoctorWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, data: dict):
        super().__init__()
        self._data = data

    def run(self):
        try:
            session = SessionLocal()
            existing = session.query(ApplicationUser).filter_by(
                email=self._data["email"]).first()
            if existing:
                session.close()
                self.finished.emit(False, "email_exists")
                return

            src_path = self._data.get("image_path", DEFAULT_IMAGE)
            if src_path and src_path != DEFAULT_IMAGE and os.path.exists(src_path):
                os.makedirs(DOCTOR_IMG_DIR, exist_ok=True)
                filename   = _doctor_image_filename(self._data.get("username", ""), src_path)
                dest       = os.path.join(DOCTOR_IMG_DIR, filename)
                shutil.copy2(src_path, dest)
                image_path = dest
            else:
                image_path = DEFAULT_IMAGE

            user = ApplicationUser(
                username             = self._data["username"],
                password_hashed      = hash_password(self._data["password"]),
                email                = self._data["email"],
                phone_number         = self._data["phone"],
                address              = self._data["address"],
                profile_image        = image_path,
                role                 = self._data["role"],
                gender               = self._data["gender"],
                added_by             = self._data.get("added_by"),
                must_change_password = True,
            )
            session.add(user)
            session.commit()
            session.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class AddDoctorContent(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._selected_image = None
        self._current_user_id = None
        self._thread = None
        self._worker = None
        self._resetting = False
        self._manager_ref = None   # set by AddDoctorScreen
        self._build_ui()

    def set_manager(self, manager):
        self._manager_ref = manager

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(16)

        # Clickable back button
        back_btn = QPushButton("< Add Doctor")
        back_btn.setFont(_semi(13))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                color: {BLUE}; background: transparent;
                border: none; text-align: left; padding: 0;
            }}
            QPushButton:hover {{ color: #0D3E8A; }}
        """)
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self._go_back)
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 0)
        back_row.addWidget(back_btn)
        back_row.addStretch()
        outer.addLayout(back_row)

        # White card
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {WHITE}; border-radius: 18px; border: 1px solid {CARD_BORDER}; }}")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card, 1)

        card_vl = QVBoxLayout(card)
        card_vl.setContentsMargins(32, 28, 32, 28)
        card_vl.setSpacing(20)

        # Avatar + title
        top_row = QHBoxLayout(); top_row.setSpacing(20)
        avatar_col = QVBoxLayout(); avatar_col.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self._avatar_lbl = QLabel()
        self._avatar_lbl.setFixedSize(80, 80)
        self._avatar_lbl.setAlignment(Qt.AlignCenter)
        self._avatar_lbl.setStyleSheet("border-radius: 40px; background: #EEF4FF; border: 2px solid #C8D8F0;")
        self._avatar_lbl.setScaledContents(False)
        self._load_default_image()

        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(f"QPushButton {{ background: {BLUE}; color: white; border-radius: 12px; border: none; font-size: 11px; }}")
        edit_btn.clicked.connect(self._pick_image)

        avatar_wrapper = QWidget()
        avatar_wrapper.setFixedSize(90, 90)
        avatar_wrapper.setStyleSheet("background: transparent;")
        self._avatar_lbl.setParent(avatar_wrapper); self._avatar_lbl.move(0, 0)
        edit_btn.setParent(avatar_wrapper); edit_btn.move(62, 58)
        avatar_col.addWidget(avatar_wrapper)
        top_row.addLayout(avatar_col)

        title_col = QVBoxLayout(); title_col.setAlignment(Qt.AlignVCenter)
        title_lbl = QLabel("Add New Doctor"); title_lbl.setFont(_semi(18))
        title_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent;")
        title_col.addWidget(title_lbl)
        top_row.addLayout(title_col); top_row.addStretch()
        card_vl.addLayout(top_row)

        # Status
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(_semi(11)); self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {RED}; background: transparent; border: none;")
        self._status_lbl.hide()
        card_vl.addWidget(self._status_lbl)

        # Form
        self._form_frame = QFrame()
        self._form_frame.setStyleSheet(f"QFrame {{ background: #F7FAFF; border-radius: 14px; border: 1px solid {CARD_BORDER}; }}")
        form_vl = QVBoxLayout(self._form_frame)
        form_vl.setContentsMargins(24, 20, 24, 20); form_vl.setSpacing(14)

        row1 = QHBoxLayout(); row1.setSpacing(16)
        self._name  = self._make_field("Full Name", "Enter Full Name")
        self._email = self._make_field("Email", "Enter Email")
        row1.addLayout(self._name[0]); row1.addLayout(self._email[0])
        form_vl.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(16)
        self._phone   = self._make_field("Phone Number", "Enter Phone Number")
        self._address = self._make_field("Address", "Enter Address")
        row2.addLayout(self._phone[0]); row2.addLayout(self._address[0])
        form_vl.addLayout(row2)

        row3 = QHBoxLayout(); row3.setSpacing(16)
        self._passwd  = self._make_field("Password", "Enter Password", pwd=True)
        self._confirm = self._make_field("Confirm Password", "Confirm Password", pwd=True)
        row3.addLayout(self._passwd[0]); row3.addLayout(self._confirm[0])
        form_vl.addLayout(row3)

        row4 = QHBoxLayout(); row4.setSpacing(16)
        role_col = QVBoxLayout(); role_col.setSpacing(4)
        role_lbl = QLabel("Role"); role_lbl.setFont(_semi(11))
        role_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._role = CustomDropdown(["DOCTOR", "ADMIN"])
        role_col.addWidget(role_lbl); role_col.addWidget(self._role)
        row4.addLayout(role_col)

        gender_col = QVBoxLayout(); gender_col.setSpacing(4)
        gender_lbl = QLabel("Gender"); gender_lbl.setFont(_semi(11))
        gender_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._gender = CustomDropdown(["Male", "Female"])
        gender_col.addWidget(gender_lbl); gender_col.addWidget(self._gender)
        row4.addLayout(gender_col)
        row4.addStretch()
        form_vl.addLayout(row4)
        card_vl.addWidget(self._form_frame)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.addStretch()
        self._add_btn = QPushButton("Add Doctor")
        self._add_btn.setFixedSize(160, 48); self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setFont(_semi(13))
        self._add_btn.setStyleSheet(f"""
            QPushButton {{ background: {BLUE}; color: white; border-radius: 10px; border: none; }}
            QPushButton:hover {{ background: #0D3E8A; }}
            QPushButton:disabled {{ background: #8AAFD4; }}
        """)
        self._add_btn.clicked.connect(self._submit)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(120, 48); cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(_semi(13))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: {WHITE}; color: {TEXT_DARK}; border-radius: 10px; border: 1px solid {CARD_BORDER}; }}
            QPushButton:hover {{ background: #F0F4FF; }}
        """)
        cancel_btn.clicked.connect(self.reset_form)
        btn_row.addWidget(self._add_btn); btn_row.addSpacing(12); btn_row.addWidget(cancel_btn)
        card_vl.addLayout(btn_row)

    def _make_field(self, label: str, placeholder: str, pwd: bool = False):
        col = QVBoxLayout(); col.setSpacing(4)
        lbl = QLabel(label); lbl.setFont(_semi(11))
        lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
        inp = QLineEdit(); inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(44); inp.setFont(_semi(11))
        if pwd: inp.setEchoMode(QLineEdit.Password)
        inp.setStyleSheet(_field_style())
        col.addWidget(lbl); col.addWidget(inp)
        return col, inp

    def _load_default_image(self):
        self._set_avatar_pixmap(DEFAULT_IMAGE)

    def _set_avatar_pixmap(self, path: str):
        size = 80
        pix  = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            if pix.width() > size or pix.height() > size:
                x = (pix.width()-size)//2; y = (pix.height()-size)//2
                pix = pix.copy(x, y, size, size)
            result = QPixmap(size, size); result.fill(Qt.transparent)
            painter = QPainter(result); painter.setRenderHint(QPainter.Antialiasing)
            path2 = QPainterPath(); path2.addEllipse(0, 0, size, size)
            painter.setClipPath(path2); painter.drawPixmap(0, 0, pix); painter.end()
            self._avatar_lbl.setPixmap(result)
        else:
            self._avatar_lbl.setText("👤"); self._avatar_lbl.setFont(QFont(CAIRO, 28))

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Profile Image", "",
                                               "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._selected_image = path
            self._set_avatar_pixmap(path)

    def _get_input(self, field_tuple):
        return field_tuple[1].text().strip()

    def _set_error(self, message: str):
        self._status_lbl.setText(message)
        self._status_lbl.setStyleSheet(f"color: {RED}; background: transparent; border: none;")
        self._status_lbl.show()
        self._form_frame.setStyleSheet(f"QFrame {{ background: #F7FAFF; border-radius: 14px; border: 2px solid {RED}; }}")

    def _clear_error(self):
        self._status_lbl.hide()
        self._form_frame.setStyleSheet(f"QFrame {{ background: #F7FAFF; border-radius: 14px; border: 1px solid {CARD_BORDER}; }}")

    def _set_loading(self, loading: bool):
        self._add_btn.setEnabled(not loading)
        self._add_btn.setText("  ⏳  Adding..." if loading else "Add Doctor")

    def _go_back(self):
        if self._manager_ref and hasattr(self._manager_ref, "go_back"):
            self._manager_ref.go_back()

    def _submit(self):
        self._clear_error()
        name = self._get_input(self._name); email = self._get_input(self._email)
        phone = self._get_input(self._phone); address = self._get_input(self._address)
        passwd = self._get_input(self._passwd); confirm = self._get_input(self._confirm)
        role = self._role.currentText(); gender = self._gender.currentText()

        if not name: self._set_error("Full Name is required."); return
        if not email: self._set_error("Email is required."); return
        if not passwd: self._set_error("Password is required."); return
        if passwd != confirm: self._set_error("Passwords do not match."); return

        data = {"username": name, "email": email, "phone": phone, "address": address,
                "password": passwd, "role": role, "gender": gender,
                "image_path": self._selected_image or DEFAULT_IMAGE,
                "added_by": self._current_user_id}

        self._set_loading(True)
        self._thread = QThread()
        self._worker = AddDoctorWorker(data)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_finished(self, success: bool, msg: str):
        self._set_loading(False)
        if success:
            self.reset_form()
            self._status_lbl.setText("✔  Doctor added successfully!")
            self._status_lbl.setStyleSheet(f"color: {GREEN}; background: transparent; border: none;")
            self._status_lbl.show()
            QTimer.singleShot(1500, self._status_lbl.hide)
        else:
            if msg == "email_exists": self._set_error("This email is already registered.")
            else: self._set_error(f"Error: {msg}")

    def reset_form(self):
        if getattr(self, '_resetting', False): return
        self._resetting = True
        try:
            self._selected_image = None; self._load_default_image()
            self._name[1].clear(); self._email[1].clear()
            self._phone[1].clear(); self._address[1].clear()
            self._passwd[1].clear(); self._confirm[1].clear()
            self._role.setCurrentIndex(0); self._gender.setCurrentIndex(0)
            self._clear_error(); self._status_lbl.hide()
        finally:
            self._resetting = False

    def set_current_user(self, user_id: int):
        self._current_user_id = user_id


class AddDoctorScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Add Doctor", parent=parent)
        self._content = AddDoctorContent()
        self._content.set_manager(manager)   # pass manager for back navigation
        self.set_content(self._content)

    def on_nav(self, label: str):
        pass

    def reset_on_enter(self):
        self._content.reset_form()

    def set_user(self, user):
        super().set_user(user)
        self._content.set_current_user(user.id)