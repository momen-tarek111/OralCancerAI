"""
views/patients.py
─────────────────
Patients list screen. Extends MainLayout.

Data loaded from:
  - Patient table     → name, age, gender, phone
  - Examination table → status, stage, last_visit (most recent exam)

If a patient has no examinations: status/stage/last_visit = "—"
"""

import math
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QLineEdit, QCalendarWidget,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QMovie

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO
from core.database import SessionLocal

WHITE       = "#FFFFFF"
RED         = "#E74C3C"
GREEN       = "#27AE60"
ORANGE      = "#F2A427"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"
PAGE_SIZE   = 6


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


class FilterBtn(QPushButton):
    def __init__(self, label, count, color, active=False, parent=None):
        super().__init__(parent)
        self._label = label; self._count = count
        self._color = color; self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36); self.setMinimumWidth(80)
        self._refresh()

    def _refresh(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{ background:{BLUE}; color:white;
                    border-radius:18px; padding:0 16px;
                    font-family:{CAIRO}; font-size:12px;
                    font-weight:600; border:none; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{ background:transparent; color:{self._color};
                    border-radius:18px; padding:0 16px;
                    font-family:{CAIRO}; font-size:12px;
                    font-weight:600; border:none; }}
                QPushButton:hover {{ background:#F0F4FF; }}
            """)
        self.setText(f"  {self._label}   {self._count}")

    def set_active(self, a):   self._active = a; self._refresh()
    def update_count(self, c): self._count  = c; self._refresh()


def _badge(text, color):
    b = QLabel(f"  {text}  ")
    b.setFont(_semi(9)); b.setAlignment(Qt.AlignCenter)
    b.setFixedHeight(24)
    b.setStyleSheet(
        f"background:{color}; color:white; border-radius:12px;"
        f"border:none; padding:0 4px;")
    return b


class PatientRow(QFrame):
    detail_clicked = Signal(int)

    def __init__(self, patient, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background:{WHITE}; border:none;"
            f"border-bottom:1px solid {CARD_BORDER}; }}")
        self.setFixedHeight(64)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(0)

        av = QLabel()
        av.setFixedSize(38, 38); av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("background:transparent; border:none;")
        img_path = (resource_path("assets/female_patient.png")
                    if getattr(patient, "gender", "") == "Female"
                    else resource_path("assets/male_patient.png"))
        pix = _circle_pixmap(img_path, 36)
        if not pix.isNull():
            av.setPixmap(pix)
        else:
            av.setText("👤"); av.setFont(QFont(CAIRO, 16))
        hl.addWidget(av)
        hl.addSpacing(12)

        def cell(text, align=Qt.AlignLeft | Qt.AlignVCenter,
                 color=TEXT_DARK):
            l = QLabel(str(text) if text else "—")
            l.setFont(_semi(11))
            l.setStyleSheet(
                f"color:{color}; background:transparent; border:none;")
            l.setAlignment(align)
            return l

        hl.addWidget(cell(patient.full_name or "—"), 2)
        hl.addWidget(cell(
            getattr(patient, "phone_number", "") or "—",
            Qt.AlignCenter), 2)

        status = getattr(patient, "status", None) or "—"
        status_color = (RED    if status == "Positive"  else
                        GREEN  if status == "Negative"  else
                        ORANGE if status == "PreCancer" else TEXT_MID)
        if status == "—":
            hl.addWidget(cell("—", Qt.AlignCenter, TEXT_MID), 1)
        else:
            badge_w = QWidget()
            badge_w.setStyleSheet("background:transparent;")
            bhl = QHBoxLayout(badge_w)
            bhl.setContentsMargins(0, 0, 0, 0); bhl.setSpacing(0)
            bhl.addWidget(_badge(status, status_color))
            bhl.addStretch()
            hl.addWidget(badge_w, 1)

        stage = getattr(patient, "stage", None) or "—"
        hl.addWidget(cell(stage, Qt.AlignCenter), 1)
        hl.addWidget(cell(
            getattr(patient, "age", "—") or "—",
            Qt.AlignCenter), 1)
        hl.addWidget(cell(
            getattr(patient, "gender", "—") or "—",
            Qt.AlignCenter), 1)
        lv = getattr(patient, "last_visit", None) or "—"
        hl.addWidget(cell(lv, Qt.AlignCenter), 1)

        arrow_btn = QPushButton("›")
        arrow_btn.setFixedSize(32, 32)
        arrow_btn.setCursor(Qt.PointingHandCursor)
        arrow_btn.setFont(_semi(16))
        arrow_btn.setStyleSheet(f"""
            QPushButton {{ background:#EEF4FF; color:{BLUE};
                           border-radius:8px; border:none; }}
            QPushButton:hover {{ background:#DDEEFF; }}
        """)
        arrow_btn.clicked.connect(
            lambda: self.detail_clicked.emit(patient.id))
        hl.addWidget(arrow_btn)


class PaginationBar(QWidget):
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._hl = QHBoxLayout(self)
        self._hl.setContentsMargins(0, 0, 0, 0); self._hl.setSpacing(4)

    def update_pages(self, current, total):
        while self._hl.count():
            item = self._hl.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._hl.addStretch()

        def nav_btn(text, page, enabled=True):
            b = QPushButton(text); b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor if enabled
                        else Qt.ArrowCursor)
            b.setEnabled(enabled); b.setFont(_semi(11))
            b.setStyleSheet(f"""
                QPushButton {{ background:transparent;
                    color:{BLUE if enabled else TEXT_MID};
                    border:none; border-radius:6px; }}
                QPushButton:hover:enabled {{ background:#EEF4FF; }}
            """)
            if enabled:
                b.clicked.connect(
                    lambda _, p=page: self.page_changed.emit(p))
            return b

        def page_btn(num):
            b = QPushButton(str(num)); b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor); b.setFont(_semi(11))
            active = (num == current)
            b.setStyleSheet(f"""
                QPushButton {{ background:{BLUE if active else 'transparent'};
                    color:{'white' if active else TEXT_DARK};
                    border:{'none' if active else f'1px solid {CARD_BORDER}'};
                    border-radius:6px; }}
                QPushButton:hover {{
                    background:{BLUE if active else '#EEF4FF'}; }}
            """)
            if not active:
                b.clicked.connect(
                    lambda _, p=num: self.page_changed.emit(p))
            return b

        self._hl.addWidget(nav_btn("‹", current - 1, current > 1))
        for p in self._get_pages(current, total):
            if p == "...":
                dots = QLabel("...")
                dots.setFixedSize(24, 32); dots.setAlignment(Qt.AlignCenter)
                dots.setStyleSheet(
                    f"color:{TEXT_MID}; background:transparent;")
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
#  DB LOADER
# ─────────────────────────────────────────────────────────────
def _load_patients_from_db():
    import types
    try:
        from sqlalchemy import text
        session = SessionLocal()
        sql = text("""
            SELECT
                p.id,
                p.full_name,
                p.phone_number,
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
            ORDER BY p.full_name
        """)
        rows = session.execute(sql).fetchall()
        session.close()
    except Exception as ex:
        print(f"[patients] DB load error: {ex}")
        return []

    result = []
    for row in rows:
        exam_date = row[8]
        if exam_date:
            try:
                dt = (datetime.fromisoformat(exam_date[:19])
                      if isinstance(exam_date, str) else exam_date)
                last_visit = dt.strftime("%d %b %Y")
            except Exception:
                last_visit = str(exam_date)[:10]
        else:
            last_visit = "—"

        result.append(types.SimpleNamespace(
            id           = row[0],
            full_name    = row[1] or "",
            phone_number = row[2] or "",
            age          = str(row[3]) if row[3] else "",
            gender       = row[4] or "",
            created_at   = row[5],
            status       = row[6] or "—",
            stage        = row[7] or "—",
            last_visit   = last_visit,
        ))
    return result


# ─────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────
class PatientsContent(QWidget):
    navigate_to_add = Signal()
    navigate_back   = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._all_patients  = []; self._filtered = []
        self._current_page  = 1
        self._active_filter = "All"
        self._search_text   = ""
        self._selected_date = None
        self._build_ui()
        self.load_patients()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16); outer.setSpacing(12)

        # ── Top bar ───────────────────────────────────────────
        top = QHBoxLayout()

        back_lbl = QPushButton("< Patients")
        back_lbl.setFont(_semi(13)); back_lbl.setCursor(Qt.PointingHandCursor)
        back_lbl.setStyleSheet(f"""
            QPushButton {{ color:{BLUE}; background:transparent;
                border:none; text-align:left; padding:0; }}
            QPushButton:hover {{ color:#0D3E8A; }}
        """)
        back_lbl.clicked.connect(self.navigate_back.emit)
        top.addWidget(back_lbl); top.addStretch()

        self._date_btn = QPushButton()
        self._date_btn.setFixedHeight(38); self._date_btn.setCursor(Qt.PointingHandCursor)
        self._date_btn.setText("  📅  Select Date")
        self._date_btn.setFont(_semi(12))
        self._date_btn.setStyleSheet(f"""
            QPushButton {{ background:{WHITE}; color:{TEXT_DARK};
                border:1px solid {CARD_BORDER}; border-radius:10px;
                padding:0 12px; text-align:left; }}
            QPushButton:hover {{ border:1px solid {BLUE}; }}
        """)
        self._date_btn.clicked.connect(self._show_calendar)

        self._calendar_popup = QCalendarWidget()
        self._calendar_popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self._calendar_popup.setGridVisible(False)
        self._calendar_popup.setStyleSheet(f"""
            QCalendarWidget {{ background:{WHITE}; border:1px solid {CARD_BORDER};
                border-radius:16px; min-width:300px; }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background:{WHITE}; padding:6px 4px 2px 4px;
                border-top-left-radius:16px; border-top-right-radius:16px; }}
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {{
                background:#EEF4FF; color:{BLUE}; border:none;
                border-radius:8px; width:28px; height:28px;
                font-size:14px; font-weight:bold; }}
            QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
            QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {{
                background:{BLUE}; color:white; }}
            QCalendarWidget QToolButton#qt_calendar_monthbutton,
            QCalendarWidget QToolButton#qt_calendar_yearbutton {{
                color:{TEXT_DARK}; background:transparent; border:none;
                font-family:{CAIRO}; font-size:14px; font-weight:700;
                padding:2px 6px; }}
            QCalendarWidget QWidget {{ alternate-background-color:{WHITE}; }}
            QCalendarWidget QAbstractItemView {{
                background:{WHITE}; gridline-color:transparent;
                selection-background-color:{BLUE}; selection-color:white;
                color:{TEXT_DARK}; font-family:{CAIRO}; font-size:12px;
                outline:none; }}
            QCalendarWidget QAbstractItemView:disabled {{ color:#C8D8F0; }}
            QCalendarWidget QSpinBox {{
                color:{TEXT_DARK}; background:transparent; border:none;
                font-family:{CAIRO}; font-size:14px; font-weight:700; }}
            QCalendarWidget QSpinBox::up-button,
            QCalendarWidget QSpinBox::down-button {{ width:0; height:0; }}
        """)
        self._calendar_popup.clicked.connect(self._on_date_selected)

        self._clear_date_btn = QPushButton("✕")
        self._clear_date_btn.setFixedSize(28, 28)
        self._clear_date_btn.setCursor(Qt.PointingHandCursor)
        self._clear_date_btn.setFont(_semi(11))
        self._clear_date_btn.setStyleSheet(f"""
            QPushButton {{ background:#F0F4FF; color:{TEXT_MID};
                border-radius:6px; border:none; }}
            QPushButton:hover {{ background:#FFDEDE; color:{RED}; }}
        """)
        self._clear_date_btn.setVisible(False)
        self._clear_date_btn.clicked.connect(self._clear_date)

        date_row = QHBoxLayout()
        date_row.setSpacing(4); date_row.setContentsMargins(0, 0, 0, 0)
        date_row.addWidget(self._date_btn)
        date_row.addWidget(self._clear_date_btn)
        top.addLayout(date_row)
        top.addSpacing(8)

        add_btn = QPushButton("+ Add Patient")
        add_btn.setFixedHeight(38); add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFont(_semi(12))
        add_btn.setStyleSheet(f"""
            QPushButton {{ background:{BLUE}; color:white;
                border-radius:10px; border:none; padding:0 16px; }}
            QPushButton:hover {{ background:#0D3E8A; }}
        """)
        add_btn.clicked.connect(self.navigate_to_add.emit)
        top.addWidget(add_btn)
        outer.addLayout(top)

        # ── White card ────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{WHITE}; border-radius:16px;"
            f"border:1px solid {CARD_BORDER}; }}")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card, 1)

        card_vl = QVBoxLayout(card)
        card_vl.setContentsMargins(16, 16, 16, 16); card_vl.setSpacing(12)

        sf = QFrame()
        sf.setStyleSheet(
            f"QFrame {{ background:{WHITE}; border:1px solid {CARD_BORDER};"
            f"border-radius:12px; }}")
        sf.setFixedHeight(44)
        shl = QHBoxLayout(sf)
        shl.setContentsMargins(12, 0, 12, 0); shl.setSpacing(8)

        search_icon = QLabel()
        search_icon.setFixedSize(24, 24); search_icon.setAlignment(Qt.AlignCenter)
        search_icon.setStyleSheet("background:transparent; border:none;")
        self._search_movie = QMovie(resource_path("assets/search.gif"))
        if self._search_movie.isValid():
            self._search_movie.setScaledSize(QSize(22, 22))
            search_icon.setMovie(self._search_movie)
            self._search_movie.start()
        else:
            pix = QPixmap(resource_path("assets/search.png"))
            if not pix.isNull():
                search_icon.setPixmap(
                    pix.scaled(22, 22, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation))
            else:
                search_icon.setText("🔍"); search_icon.setFont(QFont(CAIRO, 13))

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search patients..")
        self._search.setFont(_semi(11))
        self._search.setStyleSheet(
            "QLineEdit { border:none; background:transparent; color:#1A1A2E; }")
        self._search.textChanged.connect(self._on_search)
        shl.addWidget(search_icon); shl.addWidget(self._search, 1)
        card_vl.addWidget(sf)

        tabs = QHBoxLayout(); tabs.setSpacing(6)
        self._filter_btns = {}
        for label, color in [("All", WHITE), ("Positive", RED),
                              ("Negative", GREEN), ("PreCancer", ORANGE)]:
            btn = FilterBtn(label, 0,
                            color if label != "All" else BLUE,
                            active=(label == "All"))
            btn.clicked.connect(lambda _, l=label: self._set_filter(l))
            self._filter_btns[label] = btn; tabs.addWidget(btn)
        tabs.addStretch()
        card_vl.addLayout(tabs)

        hdr = QFrame()
        hdr.setStyleSheet("background:transparent; border:none;")
        hdr_hl = QHBoxLayout(hdr)
        hdr_hl.setContentsMargins(12, 4, 12, 4); hdr_hl.setSpacing(0)
        hdr.setFixedHeight(36)

        def _hl(text, stretch=0, align=Qt.AlignLeft | Qt.AlignVCenter):
            l = QLabel(text); l.setFont(_semi(10))
            l.setStyleSheet(
                f"color:{TEXT_MID}; background:transparent; border:none;")
            l.setAlignment(align)
            return l, stretch

        sp = QLabel(); sp.setFixedWidth(50); hdr_hl.addWidget(sp)
        for lbl, s in [
            _hl("Name",       2),
            _hl("Phone",      2, Qt.AlignCenter),
            _hl("Status",     1),
            _hl("Stage",      1, Qt.AlignCenter),
            _hl("Age",        1, Qt.AlignCenter),
            _hl("Gender",     1, Qt.AlignCenter),
            _hl("Last Visit", 1, Qt.AlignCenter),
        ]:
            hdr_hl.addWidget(lbl, s)
        sp2 = QLabel(); sp2.setFixedWidth(32); hdr_hl.addWidget(sp2)
        card_vl.addWidget(hdr)

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet(f"background:{CARD_BORDER};")
        card_vl.addWidget(div)

        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet("background:transparent;")
        self._rows_vl = QVBoxLayout(self._rows_widget)
        self._rows_vl.setContentsMargins(0, 0, 0, 0); self._rows_vl.setSpacing(0)
        card_vl.addWidget(self._rows_widget, 1)

        bottom = QHBoxLayout()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(_semi(10))
        self._count_lbl.setStyleSheet(
            f"color:{TEXT_MID}; background:transparent;")
        bottom.addWidget(self._count_lbl); bottom.addStretch()
        self._pagination = PaginationBar()
        self._pagination.page_changed.connect(self._go_to_page)
        bottom.addWidget(self._pagination)
        card_vl.addLayout(bottom)

    def _show_calendar(self):
        pos = self._date_btn.mapToGlobal(self._date_btn.rect().bottomLeft())
        self._calendar_popup.move(pos); self._calendar_popup.show()

    def _on_date_selected(self, qdate):
        self._selected_date = datetime(qdate.year(), qdate.month(), qdate.day())
        self._date_btn.setText(
            f"  📅  {self._selected_date.strftime('%d %b %Y')}")
        self._clear_date_btn.setVisible(True)
        self._calendar_popup.hide()
        self._apply_filters()

    def _clear_date(self):
        self._selected_date = None
        self._date_btn.setText("  📅  Select Date")
        self._clear_date_btn.setVisible(False)
        self._apply_filters()

    def load_patients(self):
        self._all_patients = _load_patients_from_db()
        self._apply_filters()

    def _apply_filters(self):
        pts = self._all_patients

        # ── Step 1: apply date filter first ──────────────────
        if self._selected_date:
            selected_str = self._selected_date.strftime("%d %b %Y")
            pts = [p for p in pts
                   if getattr(p, "last_visit", "—") == selected_str]

        # ── Step 2: update badge counts from date-filtered pool
        # FIX: counts now reflect only patients visible after the
        # date filter, not the entire database.
        self._update_counts(pts)

        # ── Step 3: apply search filter ───────────────────────
        if self._search_text:
            q = self._search_text.lower()
            pts = [p for p in pts
                   if q in (p.full_name or "").lower()]

        # ── Step 4: apply status filter ───────────────────────
        if self._active_filter != "All":
            pts = [p for p in pts
                   if getattr(p, "status", "") == self._active_filter]

        self._filtered = pts
        self._current_page = 1
        self._render_page()

    def _update_counts(self, pool: list):
        """
        Update the filter-tab badge counts from *pool*
        (which is already date-filtered).
        FIX: was always counting from self._all_patients,
        so selecting a date with no matches still showed
        the full totals on the All/Positive/Negative/PreCancer tabs.
        """
        self._filter_btns["All"].update_count(len(pool))
        self._filter_btns["Positive"].update_count(
            sum(1 for p in pool if getattr(p, "status", "") == "Positive"))
        self._filter_btns["Negative"].update_count(
            sum(1 for p in pool if getattr(p, "status", "") == "Negative"))
        self._filter_btns["PreCancer"].update_count(
            sum(1 for p in pool if getattr(p, "status", "") == "PreCancer"))

    def _render_page(self):
        while self._rows_vl.count():
            item = self._rows_vl.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        total    = len(self._filtered)
        pages    = max(1, math.ceil(total / PAGE_SIZE))
        start    = (self._current_page - 1) * PAGE_SIZE
        end      = min(start + PAGE_SIZE, total)
        page_pts = self._filtered[start:end]

        if not page_pts:
            empty = QLabel("No patients found.")
            empty.setFont(_semi(12)); empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{TEXT_MID}; background:transparent;")
            self._rows_vl.addWidget(empty)
        else:
            for pt in page_pts:
                row = PatientRow(pt)
                row.detail_clicked.connect(self._on_patient_detail)
                self._rows_vl.addWidget(row)
        self._rows_vl.addStretch()

        self._count_lbl.setText(
            f"showing {start+1} to {end} of {total} "
            f"patient{'s' if total != 1 else ''}"
            if total else "No patients found")
        self._pagination.update_pages(self._current_page, pages)

    def _set_filter(self, label):
        self._active_filter = label
        for name, btn in self._filter_btns.items():
            btn.set_active(name == label)
        self._apply_filters()

    def _on_search(self, text):
        self._search_text = text; self._apply_filters()

    def _go_to_page(self, page):
        self._current_page = page; self._render_page()

    def _on_patient_detail(self, patient_id: int):
        parent = self.parent()
        while parent:
            if hasattr(parent, "_manager") and parent._manager:
                mgr = parent._manager
                if hasattr(mgr, "navigate_to_patient_details"):
                    mgr.navigate_to_patient_details(patient_id)
                    return
            parent = (parent.parent()
                      if hasattr(parent, "parent") else None)

    def refresh(self):
        self._selected_date = None
        self._date_btn.setText("  📅  Select Date")
        self._clear_date_btn.setVisible(False)
        self.load_patients()


# ─────────────────────────────────────────────────────────────
#  SCREEN
# ─────────────────────────────────────────────────────────────
class PatientsScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Patients", parent=parent)
        self._content = PatientsContent()
        self._content.navigate_to_add.connect(self._go_to_add_patient)
        self._content.navigate_back.connect(self._go_back)
        self.set_content(self._content)

    def _go_to_add_patient(self):
        if self._manager and hasattr(self._manager, "navigate_to"):
            self._manager.navigate_to("Add Patient")

    def _go_back(self):
        if self._manager and hasattr(self._manager, "go_back"):
            self._manager.go_back()

    def refresh(self):
        self._content.refresh()

    def on_nav(self, label: str):
        pass