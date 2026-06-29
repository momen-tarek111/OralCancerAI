"""
views/doctor_profile.py
────────────────────────
Doctor Profile screen — view doctor info + patients table.
Parent screen: Doctors
"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QPainterPath

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from core.database import SessionLocal
from models.user import ApplicationUser
from models.patient import Patient

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
ORANGE      = "#F2A427"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"
GRAY        = "#9CA3AF"
DEFAULT_ADMIN_USERNAME = "admin"

SCROLLBAR_STYLE = f"""
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: #F1F7FF;
        width: 8px;
        border-radius: 4px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #C8D8F0;
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {BLUE};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
    }}
"""


def _semi(size: int) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(QFont.Weight.DemiBold)
    return f


def _circle_pixmap(path: str, size: int) -> QPixmap:
    pix = QPixmap(path)
    if pix.isNull():
        return QPixmap()
    pix = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                     Qt.SmoothTransformation)
    if pix.width() > size or pix.height() > size:
        x = (pix.width()  - size) // 2
        y = (pix.height() - size) // 2
        pix = pix.copy(x, y, size, size)
    result = QPixmap(size, size)
    result.fill(Qt.transparent)
    p = QPainter(result)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(0, 0, size, size)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, pix)
    p.end()
    return result


def _info_row(label: str, value: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent; border: none;")
    vl = QVBoxLayout(w)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(4)
    lbl = QLabel(label)
    lbl.setFont(_semi(10))
    lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent; border: none;")
    val = QLabel(value or "—")
    val.setFont(_semi(12))
    val.setStyleSheet(f"color: {TEXT_DARK}; background: transparent; border: none;")
    val.setWordWrap(True)
    vl.addWidget(lbl)
    vl.addWidget(val)
    return w


def _badge(text: str, color: str) -> QLabel:
    b = QLabel(f"  {text}  ")
    b.setFont(_semi(9))
    b.setAlignment(Qt.AlignCenter)
    b.setFixedHeight(24)
    b.setStyleSheet(f"""
        background: {color}; color: white;
        border-radius: 12px; border: none; padding: 0 4px;
    """)
    return b


# ─────────────────────────────────────────────────────────────
#  PATIENT ROW
# ─────────────────────────────────────────────────────────────
class PatientRow(QFrame):
    detail_clicked = Signal(int)

    def __init__(self, patient, parent=None):
        super().__init__(parent)
        self._patient_id = getattr(patient, "id", None)
        self.setStyleSheet(f"""
            QFrame {{
                background: {WHITE};
                border: none;
                border-bottom: 1px solid {CARD_BORDER};
            }}
        """)
        self.setFixedHeight(64)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(8)

        av = QLabel()
        av.setFixedSize(38, 38)
        av.setAlignment(Qt.AlignCenter)
        img = (resource_path("assets/female_patient.png")
               if getattr(patient, 'gender', '') == "Female"
               else resource_path("assets/male_patient.png"))
        pix = _circle_pixmap(img, 36)
        if not pix.isNull():
            av.setPixmap(pix)
            av.setStyleSheet("background: transparent; border: none;")
        else:
            av.setText("👤"); av.setFont(QFont(CAIRO, 16))
            av.setStyleSheet("background: transparent; border: none;")
        hl.addWidget(av)

        def cell(text, w=None, align=Qt.AlignLeft | Qt.AlignVCenter,
                 color=TEXT_DARK):
            l = QLabel(str(text) if text else "—")
            l.setFont(_semi(11))
            l.setStyleSheet(
                f"color: {color}; background: transparent; border: none;")
            l.setAlignment(align)
            if w: l.setFixedWidth(w)
            return l

        hl.addWidget(cell(patient.full_name), 2)

        status = getattr(patient, 'status', None) or "Unknown"
        status_color = (RED    if status == "Positive"  else
                        GREEN  if status == "Negative"  else
                        ORANGE if status == "PreCancer" else TEXT_MID)
        badge_w = QWidget()
        badge_w.setStyleSheet("background: transparent;")
        badge_w.setFixedWidth(100)
        bhl = QHBoxLayout(badge_w)
        bhl.setContentsMargins(0, 0, 0, 0)
        bhl.addWidget(_badge(status, status_color))
        bhl.addStretch()
        hl.addWidget(badge_w)

        stage = getattr(patient, 'stage', None) or ""
        hl.addWidget(cell(stage, 90, Qt.AlignCenter))
        hl.addWidget(cell(patient.age or "—", 60, Qt.AlignCenter))
        hl.addWidget(cell(patient.gender or "—", 80, Qt.AlignCenter))

        lv = getattr(patient, 'last_visit', None) or "—"
        hl.addWidget(cell(lv, 110, Qt.AlignCenter))

        arrow_btn = QPushButton("›")
        arrow_btn.setFixedSize(32, 32)
        arrow_btn.setCursor(Qt.PointingHandCursor)
        arrow_btn.setFont(_semi(16))
        arrow_btn.setStyleSheet(f"""
            QPushButton {{ background: #EEF4FF; color: {BLUE};
                           border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: #DDEEFF; }}
        """)
        arrow_btn.clicked.connect(lambda: self.detail_clicked.emit(self._patient_id))
        hl.addWidget(arrow_btn)


# ─────────────────────────────────────────────────────────────
#  ADDED DOCTOR ROW
# ─────────────────────────────────────────────────────────────
class AddedDoctorRow(QFrame):
    block_clicked  = Signal(int, bool)
    detail_clicked = Signal(int)

    def __init__(self, user, is_my_account: bool = False,
                 can_block: bool = True, parent=None):
        super().__init__(parent)
        self._user_id   = user.id
        self._is_blocked = not bool(getattr(user, "is_active", True))
        self.setStyleSheet(f"""
            QFrame {{
                background: {WHITE};
                border: none;
                border-bottom: 1px solid {CARD_BORDER};
            }}
        """)
        self.setFixedHeight(64)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(0)

        av = QLabel()
        av.setFixedSize(38, 38)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("background: transparent; border: none;")
        img_path = user.profile_image or ""
        if img_path and os.path.exists(img_path):
            pix = _circle_pixmap(img_path, 36)
        else:
            fallback = (resource_path("assets/female_patient.png")
                        if getattr(user, 'gender', '') == "Female"
                        else resource_path("assets/male_patient.png"))
            pix = _circle_pixmap(fallback, 36)
        if not pix.isNull():
            av.setPixmap(pix)
        else:
            av.setText("👤")
            av.setFont(QFont(CAIRO, 16))
        hl.addWidget(av)
        hl.addSpacing(12)

        def scell(text, align=Qt.AlignLeft | Qt.AlignVCenter, color=None):
            c = color or (GRAY if self._is_blocked else TEXT_DARK)
            l = QLabel(str(text) if text else "—")
            l.setFont(_semi(11))
            l.setStyleSheet(
                f"color: {c}; background: transparent; border: none;")
            l.setAlignment(align)
            return l

        name_text = user.username or "—"
        if is_my_account:
            name_text = f"{name_text} (My Account)"
        hl.addWidget(scell(name_text), 2)

        role_color = (GRAY if self._is_blocked else
                      BLUE if user.role == "DOCTOR" else GREEN)
        role_cell = QWidget()
        role_cell.setStyleSheet("background: transparent;")
        rc = QHBoxLayout(role_cell)
        rc.setContentsMargins(0, 0, 0, 0)
        rc.setSpacing(0)
        badge = QLabel(f"  {user.role}  ")
        badge.setFont(_semi(10))
        badge.setFixedHeight(26)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"""
            background: {role_color}; color: white;
            border-radius: 13px; border: none; padding: 0 4px;
        """)
        badge.adjustSize()
        rc.addWidget(badge, 0, Qt.AlignVCenter | Qt.AlignLeft)
        rc.addStretch()
        hl.addWidget(role_cell, 1, Qt.AlignCenter)

        hl.addWidget(scell(user.phone_number or "—", Qt.AlignCenter), 2)
        hl.addWidget(scell(user.email        or "—", Qt.AlignCenter), 2)
        hl.addWidget(scell(str(getattr(user, "patient_count", 0)),
                           Qt.AlignCenter), 1)

        if can_block:
            action_btn = QPushButton()
            action_btn.setFixedSize(32, 32)
            action_btn.setCursor(Qt.PointingHandCursor)
            if self._is_blocked:
                unlock_pix = QPixmap(resource_path("assets/unlock.png"))
                if not unlock_pix.isNull():
                    action_btn.setIcon(QIcon(unlock_pix.scaled(
                        18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                else:
                    action_btn.setText("🔓")
                    action_btn.setFont(QFont(CAIRO, 13))
                action_btn.setToolTip("Unblock Doctor")
                action_btn.setStyleSheet(f"""
                    QPushButton {{ background: #F0FFF4; border-radius: 8px;
                                   border: none; color: {GREEN}; }}
                    QPushButton:hover {{ background: #C6F6D5; }}
                """)
                action_btn.clicked.connect(
                    lambda: self.block_clicked.emit(self._user_id, False))
            else:
                action_btn.setText("🚫")
                action_btn.setFont(QFont(CAIRO, 13))
                action_btn.setToolTip("Block Doctor")
                action_btn.setStyleSheet(f"""
                    QPushButton {{ background: #FFF3F3; border-radius: 8px;
                                   border: none; color: {GRAY}; }}
                    QPushButton:hover {{ background: #FFD6D6; }}
                """)
                action_btn.clicked.connect(
                    lambda: self.block_clicked.emit(self._user_id, True))
            hl.addWidget(action_btn)
        else:
            spacer_action = QLabel()
            spacer_action.setFixedSize(32, 32)
            spacer_action.setStyleSheet("background: transparent; border: none;")
            hl.addWidget(spacer_action)
        hl.addSpacing(4)

        arrow_btn = QPushButton("›")
        arrow_btn.setFixedSize(32, 32)
        arrow_btn.setCursor(Qt.PointingHandCursor)
        arrow_btn.setFont(_semi(16))
        arrow_btn.setStyleSheet(f"""
            QPushButton {{ background: #EEF4FF; color: {BLUE};
                           border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: #DDEEFF; }}
        """)
        arrow_btn.clicked.connect(lambda: self.detail_clicked.emit(self._user_id))
        hl.addWidget(arrow_btn)


# ─────────────────────────────────────────────────────────────
#  DOCTOR PROFILE CONTENT
# ─────────────────────────────────────────────────────────────
class DoctorProfileContent(QWidget):
    navigate_back = Signal()

    def __init__(self, mode: str = "doctor", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._mode               = mode   # "doctor" | "my"
        self._user_id            = None
        self._doctor             = None
        self._patient_data       = []
        self._added_doctors_data = []
        self._viewer_user_id     = None
        self._viewer_username    = ""
        self._viewer_role        = ""
        self._build_ui()

    def set_viewer(self, user):
        self._viewer_user_id  = getattr(user, "id", None)
        self._viewer_username = (getattr(user, "username", "") or "")
        self._viewer_role     = (getattr(user, "role",     "") or "")

    # ── build UI ─────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        # Back button
        back_text = "< My Profile" if self._mode == "my" else "< Doctor Profile"
        back_btn  = QPushButton(back_text)
        back_btn.setFont(_semi(13))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{ color: {BLUE}; background: transparent;
                           border: none; text-align: left; padding: 0; }}
            QPushButton:hover {{ color: #0D3E8A; }}
        """)
        back_btn.clicked.connect(self.navigate_back.emit)
        top = QHBoxLayout()
        top.addWidget(back_btn)
        top.addStretch()
        outer.addLayout(top)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLLBAR_STYLE)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_vl = QVBoxLayout(scroll_content)
        scroll_vl.setContentsMargins(0, 0, 8, 0)
        scroll_vl.setSpacing(16)

        # ── Profile card ─────────────────────────────────────
        profile_card = QFrame()
        profile_card.setObjectName("profileCard")
        profile_card.setStyleSheet(f"""
            QFrame#profileCard {{
                background: {WHITE}; border-radius: 18px;
                border: 1px solid {CARD_BORDER};
            }}
            QFrame#profileCard QLabel  {{ border: none; background: transparent; }}
            QFrame#profileCard QWidget {{ border: none; }}
        """)
        pc_vl = QVBoxLayout(profile_card)
        pc_vl.setContentsMargins(28, 24, 28, 24)
        pc_vl.setSpacing(20)

        # Avatar + title header
        header = QHBoxLayout()
        header.setSpacing(24)

        self._avatar_lbl = QLabel()
        self._avatar_lbl.setFixedSize(100, 100)
        self._avatar_lbl.setAlignment(Qt.AlignCenter)
        self._avatar_lbl.setStyleSheet("""
            border-radius: 50px;
            background: #EEF4FF;
            border: 3px solid #C8D8F0;
        """)
        header.addWidget(self._avatar_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(8)
        name_col.setAlignment(Qt.AlignVCenter)

        self._info_title = QLabel(
            "My Profile" if self._mode == "my" else "Doctor Information")
        self._info_title.setFont(_semi(20))
        self._info_title.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")

        self._role_badge = QLabel("—")
        self._role_badge.setFont(_semi(10))
        self._role_badge.setFixedHeight(26)
        self._role_badge.setAlignment(Qt.AlignCenter)
        self._role_badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._status_badge = QLabel("Active")
        self._status_badge.setFont(_semi(10))
        self._status_badge.setFixedHeight(24)
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)
        badges_row.addWidget(self._role_badge)
        badges_row.addWidget(self._status_badge)
        badges_row.addStretch()

        name_col.addWidget(self._info_title)
        name_col.addLayout(badges_row)
        header.addLayout(name_col)
        header.addStretch()
        pc_vl.addLayout(header)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {CARD_BORDER}; border: none;")
        pc_vl.addWidget(div)

        # Info grid
        self._info_grid = QHBoxLayout()
        self._info_grid.setSpacing(32)
        self._left_col  = QVBoxLayout(); self._left_col.setSpacing(16)
        self._right_col = QVBoxLayout(); self._right_col.setSpacing(16)
        self._info_grid.addLayout(self._left_col,  1)
        self._info_grid.addLayout(self._right_col, 1)
        pc_vl.addLayout(self._info_grid)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._update_btn          = None
        self._update_info_btn     = None
        self._change_password_btn = None

        if self._mode == "my":
            # Update My Information button
            self._update_info_btn = QPushButton("Update My Information")
            self._update_info_btn.setFixedHeight(44)
            self._update_info_btn.setCursor(Qt.PointingHandCursor)
            self._update_info_btn.setFont(_semi(12))
            self._update_info_btn.setStyleSheet(f"""
                QPushButton {{ background: {BLUE}; color: white;
                               border-radius: 10px; border: none; padding: 0 18px; }}
                QPushButton:hover {{ background: #0D3E8A; }}
                QPushButton:disabled {{ background: #8AAFD4; }}
            """)
            self._update_info_btn.clicked.connect(self._open_update_my_info)
            btn_row.addWidget(self._update_info_btn)

            btn_row.addSpacing(12)

            # Change Password button
            self._change_password_btn = QPushButton("Change Password")
            self._change_password_btn.setFixedHeight(44)
            self._change_password_btn.setCursor(Qt.PointingHandCursor)
            self._change_password_btn.setFont(_semi(12))
            self._change_password_btn.setStyleSheet(f"""
                QPushButton {{ background: {WHITE}; color: {TEXT_DARK};
                               border-radius: 10px; border: 1px solid {CARD_BORDER};
                               padding: 0 18px; }}
                QPushButton:hover {{ background: #F0F4FF; }}
            """)
            self._change_password_btn.clicked.connect(self._open_change_password)
            btn_row.addWidget(self._change_password_btn)

        else:
            # Update Doctor button (doctor mode only)
            self._update_btn = QPushButton("Update Doctor")
            self._update_btn.setFixedSize(160, 44)
            self._update_btn.setCursor(Qt.PointingHandCursor)
            self._update_btn.setFont(_semi(12))
            self._update_btn.setStyleSheet(f"""
                QPushButton {{ background: {BLUE}; color: white;
                               border-radius: 10px; border: none; }}
                QPushButton:hover {{ background: #0D3E8A; }}
                QPushButton:disabled {{ background: #8AAFD4; }}
            """)
            self._update_btn.clicked.connect(self._open_update)
            btn_row.addWidget(self._update_btn)

        pc_vl.addLayout(btn_row)
        scroll_vl.addWidget(profile_card)

        # ── Patients card ─────────────────────────────────────
        patients_card = QFrame()
        patients_card.setObjectName("patientsCard")
        patients_card.setStyleSheet(f"""
            QFrame#patientsCard {{
                background: {WHITE}; border-radius: 16px;
                border: 1px solid {CARD_BORDER};
            }}
            QFrame#patientsCard QLabel  {{ border: none; background: transparent; }}
            QFrame#patientsCard QWidget {{ border: none; }}
        """)
        pt_vl = QVBoxLayout(patients_card)
        pt_vl.setContentsMargins(16, 16, 16, 16)
        pt_vl.setSpacing(12)

        pt_title_row = QHBoxLayout()
        pt_title = QLabel("Patients Added")
        pt_title.setFont(_semi(14))
        pt_title.setStyleSheet(f"color: {TEXT_DARK};")
        pt_title_row.addWidget(pt_title)
        pt_title_row.addStretch()
        self._pt_count_badge = QLabel("0 patients")
        self._pt_count_badge.setFont(_semi(11))
        self._pt_count_badge.setStyleSheet(f"""
            background: #EEF4FF; color: {BLUE};
            border-radius: 10px; padding: 2px 10px; border: none;
        """)
        pt_title_row.addWidget(self._pt_count_badge)
        pt_vl.addLayout(pt_title_row)

        # Patients table header
        hdr = QFrame()
        hdr.setStyleSheet("background: transparent; border: none;")
        hdr_hl = QHBoxLayout(hdr)
        hdr_hl.setContentsMargins(12, 4, 12, 4)
        hdr_hl.setSpacing(8)
        hdr.setFixedHeight(36)

        def hdr_lbl(text, stretch=0, w=None,
                    align=Qt.AlignLeft | Qt.AlignVCenter):
            l = QLabel(text)
            l.setFont(_semi(10))
            l.setStyleSheet(
                f"color: {TEXT_MID}; background: transparent; border: none;")
            l.setAlignment(align)
            if w: l.setFixedWidth(w)
            return l, stretch

        spacer = QLabel(); spacer.setFixedWidth(38)
        hdr_hl.addWidget(spacer)
        for lbl, s in [
            hdr_lbl("Name",       2),
            hdr_lbl("Status",     0, 100),
            hdr_lbl("Stage",      0, 90,  Qt.AlignCenter),
            hdr_lbl("Age",        0, 60,  Qt.AlignCenter),
            hdr_lbl("Gender",     0, 80,  Qt.AlignCenter),
            hdr_lbl("Last Visit", 0, 110, Qt.AlignCenter),
        ]:
            if s: hdr_hl.addWidget(lbl, s)
            else: hdr_hl.addWidget(lbl)
        spacer2 = QLabel(); spacer2.setFixedWidth(32)
        hdr_hl.addWidget(spacer2)
        pt_vl.addWidget(hdr)

        div2 = QFrame(); div2.setFixedHeight(1)
        div2.setStyleSheet(f"background: {CARD_BORDER};")
        pt_vl.addWidget(div2)

        self._pt_rows_widget = QWidget()
        self._pt_rows_widget.setStyleSheet("background: transparent;")
        self._pt_rows_vl = QVBoxLayout(self._pt_rows_widget)
        self._pt_rows_vl.setContentsMargins(0, 0, 0, 0)
        self._pt_rows_vl.setSpacing(0)
        pt_vl.addWidget(self._pt_rows_widget)
        scroll_vl.addWidget(patients_card)

        # ── Added Doctors card (ADMIN only) ───────────────────
        self._added_doctors_card = QFrame()
        self._added_doctors_card.setObjectName("addedDoctorsCard")
        self._added_doctors_card.setStyleSheet(f"""
            QFrame#addedDoctorsCard {{
                background: {WHITE}; border-radius: 16px;
                border: 1px solid {CARD_BORDER};
            }}
            QFrame#addedDoctorsCard QLabel  {{ border: none; background: transparent; }}
            QFrame#addedDoctorsCard QWidget {{ border: none; }}
        """)
        ad_vl = QVBoxLayout(self._added_doctors_card)
        ad_vl.setContentsMargins(16, 16, 16, 16)
        ad_vl.setSpacing(12)

        ad_title_row = QHBoxLayout()
        ad_title = QLabel("Doctors Added")
        ad_title.setFont(_semi(14))
        ad_title.setStyleSheet(f"color: {TEXT_DARK};")
        ad_title_row.addWidget(ad_title)
        ad_title_row.addStretch()
        self._ad_count_badge = QLabel("0 doctors")
        self._ad_count_badge.setFont(_semi(11))
        self._ad_count_badge.setStyleSheet(f"""
            background: #EEF4FF; color: {BLUE};
            border-radius: 10px; padding: 2px 10px; border: none;
        """)
        ad_title_row.addWidget(self._ad_count_badge)
        ad_vl.addLayout(ad_title_row)

        # Added-doctors table header
        ad_hdr = QFrame()
        ad_hdr.setStyleSheet("background: transparent; border: none;")
        ad_hdr_hl = QHBoxLayout(ad_hdr)
        ad_hdr_hl.setContentsMargins(12, 4, 12, 4)
        ad_hdr_hl.setSpacing(0)
        ad_hdr.setFixedHeight(36)

        def ad_hdr_lbl(text, align=Qt.AlignLeft | Qt.AlignVCenter):
            l = QLabel(text)
            l.setFont(_semi(10))
            l.setStyleSheet(
                f"color: {TEXT_MID}; background: transparent; border: none;")
            l.setAlignment(align)
            return l

        sp = QLabel(); sp.setFixedWidth(50)
        ad_hdr_hl.addWidget(sp)
        ad_hdr_hl.addWidget(ad_hdr_lbl("Name"),                        2)
        ad_hdr_hl.addWidget(ad_hdr_lbl("Role",     Qt.AlignCenter),    1)
        ad_hdr_hl.addWidget(ad_hdr_lbl("Phone",    Qt.AlignCenter),    2)
        ad_hdr_hl.addWidget(ad_hdr_lbl("Email",    Qt.AlignCenter),    2)
        ad_hdr_hl.addWidget(ad_hdr_lbl("Patients", Qt.AlignCenter),    1)
        sp2 = QLabel(); sp2.setFixedWidth(76)
        ad_hdr_hl.addWidget(sp2)
        ad_vl.addWidget(ad_hdr)

        ad_div = QFrame(); ad_div.setFixedHeight(1)
        ad_div.setStyleSheet(f"background: {CARD_BORDER};")
        ad_vl.addWidget(ad_div)

        self._ad_rows_widget = QWidget()
        self._ad_rows_widget.setStyleSheet("background: transparent;")
        self._ad_rows_vl = QVBoxLayout(self._ad_rows_widget)
        self._ad_rows_vl.setContentsMargins(0, 0, 0, 0)
        self._ad_rows_vl.setSpacing(0)
        ad_vl.addWidget(self._ad_rows_widget)

        self._added_doctors_card.hide()
        scroll_vl.addWidget(self._added_doctors_card)
        scroll_vl.addStretch()

        scroll.setWidget(scroll_content)
        outer.addWidget(scroll, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(_semi(11))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"color: {BLUE}; background: transparent; border: none;")
        self._status_lbl.hide()
        outer.addWidget(self._status_lbl)

    # ── load ─────────────────────────────────────────────────
    def load_doctor(self, user_id: int):
        self._user_id = user_id
        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, user_id)
            if not user:
                session.close()
                return

            import types
            self._doctor = types.SimpleNamespace(
                id               = user.id,
                username         = user.username      or "",
                email            = user.email         or "",
                phone_number     = user.phone_number  or "",
                address          = user.address       or "",
                profile_image    = user.profile_image or "",
                role             = user.role          or "",
                gender           = user.gender        or "",
                is_active        = bool(user.is_active)
                                   if user.is_active is not None else True,
                is_default_admin = (user.username == DEFAULT_ADMIN_USERNAME),
            )

            from sqlalchemy import text
            sql = text("""
                SELECT
                    p.id,
                    p.full_name,
                    p.age,
                    p.gender,
                    p.created_at,
                    e.status,
                    e.stage,
                    e.created_at AS exam_date
                FROM patients p
                LEFT JOIN examinations e
                    ON e.id = (
                        SELECT id FROM examinations
                        WHERE patient_id = p.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    )
                WHERE p.added_by = :uid
                ORDER BY p.full_name
            """)
            rows = session.execute(sql, {"uid": user_id}).fetchall()
            
            self._patient_data = []
            for row in rows:
                exam_date = row[7]
                if exam_date:
                    try:
                        dt = (datetime.fromisoformat(exam_date[:19]) if isinstance(exam_date, str) else exam_date)
                        last_visit = dt.strftime("%d %b %Y")
                    except Exception:
                        last_visit = str(exam_date)[:10]
                else:
                    last_visit = "—"
                    
                self._patient_data.append(types.SimpleNamespace(
                    id         = row[0],
                    full_name  = row[1] or "",
                    age        = str(row[2]) if row[2] else "",
                    gender     = row[3] or "",
                    created_at = row[4],
                    status     = row[5] or "Unknown",
                    stage      = row[6] or "",
                    last_visit = last_visit,
                ))

            self._added_doctors_data = []
            if (user.role or "") == "ADMIN":
                doctors_raw = session.query(ApplicationUser).filter_by(
                    added_by=user_id).all()
                for d in doctors_raw:
                    pt_count = session.query(Patient).filter_by(
                        added_by=d.id).count()
                    self._added_doctors_data.append(types.SimpleNamespace(
                        id            = d.id,
                        username      = d.username      or "",
                        email         = d.email         or "",
                        phone_number  = d.phone_number  or "",
                        profile_image = d.profile_image or "",
                        role          = d.role          or "",
                        gender        = d.gender        or "",
                        is_active     = bool(d.is_active)
                                        if d.is_active is not None else True,
                        patient_count = pt_count,
                    ))

            session.close()
        except Exception as e:
            print(f"load_doctor error: {e}")
            return

        self._refresh_ui()

    # ── refresh UI ───────────────────────────────────────────
    def _refresh_ui(self):
        d = self._doctor
        if not d:
            return

        # Avatar
        img = d.profile_image
        if img and os.path.exists(img):
            pix = _circle_pixmap(img, 100)
        else:
            fallback = (resource_path("assets/female_patient.png")
                        if d.gender == "Female" else resource_path("assets/male_patient.png"))
            pix = _circle_pixmap(fallback, 100)
        if not pix.isNull():
            self._avatar_lbl.setPixmap(pix)
            self._avatar_lbl.setStyleSheet(
                "border-radius: 50px; background: transparent; border: none;")
        else:
            self._avatar_lbl.setText("👤")
            self._avatar_lbl.setFont(QFont(CAIRO, 36))

        # Role badge
        role_color = BLUE if d.role == "DOCTOR" else GREEN
        self._role_badge.setText(f"  {d.role}  ")
        self._role_badge.setStyleSheet(f"""
            background: {role_color}; color: white;
            border-radius: 13px; border: none; padding: 0 12px;
        """)

        # Active / Blocked badge
        if d.is_active:
            self._status_badge.setText("  Active  ")
            self._status_badge.setStyleSheet(f"""
                background: #E8FFF0; color: {GREEN};
                border-radius: 12px; border: none; padding: 0 10px;
            """)
        else:
            self._status_badge.setText("  Blocked  ")
            self._status_badge.setStyleSheet(f"""
                background: #FFF0F0; color: {RED};
                border-radius: 12px; border: none; padding: 0 10px;
            """)

        # Button visibility
        is_def = getattr(d, "is_default_admin", False)
        if self._update_btn:
            # Hide "Update Doctor" when viewing the default admin externally
            self._update_btn.setVisible(not is_def)
        if self._update_info_btn:
            # "Update My Information" is always visible — including default admin
            self._update_info_btn.setVisible(True)
        if self._change_password_btn:
            # "Change Password" is always visible in My Profile
            self._change_password_btn.setVisible(True)

        # Info fields
        cnt = len(self._patient_data)
        self._pt_count_badge.setText(
            f"  {cnt} patient{'s' if cnt != 1 else ''}  ")

        for col in [self._left_col, self._right_col]:
            while col.count():
                item = col.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        for lbl, val in [("Full Name", d.username),
                          ("Email",    d.email),
                          ("Gender",   d.gender or "—")]:
            self._left_col.addWidget(_info_row(lbl, val))
        for lbl, val in [("Phone Number", d.phone_number),
                          ("Address",     d.address),
                          ("Role",        d.role)]:
            self._right_col.addWidget(_info_row(lbl, val))

        # Patient rows
        while self._pt_rows_vl.count():
            item = self._pt_rows_vl.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().setParent(None)

        if not self._patient_data:
            empty = QLabel("No patients added yet.")
            empty.setFont(_semi(11))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color: {TEXT_MID}; background: transparent; padding: 24px;")
            self._pt_rows_vl.addWidget(empty)
        else:
            for p in self._patient_data:
                row = PatientRow(p)
                row.detail_clicked.connect(self._open_patient_details)
                self._pt_rows_vl.addWidget(row)

        # Added-doctors card (ADMIN only)
        is_admin = (d.role == "ADMIN")
        self._added_doctors_card.setVisible(is_admin)
        if is_admin:
            ad_cnt = len(self._added_doctors_data)
            self._ad_count_badge.setText(
                f"  {ad_cnt} doctor{'s' if ad_cnt != 1 else ''}  ")

            while self._ad_rows_vl.count():
                item = self._ad_rows_vl.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().setParent(None)

            if not self._added_doctors_data:
                empty = QLabel("No doctors added yet.")
                empty.setFont(_semi(11))
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet(
                    f"color: {TEXT_MID}; background: transparent; padding: 24px;")
                self._ad_rows_vl.addWidget(empty)
            else:
                for doc in self._added_doctors_data:
                    is_my_account = (self._viewer_user_id == doc.id)
                    can_block     = not is_my_account
                    if (doc.username or "").lower() == DEFAULT_ADMIN_USERNAME:
                        can_block = False
                    row = AddedDoctorRow(
                        doc, is_my_account=is_my_account, can_block=can_block)
                    row.block_clicked.connect(self._toggle_added_doctor_block)
                    row.detail_clicked.connect(self._open_added_doctor_details)
                    self._ad_rows_vl.addWidget(row)

    # ── navigation helpers ────────────────────────────────────
    def _find_manager(self):
        """Walk up the parent chain to find the AppManager."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_manager') and parent._manager:
                return parent._manager
            parent = parent.parent() if hasattr(parent, 'parent') else None
        return None

    def _open_update(self):
        """Navigate to Update Doctor screen (doctor mode, other doctors)."""
        mgr = self._find_manager()
        if mgr and hasattr(mgr, 'navigate_to_update_doctor'):
            mgr.navigate_to_update_doctor(self._user_id)

    def _open_update_my_info(self):
        """Navigate to Update My Profile screen (my mode)."""
        mgr = self._find_manager()
        if mgr and hasattr(mgr, 'navigate_to_update_my_profile'):
            mgr.navigate_to_update_my_profile()

    def _open_change_password(self):
        """Navigate to Change My Password screen (my mode)."""
        mgr = self._find_manager()
        if mgr and hasattr(mgr, 'navigate_to_change_my_password'):
            mgr.navigate_to_change_my_password()

    def _open_patient_details(self, patient_id: int):
        mgr = self._find_manager()
        if mgr and hasattr(mgr, 'navigate_to_patient_details'):
            mgr.navigate_to_patient_details(patient_id)

    def _open_added_doctor_details(self, user_id: int):
        """From admin profile — clicking own row opens My Profile,
        clicking any other doctor navigates to DoctorProfileScreen
        so title/back text are correct."""
        mgr = self._find_manager()
        # Own account row → My Profile
        if self._viewer_user_id and user_id == self._viewer_user_id:
            if mgr and hasattr(mgr, 'navigate_to_my_profile'):
                mgr.navigate_to_my_profile()
            return
        # Another doctor → navigate to DoctorProfileScreen properly
        if mgr and hasattr(mgr, 'navigate_to_profile'):
            mgr.navigate_to_profile(user_id)
            return
        # Fallback (no manager): reload in-place — only hits if standalone
        self.load_doctor(user_id)

    def _toggle_added_doctor_block(self, user_id: int, should_block: bool):
        """Block / unblock a doctor from the admin's added-doctors section."""
        if self._viewer_user_id and user_id == self._viewer_user_id:
            return
        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, user_id)
            if user:
                user.is_active = not should_block
                session.commit()
            session.close()
        except Exception as e:
            print(f"_toggle_added_doctor_block error: {e}")
            return
        if self._user_id:
            self.load_doctor(self._user_id)


# ─────────────────────────────────────────────────────────────
#  DOCTOR PROFILE SCREEN
# ─────────────────────────────────────────────────────────────
class DoctorProfileScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="", parent=parent)
        self._content = DoctorProfileContent()
        self._content.navigate_back.connect(self._go_back)
        self.set_content(self._content)

    def load_doctor(self, user_id: int):
        self._content.load_doctor(user_id)

    def set_user(self, user):
        super().set_user(user)
        self._content.set_viewer(user)

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back_from_profile"):
            self._manager.go_back_from_profile()
        elif self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def on_nav(self, label: str):
        pass