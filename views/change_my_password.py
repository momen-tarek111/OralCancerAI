"""
views/change_my_password.py
────────────────────────────
Change My Password screen — accessible from My Profile.
Design mirrors update_doctor.py / update_my_profile.py.
Parent screen: My Profile
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QPixmap

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from core.database import SessionLocal
from core.security import hash_password, verify_password
from models.user import ApplicationUser

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"


def _semi(size: int, weight=QFont.Weight.DemiBold) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(weight)
    return f


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
class ChangeMyPasswordWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, user_id: int, current_pw: str, new_pw: str):
        super().__init__()
        self._user_id    = user_id
        self._current_pw = current_pw
        self._new_pw     = new_pw

    def run(self):
        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, self._user_id)
            if not user:
                session.close()
                self.finished.emit(False, "not_found")
                return

            if not verify_password(self._current_pw, user.password_hashed):
                session.close()
                self.finished.emit(False, "wrong_current")
                return

            if verify_password(self._new_pw, user.password_hashed):
                session.close()
                self.finished.emit(False, "same_password")
                return

            user.password_hashed      = hash_password(self._new_pw)
            user.must_change_password = False
            session.commit()
            session.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────
class ChangeMyPasswordContent(QWidget):
    go_back_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._user_id     = None
        self._manager_ref = None
        self._thread      = None
        self._worker      = None
        self._build_ui()

    def set_manager(self, manager):
        self._manager_ref = manager

    def set_user(self, user):
        self._user_id = getattr(user, "id", None)
        self._clear_all()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(16)

        # Back button
        back_btn = QPushButton("< Change Password")
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
        back_row.addWidget(back_btn)
        back_row.addStretch()
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

        # Form frame
        self._form_frame = QFrame()
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 1px solid {CARD_BORDER}; }}
        """)
        form_vl = QVBoxLayout(self._form_frame)
        form_vl.setContentsMargins(24, 20, 24, 20)
        form_vl.setSpacing(14)

        # ── Header row: lock icon + title ─────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # Lock icon column
        icon_col = QVBoxLayout()
        icon_col.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        icon_wrapper = QWidget()
        icon_wrapper.setFixedSize(90, 90)
        icon_wrapper.setStyleSheet("background: transparent;")

        icon_lbl = QLabel(icon_wrapper)
        icon_lbl.setFixedSize(80, 80)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "border-radius: 40px; background: #EEF4FF; border: 2px solid #C8D8F0;")
        icon_lbl.move(0, 0)

        lock_pix = QPixmap(resource_path("assets/password.png"))
        if not lock_pix.isNull():
            scaled = lock_pix.scaled(
                44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Draw icon centered inside the circle background
            from PySide6.QtGui import QPainter, QColor, QBrush, QPainterPath
            size   = 80
            result = QPixmap(size, size)
            result.fill(Qt.transparent)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#EEF4FF")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, size, size)
            x = (size - scaled.width())  // 2
            y = (size - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            icon_lbl.setPixmap(result)
            icon_lbl.setStyleSheet(
                "border-radius: 40px; background: transparent;"
                " border: 2px solid #C8D8F0;")
        else:
            icon_lbl.setText("🔒")
            icon_lbl.setFont(QFont(CAIRO, 28))

        icon_col.addWidget(icon_wrapper)
        top_row.addLayout(icon_col)

        # Title column
        title_col = QVBoxLayout()
        title_col.setAlignment(Qt.AlignVCenter)
        title_lbl = QLabel("Change Password")
        title_lbl.setFont(_semi(18))
        title_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")
        title_col.addWidget(title_lbl)
        top_row.addLayout(title_col)
        top_row.addStretch()
        form_vl.addLayout(top_row)

        # Status message
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(_semi(11))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setFixedHeight(24)
        self._status_lbl.setStyleSheet(
            f"color: {RED}; background: transparent; border: none;")
        form_vl.addWidget(self._status_lbl)

        # ── Fields — stacked vertically (single-column, centred) ──
        # Row 1: Current Password (full width)
        self._current_pw = self._make_field(
            "Current Password", "Enter your current password")
        form_vl.addLayout(self._current_pw[0])

        # Row 2: New Password + Confirm New Password side by side
        row2 = QHBoxLayout()
        row2.setSpacing(16)
        self._new_pw     = self._make_field(
            "New Password", "Enter new password")
        self._confirm_pw = self._make_field(
            "Confirm New Password", "Re-enter new password")
        row2.addLayout(self._new_pw[0])
        row2.addLayout(self._confirm_pw[0])
        form_vl.addLayout(row2)

        card_vl.addWidget(self._form_frame)

        # ── Buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._change_btn = QPushButton("Change Password")
        self._change_btn.setFixedSize(180, 48)
        self._change_btn.setCursor(Qt.PointingHandCursor)
        self._change_btn.setFont(_semi(13))
        self._change_btn.setStyleSheet(f"""
            QPushButton {{ background: {BLUE}; color: white;
                           border-radius: 10px; border: none; }}
            QPushButton:hover {{ background: #0D3E8A; }}
            QPushButton:disabled {{ background: #8AAFD4; }}
        """)
        self._change_btn.clicked.connect(self._submit)

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

        btn_row.addWidget(self._change_btn)
        btn_row.addSpacing(12)
        btn_row.addWidget(cancel_btn)
        card_vl.addLayout(btn_row)

    # ── helpers ───────────────────────────────────────────────
    def _make_field(self, label: str, placeholder: str):
        col = QVBoxLayout()
        col.setSpacing(4)
        lbl = QLabel(label)
        lbl.setFont(_semi(11))
        lbl.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(44)
        inp.setFont(_semi(11))
        inp.setEchoMode(QLineEdit.Password)
        inp.setStyleSheet(_field_style())
        col.addWidget(lbl)
        col.addWidget(inp)
        return col, inp

    def _set_error(self, msg: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {RED}; background: transparent; border: none;")
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 2px solid {RED}; }}
        """)

    def _set_success(self, msg: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {GREEN}; background: transparent; border: none;")
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 1px solid {CARD_BORDER}; }}
        """)

    def _clear_all(self):
        if not hasattr(self, "_current_pw"):
            return
        for _, inp in [self._current_pw, self._new_pw, self._confirm_pw]:
            inp.clear()
        self._status_lbl.clear()
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 1px solid {CARD_BORDER}; }}
        """)

    def _set_loading(self, loading: bool):
        self._change_btn.setEnabled(not loading)
        self._change_btn.setText(
            "  ⏳  Updating..." if loading else "Change Password")

    def _cancel(self):
        self._clear_all()
        if self._manager_ref and hasattr(self._manager_ref, "navigate_to_my_profile"):
            self._manager_ref.navigate_to_my_profile()
        else:
            self.go_back_signal.emit()

    # ── submit ────────────────────────────────────────────────
    def _submit(self):
        current = self._current_pw[1].text()
        new     = self._new_pw[1].text().strip()
        confirm = self._confirm_pw[1].text().strip()

        if not current:
            self._set_error("Current password is required.")
            return
        if not new:
            self._set_error("New password is required.")
            return
        if not confirm:
            self._set_error("Please confirm your new password.")
            return
        if new != confirm:
            self._set_error("New password and confirmation do not match.")
            return
        if new == current:
            self._set_error("New password must differ from your current password.")
            return

        self._set_loading(True)
        self._status_lbl.clear()
        self._form_frame.setStyleSheet(f"""
            QFrame {{ background: #F7FAFF; border-radius: 14px;
                      border: 1px solid {CARD_BORDER}; }}
        """)

        self._thread = QThread()
        self._worker = ChangeMyPasswordWorker(self._user_id, current, new)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_finished(self, success: bool, msg: str):
        self._set_loading(False)
        if success:
            self._set_success("✔  Password changed successfully!")
            QTimer.singleShot(1000, self._go_to_profile)
        else:
            if msg == "wrong_current":
                self._set_error("Current password is incorrect.")
            elif msg == "same_password":
                self._set_error("New password must differ from your current password.")
            elif msg == "not_found":
                self._set_error("User account not found.")
            else:
                self._set_error("An internal error occurred.")

    def _go_to_profile(self):
        self._clear_all()
        if self._manager_ref and hasattr(self._manager_ref, "navigate_to_my_profile"):
            self._manager_ref.navigate_to_my_profile()
        else:
            self.go_back_signal.emit()


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class ChangeMyPasswordScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="", parent=parent)
        self._content = ChangeMyPasswordContent()
        self._content.set_manager(manager)
        self._content.go_back_signal.connect(self._go_back)
        self.set_content(self._content)

    def set_user(self, user):
        super().set_user(user)
        self._content.set_user(user)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "navigate_to_my_profile"):
            self._manager.navigate_to_my_profile()
        elif self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass