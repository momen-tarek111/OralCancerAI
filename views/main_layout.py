"""
main_layout.py  —  Sidebar + Navbar + Content shell
"""

import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import (
    QFont, QPixmap, QIcon, QPainter, QColor, QPainterPath, QBrush, QPen,
)

from core.utils import resource_path

BLUE          = "#104EA5"
BG_MAIN       = "#F1F7FF"
WHITE         = "#FFFFFF"
ACTIVE_TEXT   = "#104EA5"
INACTIVE_TEXT = "#FFFFFF"
CAIRO         = "Cairo"

LOGO_TEXT_X = 20
LOGO_TEXT_Y = 120

NAV_ITEMS = [
    ("Dashboard",   resource_path("assets/icons8-dashboard-100.png"), resource_path("assets/icons8-dashboard-100 (1).png")),
    ("Patients",    resource_path("assets/icons8-patients-100 (3).png"), resource_path("assets/icons8-patients-100 (4).png")),
    ("Doctors",     resource_path("assets/icons8-doctor-100.png"), resource_path("assets/icons8-doctor-100 (1).png")),
    ("Add Patient", resource_path("assets/icons8-add-user-male-100.png"), resource_path("assets/icons8-add-user-male-100 (1).png")),
    ("Add Doctor",  resource_path("assets/icons8-add-administrator-100.png"), resource_path("assets/icons8-add-administrator-100 (1).png")),
    ("Quick Check", resource_path("assets/quick_check_white.png"), resource_path("assets/quick_check_active.png")),
]


# ─────────────────────────────────────────────────────────────
#  NAV BUTTON
# ─────────────────────────────────────────────────────────────
class NavButton(QPushButton):
    def __init__(self, label: str, icon_path: str, active_icon_path: str, parent=None):
        super().__init__(parent)
        self.setText(f"    {label}")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(52)
        self.setIconSize(QSize(24, 24))
        self._active = False

        f = QFont(CAIRO, 13)
        f.setWeight(QFont.Weight.DemiBold)
        self.setFont(f)

        self._icon_pixmap        = QPixmap(icon_path)
        self._active_icon_pixmap = QPixmap(active_icon_path)
        self._update_style()

    def _update_style(self):
        c  = ACTIVE_TEXT if self._active else INACTIVE_TEXT
        bg = "transparent"
        if self._active:
            bg = BG_MAIN
        elif self.underMouse():
            bg = "rgba(255, 255, 255, 0.15)"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 12px;
                color: {c};
                text-align: left;
                padding-left: 16px;
            }}
        """)
        pix = self._active_icon_pixmap if self._active else self._icon_pixmap
        if not pix.isNull():
            self.setIcon(QIcon(pix.scaled(24, 24, Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation)))

    def set_active(self, active: bool):
        self._active = active
        self.blockSignals(True)
        self.setChecked(active)
        self.blockSignals(False)
        self._update_style()
        if self.parent():
            self.parent().update()

    def enterEvent(self, e):
        self._update_style()
        if self.parent(): self.parent().update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._update_style()
        if self.parent(): self.parent().update()
        super().leaveEvent(e)


# ─────────────────────────────────────────────────────────────
#  LOGO WIDGET
# ─────────────────────────────────────────────────────────────
class LogoWidget(QWidget):
    W, H = 195, 165

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setStyleSheet("background: transparent;")

        img = QLabel(self)
        img.setGeometry(0, 0, self.W, self.H)
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("background: transparent;")
        pix = QPixmap(resource_path("assets/logo_white.png"))
        if not pix.isNull():
            img.setPixmap(pix.scaled(self.W, self.H,
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            img.setText("🫁")
            img.setFont(QFont(CAIRO, 36))
            img.setStyleSheet("color:white; background:transparent;")

        txt = QLabel("HIDDEN TRUTH\nOF CELLS", self)
        txt.setAlignment(Qt.AlignCenter)
        tf = QFont(CAIRO, 7)
        tf.setWeight(QFont.Weight.DemiBold)
        tf.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        txt.setFont(tf)
        txt.setStyleSheet("color:white; background:transparent;")
        txt.adjustSize()
        txt.move(LOGO_TEXT_X, LOGO_TEXT_Y)
        txt.setFixedWidth(self.W)


# ─────────────────────────────────────────────────────────────
#  AVATAR LABEL  — draws a white ring when active
# ─────────────────────────────────────────────────────────────
class AvatarLabel(QLabel):
    """
    A circular avatar that can show a white ring to indicate
    the user is currently on the My Profile screen.
    """
    RING_W  = 2      # ring stroke width
    RING_GAP = 2     # gap between image edge and ring

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False

    def set_profile_active(self, active: bool):
        self._active = active
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(WHITE))
        pen.setWidth(self.RING_W)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        m = self.RING_W + self.RING_GAP
        p.drawEllipse(m // 2, m // 2,
                      self.width()  - m,
                      self.height() - m)
        p.end()


# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
class Sidebar(QFrame):
    nav_clicked = Signal(str)

    def __init__(self, active_page: str = "Dashboard", parent=None):
        super().__init__(parent)
        self.setFixedWidth(215)
        self.setStyleSheet("border: none;")
        self._active_label: str = active_page

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 20, 12, 20)
        root.setSpacing(0)

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.addStretch()
        logo_row.addWidget(LogoWidget())
        logo_row.addStretch()
        root.addLayout(logo_row)
        root.addSpacing(16)

        d = QFrame(); d.setFixedHeight(1)
        d.setStyleSheet("background:rgba(255,255,255,0.30);")
        root.addWidget(d)
        root.addSpacing(10)

        self._buttons: dict[str, NavButton] = {}
        for label, icon_path, active_icon_path in NAV_ITEMS:
            btn = NavButton(label, icon_path, active_icon_path, self)
            btn.clicked.connect(lambda _, l=label: self._on_nav(l))
            self._buttons[label] = btn
            root.addWidget(btn)
            root.addSpacing(2)

        if active_page in self._buttons:
            self._buttons[active_page].set_active(True)

        root.addStretch()

        d2 = QFrame(); d2.setFixedHeight(1)
        d2.setStyleSheet("background:rgba(255,255,255,0.30);")
        root.addWidget(d2)
        root.addSpacing(10)

        lo = QPushButton()
        lo.setCursor(Qt.PointingHandCursor)
        lo.setFixedHeight(52)
        lo.setIconSize(QSize(24, 24))
        lp = QPixmap(resource_path("assets/logout.png"))
        if not lp.isNull():
            lo.setIcon(QIcon(lp.scaled(24, 24, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)))
            lo.setText("    Log Out")
        else:
            lo.setText("➜   Log Out")
        lf = QFont(CAIRO, 13); lf.setWeight(QFont.Weight.DemiBold)
        lo.setFont(lf)
        lo.setStyleSheet("""
            QPushButton {
                background:transparent; color:#E74C3C;
                border:none; text-align:left; padding-left:16px;
                border-radius: 10px;
            }
            QPushButton:hover { background:rgba(231,76,60,0.15); }
        """)
        lo.clicked.connect(lambda: self.nav_clicked.emit("__logout__"))
        root.addWidget(lo)

    def _on_nav(self, label: str):
        self._active_label = label
        for name, btn in self._buttons.items():
            btn.blockSignals(True)
            btn.set_active(name == label)
            btn.blockSignals(False)
        self.nav_clicked.emit(label)
        self.update()

    def set_active(self, label: str):
        """Set active item without emitting nav_clicked.
        Pass empty string to deactivate all items."""
        self._active_label = label
        for name, btn in self._buttons.items():
            btn.blockSignals(True)
            btn.set_active(name == label and label != "")
            btn.blockSignals(False)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W  = float(self.width())
        H  = float(self.height())
        CR = 20.0
        path = QPainterPath()
        path.moveTo(CR, 0)
        path.lineTo(W, 0)
        path.lineTo(W, H)
        path.lineTo(CR, H)
        path.arcTo(QRectF(0, H - CR*2, CR*2, CR*2), 270, -90)
        path.lineTo(0, CR)
        path.arcTo(QRectF(0, 0, CR*2, CR*2), 180, -90)
        path.closeSubpath()
        p.fillPath(path, QBrush(QColor(BLUE)))
        p.end()


# ─────────────────────────────────────────────────────────────
#  NAVBAR
# ─────────────────────────────────────────────────────────────
class Navbar(QFrame):
    def __init__(self, doctor_name: str = "Dr.Amira", parent=None):
        super().__init__(parent)
        self.setFixedHeight(62)
        self.setStyleSheet("border: none; background: transparent;")
        self._doctor_name = doctor_name

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W  = float(self.width())
        H  = float(self.height())
        CR = 20.0
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(W - CR, 0)
        path.arcTo(QRectF(W - CR*2, 0, CR*2, CR*2), 90, -90)
        path.lineTo(W, H)
        path.lineTo(0, H)
        path.closeSubpath()
        p.fillPath(path, QBrush(QColor(BLUE)))
        p.end()
        super().paintEvent(event)

    def _set_avatar(self, path: str):
        size = 38
        pix  = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                             Qt.SmoothTransformation)
            if pix.width() > size or pix.height() > size:
                x = (pix.width()  - size) // 2
                y = (pix.height() - size) // 2
                pix = pix.copy(x, y, size, size)
            result = QPixmap(size, size)
            result.fill(Qt.transparent)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.Antialiasing)
            clip = QPainterPath()
            clip.addEllipse(0, 0, size, size)
            painter.setClipPath(clip)
            painter.drawPixmap(0, 0, pix)
            painter.end()
            self._avatar.setPixmap(result)
            self._avatar.setStyleSheet("background:transparent; border:none;")
        else:
            self._avatar.setText("👤")
            self._avatar.setFont(QFont(CAIRO, 20))
            self._avatar.setStyleSheet(
                "background:rgba(255,255,255,0.20); border-radius:20px; color:white;")

    def set_doctor_name(self, name: str):
        self._welcome.setText(f"Welcome ,  {name}")

    def set_avatar_active(self, active: bool):
        """Show / hide the white profile-active ring on the avatar."""
        self._avatar.set_profile_active(active)


# ─────────────────────────────────────────────────────────────
#  MAIN LAYOUT
# ─────────────────────────────────────────────────────────────
class MainLayout(QWidget):
    def __init__(self, manager=None, active_page: str = "Dashboard",
                 doctor_name: str = "Dr.Amira", parent=None):
        super().__init__(parent)
        self._manager     = manager
        self._active_page = active_page

        self.setStyleSheet("background-color: #1a1a2e;")

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(0)

        inner = QWidget()
        inner.setStyleSheet(
            "QWidget { background-color: transparent; border-radius: 20px; }")
        outer_layout.addWidget(inner)

        main_h = QHBoxLayout(inner)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        self.sidebar = Sidebar(active_page)
        self.sidebar.nav_clicked.connect(self._handle_nav)
        main_h.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.navbar = Navbar(doctor_name)
        nav_lay = QHBoxLayout(self.navbar)
        nav_lay.setContentsMargins(24, 0, 20, 0)

        self.navbar._welcome = QLabel(f"Welcome ,  {doctor_name}")
        wf = QFont(CAIRO, 15); wf.setWeight(QFont.Weight.DemiBold)
        self.navbar._welcome.setFont(wf)
        self.navbar._welcome.setStyleSheet(
            "color:white; background:transparent;")
        nav_lay.addWidget(self.navbar._welcome)
        nav_lay.addStretch()

        # ── Avatar — now AvatarLabel so it can show the active ring ──
        self.navbar._avatar = AvatarLabel()
        self.navbar._avatar.setFixedSize(40, 40)
        self.navbar._avatar.setAlignment(Qt.AlignCenter)
        self.navbar._set_avatar(resource_path("assets/profile.png"))
        self.navbar._avatar.setCursor(Qt.PointingHandCursor)
        self.navbar._avatar.mousePressEvent = self._on_avatar_clicked
        nav_lay.addWidget(self.navbar._avatar)

        right.addWidget(self.navbar)

        self._cf = QFrame()
        self._cf.setStyleSheet(f"""
            QFrame {{
                background: {BG_MAIN};
                border-bottom-right-radius: 20px;
                border: none;
            }}
        """)
        self._cl = QVBoxLayout(self._cf)
        self._cl.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self._cf, 1)

        main_h.addLayout(right, 1)

    def set_content(self, widget: QWidget):
        while self._cl.count():
            item = self._cl.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._cl.addWidget(widget)

    def set_doctor_name(self, name: str):
        self.navbar.set_doctor_name(name)

    def set_avatar_active(self, active: bool):
        """Highlight / un-highlight the navbar avatar."""
        self.navbar.set_avatar_active(active)

    def set_user(self, user):
        img_path = user.profile_image if user.profile_image else ""
        if not img_path or not os.path.exists(img_path):
            img_path = resource_path("assets/profile.png")
        self.navbar._set_avatar(img_path)

        is_doctor  = (user.role == "DOCTOR")
        admin_only = {"Add Doctor", "Doctors"}
        for name, btn in self.sidebar._buttons.items():
            if name in admin_only:
                btn.setVisible(not is_doctor)
            else:
                btn.setVisible(True)
        self.sidebar.update()

    def _handle_nav(self, label: str):
        if label == "__logout__" and self._manager:
            if hasattr(self._manager, "reset_all_sidebars"):
                self._manager.reset_all_sidebars()
            self._manager.setCurrentWidget(self._manager.login)
            return
        if self._manager and hasattr(self._manager, "navigate_to"):
            self._manager.navigate_to(label)
            return
        self.on_nav(label)

    def _on_avatar_clicked(self, _event):
        if self._manager and hasattr(self._manager, "navigate_to_my_profile"):
            self._manager.navigate_to_my_profile()

    def on_nav(self, label: str):
        pass