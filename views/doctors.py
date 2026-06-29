"""
views/doctors.py
─────────────────
Doctors list screen. Admin only. Extends MainLayout.
"""

import math
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QLineEdit, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QIcon

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from core.database import SessionLocal
from models.user import ApplicationUser
from models.patient import Patient

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
GRAY        = "#9CA3AF"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"
PAGE_SIZE   = 6
DEFAULT_ADMIN_USERNAME = "admin"


def _semi(size: int) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(QFont.Weight.DemiBold)
    return f


def _circle_pixmap(path: str, size: int = 36) -> QPixmap:
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


# ─────────────────────────────────────────────────────────────
#  BLOCK / UNBLOCK WORKER
# ─────────────────────────────────────────────────────────────
class ToggleBlockWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, user_id: int, block: bool):
        super().__init__()
        self._id    = user_id
        self._block = block

    def run(self):
        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, self._id)
            if user:
                user.is_active = not self._block
                session.commit()
            session.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
#  DELETE WORKER
# ─────────────────────────────────────────────────────────────
class DeleteDoctorWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, user_id: int):
        super().__init__()
        self._id = user_id

    def run(self):
        try:
            session = SessionLocal()
            user = session.get(ApplicationUser, self._id)
            if user:
                session.delete(user)
                session.commit()
            session.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
#  DOCTOR ROW
# ─────────────────────────────────────────────────────────────
class DoctorRow(QFrame):
    block_clicked  = Signal(int, bool)
    delete_clicked = Signal(int)
    detail_clicked = Signal(int)

    def __init__(self, user, patient_count: int,
                 is_blocked: bool = False, can_block: bool = True, parent=None):
        super().__init__(parent)
        self._user_id    = user.id
        self._is_blocked = is_blocked
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

        # Avatar
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
            av.setText("👤"); av.setFont(QFont(CAIRO, 16))
        if is_blocked:
            av.setStyleSheet("background: transparent; border: none; opacity: 0.5;")

        hl.addWidget(av)
        hl.addSpacing(12)

        def scell(text, align=Qt.AlignLeft | Qt.AlignVCenter, color=None):
            c = color or (GRAY if is_blocked else TEXT_DARK)
            l = QLabel(str(text) if text else "—")
            l.setFont(_semi(11))
            l.setStyleSheet(f"color: {c}; background: transparent; border: none;")
            l.setAlignment(align)
            return l

        # Name stretch=2
        hl.addWidget(scell(user.username), 2)

        # Role badge stretch=1
        role_color = (GRAY if is_blocked else
                      BLUE if user.role == "DOCTOR" else GREEN)
        role_cell = QWidget()
        role_cell.setStyleSheet("background: transparent;")
        rc = QHBoxLayout(role_cell)
        rc.setContentsMargins(0, 0, 0, 0); rc.setSpacing(0)
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

        # Phone stretch=2
        hl.addWidget(scell(user.phone_number or "—", Qt.AlignCenter), 2)

        # Email stretch=2
        hl.addWidget(scell(user.email or "—", Qt.AlignCenter), 2)

        # Patients stretch=1
        hl.addWidget(scell(str(patient_count), Qt.AlignCenter), 1)

        # Block / Unblock button
        if can_block:
            action_btn = QPushButton()
            action_btn.setFixedSize(32, 32)
            action_btn.setCursor(Qt.PointingHandCursor)

            if is_blocked:
                unlock_pix = QPixmap(resource_path("assets/unlock.png"))
                if not unlock_pix.isNull():
                    action_btn.setIcon(QIcon(unlock_pix.scaled(
                        18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                else:
                    action_btn.setText("🔓"); action_btn.setFont(QFont(CAIRO, 13))
                action_btn.setToolTip("Unblock Doctor")
                action_btn.setStyleSheet(f"""
                    QPushButton {{ background: #F0FFF4; border-radius: 8px;
                                   border: none; color: {GREEN}; }}
                    QPushButton:hover {{ background: #C6F6D5; }}
                """)
                action_btn.clicked.connect(
                    lambda: self.block_clicked.emit(self._user_id, False))
            else:
                block_pix = QPixmap(resource_path("assets/block.png"))
                if not block_pix.isNull():
                    action_btn.setIcon(QIcon(block_pix.scaled(
                        18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                else:
                    action_btn.setText("🚫"); action_btn.setFont(QFont(CAIRO, 13))
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

        # Arrow → Doctor Profile
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
#  TAB BUTTON
# ─────────────────────────────────────────────────────────────
class TabBtn(QPushButton):
    def __init__(self, text: str, active: bool = False,
                 color: str = None, parent=None):
        super().__init__(text, parent)
        self._color  = color or BLUE
        self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMinimumWidth(90)
        self._refresh()

    def _refresh(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {self._color}; color: white;
                    border-radius: 18px; border: none;
                    font-family: {CAIRO}; font-size: 12px; font-weight: 600;
                    padding: 0 16px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {self._color};
                    border-radius: 18px; border: none;
                    font-family: {CAIRO}; font-size: 12px; font-weight: 600;
                    padding: 0 16px;
                }}
                QPushButton:hover {{ background: #F0F4FF; }}
            """)

    def set_active(self, active: bool):
        self._active = active
        self._refresh()


# ─────────────────────────────────────────────────────────────
#  PAGINATION BAR
# ─────────────────────────────────────────────────────────────
class PaginationBar(QWidget):
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._hl = QHBoxLayout(self)
        self._hl.setContentsMargins(0, 0, 0, 0)
        self._hl.setSpacing(4)

    def update_pages(self, current: int, total: int):
        while self._hl.count():
            item = self._hl.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self._hl.addStretch()

        def nav_btn(text, page, enabled=True):
            b = QPushButton(text); b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
            b.setEnabled(enabled); b.setFont(_semi(11))
            b.setStyleSheet(f"""
                QPushButton {{ background: transparent;
                               color: {BLUE if enabled else TEXT_MID};
                               border: none; border-radius: 6px; }}
                QPushButton:hover:enabled {{ background: #EEF4FF; }}
            """)
            if enabled:
                b.clicked.connect(lambda _, p=page: self.page_changed.emit(p))
            return b

        def page_btn(num):
            b = QPushButton(str(num)); b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor); b.setFont(_semi(11))
            active = (num == current)
            b.setStyleSheet(f"""
                QPushButton {{ background: {BLUE if active else "transparent"};
                               color: {"white" if active else TEXT_DARK};
                               border: {"none" if active else f"1px solid {CARD_BORDER}"};
                               border-radius: 6px; }}
                QPushButton:hover {{ background: {BLUE if active else "#EEF4FF"}; }}
            """)
            if not active:
                b.clicked.connect(lambda _, p=num: self.page_changed.emit(p))
            return b

        self._hl.addWidget(nav_btn("‹", current - 1, current > 1))
        for p in self._get_pages(current, total):
            if p == "...":
                dots = QLabel("..."); dots.setFixedSize(24, 32)
                dots.setAlignment(Qt.AlignCenter)
                dots.setStyleSheet(f"color:{TEXT_MID}; background:transparent;")
                self._hl.addWidget(dots)
            else:
                self._hl.addWidget(page_btn(p))
        self._hl.addWidget(nav_btn("›", current + 1, current < total))

    def _get_pages(self, current, total):
        if total <= 5: return list(range(1, total + 1))
        pages = [1]
        if current > 3: pages.append("...")
        for p in range(max(2, current - 1), min(total, current + 2)):
            pages.append(p)
        if current < total - 2: pages.append("...")
        if total not in pages: pages.append(total)
        return pages


# ─────────────────────────────────────────────────────────────
#  DOCTORS CONTENT
# ─────────────────────────────────────────────────────────────
class DoctorsContent(QWidget):
    navigate_to_add = Signal()
    navigate_back   = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._all_doctors     = []
        self._filtered        = []
        self._current_page    = 1
        self._search_text     = ""
        self._active_tab      = "Active"
        self._thread          = None
        self._worker          = None
        self._current_user_id = None
        self._current_username = ""
        self._current_role = ""
        self._patient_counts  = {}
        self._build_ui()
        self.load_doctors()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        # TOP BAR
        top = QHBoxLayout()
        back_btn = QPushButton("< Doctors")
        back_btn.setFont(_semi(13)); back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{ color: {BLUE}; background: transparent;
                           border: none; text-align: left; padding: 0; }}
            QPushButton:hover {{ color: #0D3E8A; }}
        """)
        back_btn.clicked.connect(self.navigate_back.emit)
        top.addWidget(back_btn)
        top.addStretch()

        add_btn = QPushButton("+ Add Doctor")
        add_btn.setFixedHeight(38); add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFont(_semi(12))
        add_btn.setStyleSheet(f"""
            QPushButton {{ background: {BLUE}; color: white;
                           border-radius: 10px; border: none; padding: 0 16px; }}
            QPushButton:hover {{ background: #0D3E8A; }}
        """)
        add_btn.clicked.connect(self.navigate_to_add.emit)
        top.addWidget(add_btn)
        outer.addLayout(top)

        # WHITE CARD
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background: {WHITE}; border-radius: 16px;
                      border: 1px solid {CARD_BORDER}; }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card, 1)

        card_vl = QVBoxLayout(card)
        card_vl.setContentsMargins(16, 16, 16, 16); card_vl.setSpacing(12)

        # Search
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{ background: {WHITE}; border: 1px solid {CARD_BORDER};
                      border-radius: 12px; }}
        """)
        search_frame.setFixedHeight(44)
        shl = QHBoxLayout(search_frame)
        shl.setContentsMargins(12, 0, 12, 0); shl.setSpacing(8)

        search_icon = QLabel()
        search_icon.setFixedSize(22, 22)
        search_icon.setAlignment(Qt.AlignCenter)
        search_icon.setStyleSheet("background: transparent; border: none;")
        _spix = QPixmap(resource_path("assets/search.png"))
        if not _spix.isNull():
            search_icon.setPixmap(_spix.scaled(20, 20, Qt.KeepAspectRatio,
                                               Qt.SmoothTransformation))
        else:
            search_icon.setText("🔍"); search_icon.setFont(QFont(CAIRO, 13))

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search Doctors..")
        self._search.setFont(_semi(11))
        self._search.setStyleSheet(
            "QLineEdit { border: none; background: transparent; color: #1A1A2E; }")
        self._search.textChanged.connect(self._on_search)
        shl.addWidget(search_icon); shl.addWidget(self._search, 1)
        card_vl.addWidget(search_frame)

        # ── TABS ─────────────────────────────────────────────
        tabs_row = QHBoxLayout(); tabs_row.setSpacing(6)
        self._tab_active  = TabBtn("Active   0",  active=True,  color=BLUE)
        self._tab_blocked = TabBtn("Blocked   0", active=False, color=RED)
        self._tab_active.clicked.connect(lambda: self._set_tab("Active"))
        self._tab_blocked.clicked.connect(lambda: self._set_tab("Blocked"))
        tabs_row.addWidget(self._tab_active)
        self._tab_blocked.hide()
        tabs_row.addWidget(self._tab_blocked)
        tabs_row.addStretch()
        card_vl.addLayout(tabs_row)

        # Table header
        hdr = QFrame()
        hdr.setStyleSheet("background: transparent; border: none;")
        hdr_hl = QHBoxLayout(hdr)
        hdr_hl.setContentsMargins(12, 4, 12, 4)
        hdr_hl.setSpacing(0)
        hdr.setFixedHeight(36)

        def _hs(text, align=Qt.AlignLeft | Qt.AlignVCenter):
            l = QLabel(text); l.setFont(_semi(10))
            l.setStyleSheet(
                f"color: {TEXT_MID}; background: transparent; border: none;")
            l.setAlignment(align)
            return l

        sp = QLabel(); sp.setFixedWidth(50); hdr_hl.addWidget(sp)
        hdr_hl.addWidget(_hs("Name"),                     2)
        hdr_hl.addWidget(_hs("Role",     Qt.AlignCenter), 1)
        hdr_hl.addWidget(_hs("Phone",    Qt.AlignCenter), 2)
        hdr_hl.addWidget(_hs("Email",    Qt.AlignCenter), 2)
        hdr_hl.addWidget(_hs("Patients", Qt.AlignCenter), 1)
        sp2 = QLabel(); sp2.setFixedWidth(76); hdr_hl.addWidget(sp2)
        card_vl.addWidget(hdr)

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet(f"background: {CARD_BORDER};")
        card_vl.addWidget(div)

        # Rows area
        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet("background: transparent;")
        self._rows_vl = QVBoxLayout(self._rows_widget)
        self._rows_vl.setContentsMargins(0, 0, 0, 0)
        self._rows_vl.setSpacing(0)
        card_vl.addWidget(self._rows_widget, 1)

        # Bottom
        bottom = QHBoxLayout()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(_semi(10))
        self._count_lbl.setStyleSheet(
            f"color: {TEXT_MID}; background: transparent;")
        bottom.addWidget(self._count_lbl); bottom.addStretch()
        self._pagination = PaginationBar()
        self._pagination.page_changed.connect(self._go_to_page)
        bottom.addWidget(self._pagination)
        card_vl.addLayout(bottom)

    def _set_tab(self, tab: str):
        self._active_tab = tab
        self._tab_active.set_active(tab == "Active")
        self._tab_blocked.set_active(tab == "Blocked")
        self._current_page = 1
        self._apply_filters()

    def set_current_user(self, user_id: int, username: str = "", role: str = ""):
        self._current_user_id = user_id
        self._current_username = username or ""
        self._current_role = role or ""
        self.load_doctors()

    # ── data ─────────────────────────────────────────────────
    def load_doctors(self):
        try:
            session = SessionLocal()
            q = session.query(ApplicationUser)
            if self._current_user_id:
                q = q.filter(ApplicationUser.id != self._current_user_id)
            raw_doctors = q.all()

            import types
            doctors = []
            for d in raw_doctors:
                obj = types.SimpleNamespace(
                    id                   = d.id,
                    username             = d.username,
                    email                = d.email,
                    phone_number         = d.phone_number or "",
                    address              = d.address or "",
                    profile_image        = d.profile_image or "",
                    role                 = d.role or "",
                    gender               = d.gender or "",
                    is_active            = bool(d.is_active) if d.is_active is not None else True,
                    must_change_password = bool(d.must_change_password),
                )
                doctors.append(obj)

            patient_counts = {}
            try:
                import sqlalchemy
                rows = session.query(
                    Patient.added_by,
                    sqlalchemy.func.count(Patient.id)
                ).group_by(Patient.added_by).all()
                for uid, cnt in rows:
                    if uid: patient_counts[uid] = cnt
            except Exception:
                pass

            session.close()
            self._all_doctors    = doctors
            self._patient_counts = patient_counts
        except Exception as e:
            print(f"load_doctors error: {e}")
            self._all_doctors    = []
            self._patient_counts = {}
        self._apply_filters()

    def _apply_filters(self):
        active_all  = [d for d in self._all_doctors if d.is_active]
        blocked_all = [d for d in self._all_doctors if not d.is_active]

        self._tab_active.setText(f"Active   {len(active_all)}")
        self._tab_blocked.setText(f"Blocked   {len(blocked_all)}")

        if len(blocked_all) > 0:
            self._tab_blocked.show()
        else:
            self._tab_blocked.hide()
            if self._active_tab == "Blocked":
                self._active_tab = "Active"
                self._tab_active.set_active(True)
                self._tab_blocked.set_active(False)

        base = active_all if self._active_tab == "Active" else blocked_all

        if self._search_text:
            q = self._search_text.lower()
            base = [d for d in base
                    if q in (d.username or "").lower()
                    or q in (d.email or "").lower()]

        self._filtered = base
        self._render_page()

    def _render_page(self):
        while self._rows_vl.count():
            item = self._rows_vl.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().setParent(None)

        total     = len(self._filtered)
        pages     = max(1, math.ceil(total / PAGE_SIZE))
        start     = (self._current_page - 1) * PAGE_SIZE
        end       = min(start + PAGE_SIZE, total)
        page_docs = self._filtered[start:end]

        is_blocked_tab = (self._active_tab == "Blocked")

        if not page_docs:
            msg = ("No blocked doctors." if is_blocked_tab
                   else "No active doctors found.")
            empty = QLabel(msg)
            empty.setFont(_semi(12)); empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
            self._rows_vl.addWidget(empty)
        else:
            for doc in page_docs:
                cnt = self._patient_counts.get(doc.id, 0)
                can_block = True
                # Hide block only for the default admin account row.
                if (getattr(doc, "username", "") or "").lower() == DEFAULT_ADMIN_USERNAME:
                    can_block = False
                row = DoctorRow(doc, cnt, is_blocked=is_blocked_tab, can_block=can_block)
                row.block_clicked.connect(self._handle_block)
                row.detail_clicked.connect(self._open_profile)
                self._rows_vl.addWidget(row)
        self._rows_vl.addStretch()

        self._count_lbl.setText(
            f"showing {start+1} to {end} of {total} doctor{'s' if total!=1 else ''}"
            if total else "")
        self._pagination.update_pages(self._current_page, pages)

    def _handle_block(self, user_id: int, should_block: bool):
        self._run_block(user_id, should_block)

    def _run_block(self, user_id: int, should_block: bool):
        from PySide6.QtCore import QThread
        self._thread = QThread()
        self._worker = ToggleBlockWorker(user_id, should_block)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(
            lambda sb=should_block: self._on_block_done(sb))
        self._thread.start()

    def _on_block_done(self, was_blocking: bool):
        if not was_blocking:
            self._active_tab = "Active"
            self._tab_active.set_active(True)
            self._tab_blocked.set_active(False)
        self.load_doctors()

    def _open_profile(self, user_id: int):
        """Navigate to Doctor Profile screen."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_manager') and parent._manager:
                mgr = parent._manager
                if hasattr(mgr, 'navigate_to_profile'):
                    mgr.navigate_to_profile(user_id)
                    return
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _on_search(self, text: str):
        self._search_text = text
        self._current_page = 1
        self._apply_filters()

    def _go_to_page(self, page: int):
        self._current_page = page
        self._render_page()

    def refresh(self):
        # Reset to Active tab on every refresh (navigation entry)
        self._active_tab = "Active"
        self._tab_active.set_active(True)
        self._tab_blocked.set_active(False)
        self.load_doctors()


# ─────────────────────────────────────────────────────────────
#  DOCTORS SCREEN
# ─────────────────────────────────────────────────────────────
class DoctorsScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Doctors", parent=parent)
        self._content = DoctorsContent()
        self._content.navigate_to_add.connect(self._go_to_add_doctor)
        self._content.navigate_back.connect(self._go_back)
        self.set_content(self._content)

    def set_user(self, user):
        super().set_user(user)
        self._content.set_current_user(user.id, user.username or "", user.role or "")

    def _go_to_add_doctor(self):
        if self._manager and hasattr(self._manager, "navigate_to"):
            self._manager.navigate_to("Add Doctor")

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def navigate_to_profile(self, user_id: int):
        """Called by DoctorsContent to open the profile screen."""
        if self._manager and hasattr(self._manager, "navigate_to_profile"):
            self._manager.navigate_to_profile(user_id)

    def refresh(self):
        self._content.refresh()

    def on_nav(self, label: str):
        pass