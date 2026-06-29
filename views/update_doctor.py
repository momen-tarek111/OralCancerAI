"""
views/update_doctor.py
───────────────────────
Update Doctor screen — pre-filled form, no password fields.
Parent screen: Doctor Profile
"""

import os
import shutil
import re
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QPixmap, QIcon, QPainter, QPainterPath

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from views.add_doctor import CustomDropdown
from core.database import SessionLocal, APP_FOLDER
from models.user import ApplicationUser

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"

DEFAULT_IMAGE  = resource_path("assets/profile.png")
DOCTOR_IMG_DIR = os.path.join(APP_FOLDER, "Doctor Images")


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size); f.setWeight(weight); return f


def _doctor_image_filename(doctor_name: str, src_path: str) -> str:
    base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", (doctor_name or "").strip())
    base_name = base_name.strip("_") or "doctor"
    ext = os.path.splitext(src_path)[1].lower() or ".png"
    return f"{base_name}_{uuid.uuid4().hex}{ext}"


def _is_custom_doctor_image(path: str) -> bool:
    if not path:
        return False
    if path == DEFAULT_IMAGE:
        return False
    try:
        normalized = os.path.abspath(path)
        doctor_dir = os.path.abspath(DOCTOR_IMG_DIR)
        return normalized.startswith(doctor_dir)
    except Exception:
        return False


def _field_style() -> str:
    return f"""
        QLineEdit {{
            border: 1px solid #C8D8F0;
            border-radius: 10px;
            background: {WHITE};
            padding: 0 12px;
            color: {TEXT_DARK};
            font-family: {CAIRO};
            font-size: 13px;
        }}
        QLineEdit:focus {{ border: 2px solid {BLUE}; }}
    """


# ─────────────────────────────────────────────────────────────
#  WORKER
# ─────────────────────────────────────────────────────────────
class UpdateDoctorWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, user_id: int, data: dict):
        super().__init__()
        self._id   = user_id
        self._data = data

    def run(self):
        try:
            session = SessionLocal()

            # Check email uniqueness (exclude self)
            existing = session.query(ApplicationUser).filter(
                ApplicationUser.email == self._data["email"],
                ApplicationUser.id    != self._id
            ).first()
            if existing:
                session.close()
                self.finished.emit(False, "email_exists")
                return

            # Check username uniqueness (exclude self)
            existing_name = session.query(ApplicationUser).filter(
                ApplicationUser.username == self._data["username"],
                ApplicationUser.id       != self._id
            ).first()
            if existing_name:
                session.close()
                self.finished.emit(False, "name_exists")
                return

            user = session.get(ApplicationUser, self._id)
            if not user:
                session.close()
                self.finished.emit(False, "not_found")
                return

            # Handle image
            src_path = self._data.get("image_path", "")
            old_image = user.profile_image or ""
            if src_path and src_path != user.profile_image \
                    and src_path != DEFAULT_IMAGE \
                    and os.path.exists(src_path):
                os.makedirs(DOCTOR_IMG_DIR, exist_ok=True)
                filename = _doctor_image_filename(self._data.get("username", ""), src_path)
                dest     = os.path.join(DOCTOR_IMG_DIR, filename)
                shutil.copy2(src_path, dest)
                user.profile_image = dest
                # Remove old custom image after replacing with a new one.
                if _is_custom_doctor_image(old_image) and os.path.exists(old_image):
                    try:
                        os.remove(old_image)
                    except Exception:
                        pass
            elif src_path == DEFAULT_IMAGE:
                user.profile_image = DEFAULT_IMAGE
                # Remove old custom image after switching back to default.
                if _is_custom_doctor_image(old_image) and os.path.exists(old_image):
                    try:
                        os.remove(old_image)
                    except Exception:
                        pass

            user.username     = self._data["username"]
            user.email        = self._data["email"]
            user.phone_number = self._data["phone"]
            user.address      = self._data["address"]
            user.role         = self._data["role"]
            user.gender       = self._data["gender"]

            session.commit()
            session.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────
class UpdateDoctorContent(QWidget):
    go_back_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._user_id        = None
        self._selected_image = None   # new image path if changed
        self._current_image  = None   # existing image path from DB
        self._thread         = None
        self._worker         = None
        self._manager_ref    = None
        self._build_ui()

    def set_manager(self, manager):
        self._manager_ref = manager

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(16)

        # Back button
        back_btn = QPushButton("< Update Doctor")
        back_btn.setFont(_semi(13))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{ color: {BLUE}; background: transparent;
                           border: none; text-align: left; padding: 0; }}
            QPushButton:hover {{ color: #0D3E8A; }}
        """)
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self._cancel)
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 0)
        back_row.addWidget(back_btn); back_row.addStretch()
        outer.addLayout(back_row)

        # White card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background: {WHITE}; border-radius: 18px;
                      border: 1px solid {CARD_BORDER}; }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card, 1)

        card_vl = QVBoxLayout(card)
        card_vl.setContentsMargins(32, 28, 32, 28)
        card_vl.setSpacing(20)

        # Form
        self._form_frame = QFrame()
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 1px solid {CARD_BORDER}; }}
        """)
        form_vl = QVBoxLayout(self._form_frame)
        form_vl.setContentsMargins(24, 20, 24, 20)
        form_vl.setSpacing(14)

        # Avatar + title at top of form
        top_row = QHBoxLayout(); top_row.setSpacing(20)
        avatar_col = QVBoxLayout()
        avatar_col.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self._avatar_lbl = QLabel()
        self._avatar_lbl.setFixedSize(80, 80)
        self._avatar_lbl.setAlignment(Qt.AlignCenter)
        self._avatar_lbl.setStyleSheet(
            "border-radius: 40px; background: #EEF4FF; border: 2px solid #C8D8F0;")
        self._avatar_lbl.setScaledContents(False)

        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton {{ background: {BLUE}; color: white;
                           border-radius: 12px; border: none; font-size: 11px; }}
        """)
        edit_btn.clicked.connect(self._pick_image)

        # Remove image button — top-left corner (mirrors edit btn at bottom-right)
        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFixedSize(24, 24)
        self._remove_btn.setCursor(Qt.PointingHandCursor)
        self._remove_btn.setToolTip("Remove image")
        self._remove_btn.setFont(QFont(CAIRO, 10))
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{ background: {RED}; color: white;
                           border-radius: 12px; border: none; font-weight: bold; }}
            QPushButton:hover {{ background: #C0392B; }}
        """)
        self._remove_btn.clicked.connect(self._remove_image)
        self._remove_btn.hide()   # hidden until a real image is loaded

        avatar_wrapper = QWidget()
        avatar_wrapper.setFixedSize(90, 90)
        avatar_wrapper.setStyleSheet("background: transparent;")
        self._avatar_lbl.setParent(avatar_wrapper); self._avatar_lbl.move(0, 0)
        edit_btn.setParent(avatar_wrapper);         edit_btn.move(62, 58)   # bottom-right
        self._remove_btn.setParent(avatar_wrapper); self._remove_btn.move(0, 0)  # top-left
        avatar_col.addWidget(avatar_wrapper)
        top_row.addLayout(avatar_col)

        title_col = QVBoxLayout(); title_col.setAlignment(Qt.AlignVCenter)
        title_lbl = QLabel("Update Doctor")
        title_lbl.setFont(_semi(18))
        title_lbl.setStyleSheet(f"color: {TEXT_DARK}; background: transparent;")
        title_col.addWidget(title_lbl)
        top_row.addLayout(title_col); top_row.addStretch()
        form_vl.addLayout(top_row)

        # Status message area under image/title
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(_semi(11))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setFixedHeight(24)
        self._status_lbl.setStyleSheet(
            f"color: {RED}; background: transparent; border: none;")
        form_vl.addWidget(self._status_lbl)

        # Row 1: Full Name + Email
        row1 = QHBoxLayout(); row1.setSpacing(16)
        self._name  = self._make_field("Full Name",    "Enter Full Name")
        self._email = self._make_field("Email",        "Enter Email")
        row1.addLayout(self._name[0]); row1.addLayout(self._email[0])
        form_vl.addLayout(row1)

        # Row 2: Phone + Address
        row2 = QHBoxLayout(); row2.setSpacing(16)
        self._phone   = self._make_field("Phone Number", "Enter Phone Number")
        self._address = self._make_field("Address",      "Enter Address")
        row2.addLayout(self._phone[0]); row2.addLayout(self._address[0])
        form_vl.addLayout(row2)

        # Row 3: Role + Gender
        row3 = QHBoxLayout(); row3.setSpacing(16)

        role_col = QVBoxLayout(); role_col.setSpacing(4)
        role_lbl = QLabel("Role"); role_lbl.setFont(_semi(11))
        role_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._role = CustomDropdown(["DOCTOR", "ADMIN"])
        role_col.addWidget(role_lbl); role_col.addWidget(self._role)
        row3.addLayout(role_col)

        gender_col = QVBoxLayout(); gender_col.setSpacing(4)
        gender_lbl = QLabel("Gender"); gender_lbl.setFont(_semi(11))
        gender_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")
        self._gender = CustomDropdown(["Male", "Female"])
        gender_col.addWidget(gender_lbl); gender_col.addWidget(self._gender)
        row3.addLayout(gender_col)

        row3.addStretch()
        form_vl.addLayout(row3)
        card_vl.addWidget(self._form_frame)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.addStretch()

        self._update_btn = QPushButton("Update Doctor")
        self._update_btn.setFixedSize(160, 48)
        self._update_btn.setCursor(Qt.PointingHandCursor)
        self._update_btn.setFont(_semi(13))
        self._update_btn.setStyleSheet(f"""
            QPushButton {{ background: {BLUE}; color: white;
                           border-radius: 10px; border: none; }}
            QPushButton:hover {{ background: #0D3E8A; }}
            QPushButton:disabled {{ background: #8AAFD4; }}
        """)
        self._update_btn.clicked.connect(self._submit)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(120, 48)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(_semi(13))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: {WHITE}; color: {TEXT_DARK};
                           border-radius: 10px; border: 1px solid {CARD_BORDER}; }}
            QPushButton:hover {{ background: #F0F4FF; }}
        """)
        cancel_btn.clicked.connect(self._cancel)

        btn_row.addWidget(self._update_btn)
        btn_row.addSpacing(12)
        btn_row.addWidget(cancel_btn)
        card_vl.addLayout(btn_row)

    # ── helpers ───────────────────────────────────────────────
    def _make_field(self, label: str, placeholder: str):
        col = QVBoxLayout(); col.setSpacing(4)
        lbl = QLabel(label); lbl.setFont(_semi(11))
        lbl.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(44); inp.setFont(_semi(11))
        inp.setStyleSheet(_field_style())
        col.addWidget(lbl); col.addWidget(inp)
        return col, inp

    def _set_avatar_pixmap(self, path: str):
        size = 80
        pix  = QPixmap(path)
        if not pix.isNull():
            is_default = (path == DEFAULT_IMAGE or
                          path.endswith("profile.png") or
                          path.endswith("male_patient.png") or
                          path.endswith("female_patient.png"))
            if is_default:
                # Show default image fully inside the circle background — no crop
                scaled = pix.scaled(size - 16, size - 16, Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation)
                result = QPixmap(size, size); result.fill(Qt.transparent)
                painter = QPainter(result); painter.setRenderHint(QPainter.Antialiasing)
                # Draw circle background
                from PySide6.QtGui import QColor, QBrush
                painter.setBrush(QBrush(QColor("#EEF4FF")))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(0, 0, size, size)
                # Draw icon centered
                x = (size - scaled.width())  // 2
                y = (size - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                self._avatar_lbl.setPixmap(result)
                self._avatar_lbl.setStyleSheet(
                    "border-radius: 40px; background: transparent; border: 2px solid #C8D8F0;")
            else:
                # Real photo — clip to circle
                pix = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                                 Qt.SmoothTransformation)
                if pix.width() > size or pix.height() > size:
                    x = (pix.width()-size)//2; y = (pix.height()-size)//2
                    pix = pix.copy(x, y, size, size)
                result = QPixmap(size, size); result.fill(Qt.transparent)
                painter = QPainter(result); painter.setRenderHint(QPainter.Antialiasing)
                p2 = QPainterPath(); p2.addEllipse(0, 0, size, size)
                painter.setClipPath(p2); painter.drawPixmap(0, 0, pix); painter.end()
                self._avatar_lbl.setPixmap(result)
                self._avatar_lbl.setStyleSheet(
                    "border-radius: 40px; background: transparent; border: none;")
        else:
            self._avatar_lbl.setText("👤")
            self._avatar_lbl.setFont(QFont(CAIRO, 28))

    def _remove_image(self):
        """Remove current image, revert to default, hide remove button."""
        self._selected_image = DEFAULT_IMAGE
        self._current_image  = DEFAULT_IMAGE
        self._set_avatar_pixmap(DEFAULT_IMAGE)
        self._remove_btn.hide()

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._selected_image = path
            self._set_avatar_pixmap(path)
            self._remove_btn.show()

    def _set_error(self, msg: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {RED}; background: transparent; border: none;")
        self._status_lbl.show()
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 2px solid {RED}; }}
        """)

    def _clear_error(self):
        self._status_lbl.clear()
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 1px solid {CARD_BORDER}; }}
        """)

    def _set_loading(self, loading: bool):
        self._update_btn.setEnabled(not loading)
        self._update_btn.setText("  ⏳  Updating..." if loading else "Update Doctor")

    def _cancel(self):
        """Go back directly to Doctor Profile."""
        if self._manager_ref and hasattr(self._manager_ref, 'navigate_to_profile'):
            self._manager_ref.navigate_to_profile(self._user_id)
        else:
            self.go_back_signal.emit()

    # ── populate ──────────────────────────────────────────────
    def load_doctor(self, user_id: int):
        """Load existing doctor data and populate all fields."""
        self._user_id        = user_id
        self._selected_image = None

        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, user_id)
            if not user:
                session.close()
                return

            # Fill fields
            self._name[1].setText(user.username   or "")
            self._email[1].setText(user.email     or "")
            self._phone[1].setText(user.phone_number or "")
            self._address[1].setText(user.address or "")

            # Role dropdown
            role = user.role or "DOCTOR"
            if role in ["DOCTOR", "ADMIN"]:
                self._role.setCurrentIndex(["DOCTOR","ADMIN"].index(role))

            # Gender dropdown
            gender = user.gender or "Male"
            if gender in ["Male", "Female"]:
                self._gender.setCurrentIndex(["Male","Female"].index(gender))

            # Avatar
            self._current_image = user.profile_image or ""
            img = self._current_image
            if img and os.path.exists(img) and img != DEFAULT_IMAGE:
                self._set_avatar_pixmap(img)
                self._remove_btn.show()
            else:
                self._set_avatar_pixmap(DEFAULT_IMAGE)
                self._remove_btn.hide()

            session.close()
        except Exception as e:
            print(f"load_doctor error: {e}")

        self._clear_error()

    # ── submit ────────────────────────────────────────────────
    def _submit(self):
        self._clear_error()

        name    = self._name[1].text().strip()
        email   = self._email[1].text().strip()
        phone   = self._phone[1].text().strip()
        address = self._address[1].text().strip()
        role    = self._role.currentText()
        gender  = self._gender.currentText()

        if not name:  self._set_error("Full Name is required."); return
        if not email: self._set_error("Email is required.");     return

        data = {
            "username":   name,
            "email":      email,
            "phone":      phone,
            "address":    address,
            "role":       role,
            "gender":     gender,
            "image_path": self._selected_image or self._current_image or DEFAULT_IMAGE,
        }

        self._set_loading(True)
        self._thread = QThread()
        self._worker = UpdateDoctorWorker(self._user_id, data)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_finished(self, success: bool, msg: str):
        self._set_loading(False)
        if success:
            # Show success message in the dedicated message area.
            self._form_frame.setStyleSheet(f"""
                QFrame {{ background: #F7FAFF; border-radius: 14px;
                          border: 1px solid {CARD_BORDER}; }}
            """)
            self._status_lbl.setText("✔  Doctor updated successfully!")
            self._status_lbl.setStyleSheet(
                f"color: {GREEN}; background: transparent; border: none;")
            self._status_lbl.show()
            QTimer.singleShot(1000, self._go_to_profile)
        else:
            if msg == "email_exists":
                self._set_error("This email is already registered.")
            elif msg == "name_exists":
                self._set_error("A doctor with this name already exists.")
            elif msg == "not_found":
                self._set_error("Doctor not found.")
            else:
                self._set_error(f"Error: {msg}")

    def _go_to_profile(self):
        """Navigate back to Doctor Profile and reload updated data."""
        if self._manager_ref and hasattr(self._manager_ref, "navigate_to_profile"):
            self._manager_ref.navigate_to_profile(self._user_id)


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class UpdateDoctorScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="", parent=parent)
        self._content = UpdateDoctorContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self.set_content(self._content)

    def load_doctor(self, user_id: int):
        self._content.load_doctor(user_id)

    def _go_back(self):
        """Back button = same as cancel = go to Doctor Profile."""
        uid = self._content._user_id
        if uid and self._manager and hasattr(self._manager, "navigate_to_profile"):
            self._manager.navigate_to_profile(uid)
        elif self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass