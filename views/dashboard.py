"""
dashboard.py  —  DashboardScreen + DashboardContent  (dynamic, DB-driven)
Place at: views/dashboard.py

All data comes from the database via DashboardData.load().
Every section uses the real query result; no hard-coded demo values remain.
"""

import math
from datetime import datetime, timedelta, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPixmap,
    QLinearGradient, QPainterPath, QPen, QBrush,
)

from core.utils import resource_path
from views.main_layout import MainLayout, BLUE, BG_MAIN, CAIRO

WHITE       = "#FFFFFF"
GREEN       = "#3F9D53"
RED         = "#D94558"
ORANGE      = "#F2A427"
TEXT_DARK   = "#1A1A2E"
TEXT_MID    = "#6B7280"
CARD_BORDER = "#D9E4F5"

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


def _semi(size: int) -> QFont:
    f = QFont(CAIRO, size)
    f.setWeight(QFont.Weight.DemiBold)
    return f


# ─────────────────────────────────────────────────────────────
#  DATABASE QUERIES  — one place, easy to extend
# ─────────────────────────────────────────────────────────────
class DashboardData:
    """
    Loads every metric the dashboard needs in a single pass.
    Call DashboardData.load() → returns a populated instance.

    Definitions
    ──────────────────────────────────────────────────────────
    "last examination" of a patient = the examination with the
    MAX created_at for that patient_id.

    status values stored in Examination.status:
        "Positive"   → cancer (Stage 1 / Stage 2 / Stage 3 in .stage)
        "Negative"   → normal
        "PreCancer"  → pre-cancer
    """

    def __init__(self):
        # stat cards
        self.total_patients      = 0
        self.new_patients_week   = 0
        self.cancer_positive     = 0
        self.new_positive_week   = 0
        self.cancer_negative     = 0
        self.new_negative_week   = 0
        self.pre_cancer          = 0
        self.new_precancer_week  = 0

        # bar chart  {stage_label: count}
        self.stage_distribution  = {"Stage 1": 0, "Stage 2": 0, "Stage 3": 0}

        # pie chart  {label: count}
        self.detection_results   = {"Positive": 0, "Negative": 0, "PreCancer": 0}

        # frequent patients — list of (full_name, exam_count, last_visit_date)
        self.frequent_patients   = []

        # recent patients — list of (full_name, status, stage, exam_date, gender)
        self.recent_patients     = []

        # monthly cancer cases — list of (month_abbr, count) for current year
        self.monthly_cancer      = [(m, 0) for m in MONTH_NAMES]

    # ── helpers ───────────────────────────────────────────────
    @staticmethod
    def _week_ago() -> datetime:
        return datetime.utcnow() - timedelta(days=7)

    @staticmethod
    def _fmt_date(d) -> str:
        """Return 'Today', 'Yesterday', or 'YYYY-MM-DD'."""
        if d is None:
            return ""
        if isinstance(d, datetime):
            d = d.date()
        today = date.today()
        if d == today:
            return "Today"
        if d == today - timedelta(days=1):
            return "Yesterday"
        return d.strftime("%Y-%m-%d")

    # ── main loader ───────────────────────────────────────────
    @classmethod
    def load(cls) -> "DashboardData":
        obj = cls()
        try:
            from core.database import SessionLocal
            from models.patient     import Patient
            from models.examination import Examination
            from sqlalchemy import func, case

            session = SessionLocal()
            week_ago = obj._week_ago()

            # ── 1. Total patients ─────────────────────────────
            obj.total_patients    = session.query(func.count(Patient.id)).scalar() or 0
            obj.new_patients_week = (
                session.query(func.count(Patient.id))
                .filter(Patient.created_at >= week_ago)
                .scalar() or 0
            )

            # ── 2-4. Last-examination status per patient ──────
            # Subquery: latest exam id per patient
            latest_sub = (
                session.query(
                    Examination.patient_id,
                    func.max(Examination.created_at).label("max_dt")
                )
                .group_by(Examination.patient_id)
                .subquery()
            )

            last_exams = (
                session.query(Examination)
                .join(latest_sub,
                      (Examination.patient_id == latest_sub.c.patient_id) &
                      (Examination.created_at == latest_sub.c.max_dt))
                .all()
            )

            pos_ids = set()
            neg_ids = set()
            pre_ids = set()

            for ex in last_exams:
                st = (ex.status or "").strip()
                if st == "Positive":
                    pos_ids.add(ex.patient_id)
                    s = (ex.stage or "").strip()
                    if "1" in s:
                        obj.stage_distribution["Stage 1"] += 1
                    elif "2" in s:
                        obj.stage_distribution["Stage 2"] += 1
                    elif "3" in s:
                        obj.stage_distribution["Stage 3"] += 1
                elif st == "Negative":
                    neg_ids.add(ex.patient_id)
                elif st in ("PreCancer", "Pre Cancer"):
                    pre_ids.add(ex.patient_id)

            obj.cancer_positive = len(pos_ids)
            obj.cancer_negative = len(neg_ids)
            obj.pre_cancer      = len(pre_ids)

            # delta (new this week) — based on exams created this week
            recent_exams_week = (
                session.query(Examination)
                .join(latest_sub,
                      (Examination.patient_id == latest_sub.c.patient_id) &
                      (Examination.created_at == latest_sub.c.max_dt))
                .filter(Examination.created_at >= week_ago)
                .all()
            )
            for ex in recent_exams_week:
                st = (ex.status or "").strip()
                if st == "Positive":
                    obj.new_positive_week += 1
                elif st == "Negative":
                    obj.new_negative_week += 1
                elif st in ("PreCancer", "Pre Cancer"):
                    obj.new_precancer_week += 1

            # ── 5. Detection results (pie) ────────────────────
            obj.detection_results = {
                "Positive":  obj.cancer_positive,
                "Negative":  obj.cancer_negative,
                "PreCancer": obj.pre_cancer,
            }

            # ── 6. Most frequent patients (top 5 by exam count) ─
            freq_rows = (
                session.query(
                    Patient.full_name,
                    Patient.gender,
                    func.count(Examination.id).label("cnt"),
                    func.max(Examination.created_at).label("last_dt"),
                )
                .join(Examination, Examination.patient_id == Patient.id)
                .group_by(Patient.id, Patient.full_name, Patient.gender)
                .order_by(func.count(Examination.id).desc())
                .limit(5)
                .all()
            )
            obj.frequent_patients = [
                (row.full_name, row.gender or "", row.cnt,
                 obj._fmt_date(row.last_dt))
                for row in freq_rows
            ]

            # ── 7. Recent patients (last 2 distinct patients) ──
            # Get latest exam per patient ordered by date desc
            recent_rows = (
                session.query(
                    Patient.full_name,
                    Patient.gender,
                    Examination.status,
                    Examination.stage,
                    Examination.created_at,
                )
                .join(Patient, Patient.id == Examination.patient_id)
                .join(latest_sub,
                      (Examination.patient_id == latest_sub.c.patient_id) &
                      (Examination.created_at == latest_sub.c.max_dt))
                .order_by(Examination.created_at.desc())
                .limit(2)
                .all()
            )
            obj.recent_patients = [
                (row.full_name, row.gender or "",
                 row.status or "", row.stage or "",
                 obj._fmt_date(row.created_at))
                for row in recent_rows
            ]

            # ── 8. Monthly cancer cases (current year) ─────────
            cur_year = datetime.utcnow().year
            monthly_rows = (
                session.query(
                    func.strftime("%m", Examination.created_at).label("month"),
                    func.count(Examination.id).label("cnt"),
                )
                .filter(
                    func.strftime("%Y", Examination.created_at) == str(cur_year),
                    Examination.status == "Positive",
                )
                .group_by(func.strftime("%m", Examination.created_at))
                .all()
            )
            monthly_map = {int(row.month): row.cnt for row in monthly_rows}
            obj.monthly_cancer = [
                (MONTH_NAMES[i], monthly_map.get(i + 1, 0))
                for i in range(12)
            ]

            session.close()

        except Exception as e:
            print(f"[DashboardData.load] error: {e}")

        return obj


# ─────────────────────────────────────────────────────────────
#  STAT CARD
# ─────────────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, icon_path: str, title: str, value: str,
                 delta: str, title_color: str = BLUE, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {WHITE};
                border-radius: 16px;
                border: 1px solid {CARD_BORDER};
            }}
        """)
        self.setMinimumHeight(90)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignCenter)
        pix = QPixmap(icon_path)
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(44, 44, Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))
            icon_lbl.setStyleSheet("background: transparent; border: none;")
        else:
            icon_lbl.setText("●")
            icon_lbl.setFont(QFont(CAIRO, 22))
            icon_lbl.setStyleSheet(
                f"color: {title_color}; background: transparent; border: none;")
        hl.addWidget(icon_lbl)

        vl = QVBoxLayout(); vl.setSpacing(1)

        t_lbl = QLabel(title); t_lbl.setFont(_semi(10))
        t_lbl.setStyleSheet(
            f"color: {title_color}; background: transparent; border: none;")

        v_lbl = QLabel(value); v_lbl.setFont(_semi(20))
        v_lbl.setStyleSheet(
            f"color: {TEXT_DARK}; background: transparent; border: none;")

        parts      = delta.split(" ", 1)
        delta_num  = parts[0]
        delta_rest = " " + parts[1] if len(parts) > 1 else ""

        delta_row = QHBoxLayout()
        delta_row.setSpacing(0)
        delta_row.setContentsMargins(0, 0, 0, 0)
        d_num = QLabel(delta_num); d_num.setFont(_semi(8))
        d_num.setStyleSheet(
            f"color: {title_color}; background: transparent; border: none;")
        d_rest = QLabel(delta_rest); d_rest.setFont(_semi(8))
        d_rest.setStyleSheet(
            f"color: {TEXT_MID}; background: transparent; border: none;")
        delta_row.addWidget(d_num)
        delta_row.addWidget(d_rest)
        delta_row.addStretch()

        d_w = QWidget()
        d_w.setLayout(delta_row)
        d_w.setStyleSheet("background: transparent; border: none;")

        self._v_lbl  = v_lbl
        self._d_num  = d_num
        self._d_rest = d_rest

        vl.addWidget(t_lbl); vl.addWidget(v_lbl); vl.addWidget(d_w)
        hl.addLayout(vl); hl.addStretch()

    def _set_values(self, value: str, delta: str):
        self._v_lbl.setText(value)
        parts = delta.split(" ", 1)
        self._d_num.setText(parts[0])
        self._d_rest.setText(" " + parts[1] if len(parts) > 1 else "")


# ─────────────────────────────────────────────────────────────
#  SECTION CARD
# ─────────────────────────────────────────────────────────────
class SectionCard(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {WHITE};
                border-radius: 16px;
                border: 1px solid {CARD_BORDER};
            }}
        """)
        self._vl = QVBoxLayout(self)
        self._vl.setContentsMargins(14, 12, 14, 12)
        self._vl.setSpacing(8)
        if title:
            t = QLabel(title); t.setFont(_semi(13))
            t.setStyleSheet(
                f"color: {TEXT_DARK}; background: transparent; border: none;")
            self._vl.addWidget(t)

    def body(self) -> QVBoxLayout:
        return self._vl


# ─────────────────────────────────────────────────────────────
#  BAR CHART
# ─────────────────────────────────────────────────────────────
class BarChart(QWidget):
    def __init__(self, data: list, color: str = BLUE,
                 y_max: int = None, y_step: int = None, parent=None):
        super().__init__(parent)
        self._data  = data          # list of (label, value)
        self._color = QColor(color)
        # Auto-scale if not provided
        raw_max     = max((v for _, v in data), default=0)
        self._y_max  = y_max  if y_max  else max(10, math.ceil(raw_max / 10) * 10)
        self._y_step = y_step if y_step else max(1, self._y_max // 5)
        self.setMinimumHeight(160)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pl, pr, pt, pb = 36, 10, 8, 24
        cw = w - pl - pr
        ch = h - pt - pb

        steps = self._y_max // self._y_step
        for i in range(steps + 1):
            val = i * self._y_step
            y   = pt + ch - int(ch * val / self._y_max)
            p.setPen(QColor(CARD_BORDER))
            p.drawLine(pl, y, pl + cw, y)
            p.setPen(QColor(TEXT_MID))
            p.setFont(QFont(CAIRO, 7))
            p.drawText(0, y - 6, pl - 4, 14,
                       Qt.AlignRight | Qt.AlignVCenter, str(val))

        n     = len(self._data)
        grp_w = cw / n if n else cw
        bar_w = grp_w * 0.42
        for i, (lbl, val) in enumerate(self._data):
            bh = int(ch * val / self._y_max) if self._y_max else 0
            x  = pl + i * grp_w + (grp_w - bar_w) / 2
            y  = pt + ch - bh
            p.setBrush(self._color); p.setPen(Qt.NoPen)
            if bh > 0:
                p.drawRoundedRect(int(x), y, int(bar_w), bh, 5, 5)
            p.setPen(QColor(TEXT_MID)); p.setFont(QFont(CAIRO, 7))
            p.drawText(int(x - 8), h - pb + 4, int(bar_w + 16), 18,
                       Qt.AlignCenter, lbl)
        p.end()


# ─────────────────────────────────────────────────────────────
#  PIE CHART  — dynamic slices
# ─────────────────────────────────────────────────────────────
class PieChart(QWidget):
    """Pie chart driven by a dict {label: count}."""

    COLORS = {
        "Positive":  RED,
        "Negative":  GREEN,
        "PreCancer": ORANGE,
    }
    DISPLAY = {
        "Positive":  "Positive",
        "Negative":  "Negative",
        "PreCancer": "Pre Cancer",
    }

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data          # {"Positive": n, "Negative": n, "PreCancer": n}
        self.setMinimumSize(220, 160)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        total = sum(self._data.values()) or 1

        legend_w = 130
        pie_w    = w - legend_w
        side     = min(pie_w, h) - 16
        x        = (pie_w - side) // 2
        y        = (h     - side) // 2
        rect     = QRectF(x, y, side, side)
        start    = 90 * 16

        for key in ("Positive", "Negative", "PreCancer"):
            count = self._data.get(key, 0)
            pct   = count / total * 100
            color = self.COLORS[key]
            span  = int(pct / 100 * 360 * 16)

            p.setBrush(QColor(color))
            p.setPen(Qt.NoPen)
            if span > 0:
                p.drawPie(rect, start, span)

            if pct >= 5:
                mid_angle_r = math.radians(-(start + span / 2) / 16)
                cx = x + side / 2
                cy = y + side / 2
                r  = side * 0.30
                lx = cx + r * math.cos(mid_angle_r)
                ly = cy + r * math.sin(mid_angle_r)
                p.setFont(QFont(CAIRO, 7, int(QFont.Weight.DemiBold)))
                p.setPen(QColor(WHITE))
                p.drawText(QRectF(lx - 22, ly - 10, 44, 20),
                           Qt.AlignCenter, f"{pct:.0f}%")
            start += span

        # Legend
        legend_x = x + side + 14
        dot_size = 14
        row_h    = 32
        total_h  = 3 * row_h
        legend_y = (h - total_h) // 2

        for i, key in enumerate(("Positive", "Negative", "PreCancer")):
            color = self.COLORS[key]
            ly2   = legend_y + i * row_h + row_h // 2
            p.setBrush(QColor(color)); p.setPen(Qt.NoPen)
            p.drawEllipse(legend_x, ly2 - dot_size // 2,
                          dot_size, dot_size)
            p.setPen(QColor(TEXT_DARK))
            p.setFont(QFont(CAIRO, 12, int(QFont.Weight.DemiBold)))
            p.drawText(legend_x + dot_size + 8, ly2 - 10,
                       140, 20,
                       Qt.AlignLeft | Qt.AlignVCenter, self.DISPLAY[key])
        p.end()


# ─────────────────────────────────────────────────────────────
#  LINE CHART
# ─────────────────────────────────────────────────────────────
class LineChart(QWidget):
    def __init__(self, data: list, parent=None):
        super().__init__(parent)
        self._data = data          # list of (label, value)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, _):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        pl, pr, pt, pb = 30, 8, 10, 54
        cw = w - pl - pr
        ch = h - pt - pb

        n     = len(self._data)
        max_v = max(v for _, v in self._data) or 1
        y_max  = max(10, math.ceil(max_v / 10) * 10)
        y_step = max(1, y_max // 5)

        def px(i): return pl + int(i * cw / max(n - 1, 1))
        def py(v): return pt + ch - int(v * ch / y_max)

        dash_pen = QPen(QColor("#DDDDDD"))
        dash_pen.setStyle(Qt.DashLine)
        dash_pen.setWidth(1)
        for i in range(y_max // y_step + 1):
            val = i * y_step
            yy  = py(val)
            p.setPen(dash_pen)
            p.drawLine(pl, yy, pl + cw, yy)
            p.setPen(QColor(TEXT_MID))
            p.setFont(QFont(CAIRO, 7))
            p.drawText(0, yy - 7, pl - 3, 14,
                       Qt.AlignRight | Qt.AlignVCenter, str(val))

        # Fill area
        area = QPainterPath()
        area.moveTo(px(0), py(self._data[0][1]))
        for i, (_, v) in enumerate(self._data[1:], 1):
            area.lineTo(px(i), py(v))
        area.lineTo(px(n - 1), pt + ch)
        area.lineTo(px(0),     pt + ch)
        area.closeSubpath()
        grad = QLinearGradient(0, pt, 0, pt + ch)
        grad.setColorAt(0, QColor(16, 78, 165, 70))
        grad.setColorAt(1, QColor(16, 78, 165, 5))
        p.fillPath(area, grad)

        # Line
        lp = QPen(QColor(BLUE)); lp.setWidth(2)
        p.setPen(lp)
        for i in range(n - 1):
            p.drawLine(QPointF(px(i), py(self._data[i][1])),
                       QPointF(px(i + 1), py(self._data[i + 1][1])))

        # Dots
        p.setBrush(QColor(WHITE))
        p.setPen(QPen(QColor(BLUE), 2))
        for i, (_, v) in enumerate(self._data):
            p.drawEllipse(QPointF(px(i), py(v)), 3, 3)

        # X labels
        p.setFont(QFont(CAIRO, 7))
        p.setPen(QColor(TEXT_MID))
        for i, (lbl, _) in enumerate(self._data):
            p.drawText(px(i) - 18, pt + ch + 5, 36, 14,
                       Qt.AlignCenter, lbl)

        # Legend
        year  = str(datetime.now().year)
        leg_y = h - 12
        leg_x = w // 2 - 20
        p.setBrush(QColor(WHITE))
        p.setPen(QPen(QColor(BLUE), 2))
        p.drawEllipse(QPointF(leg_x, leg_y), 3, 3)
        p.drawLine(QPointF(leg_x + 4, leg_y), QPointF(leg_x + 14, leg_y))
        p.setFont(QFont(CAIRO, 8))
        p.setPen(QColor(TEXT_MID))
        p.drawText(leg_x + 18, leg_y - 7, 45, 14,
                   Qt.AlignLeft | Qt.AlignVCenter, year)
        p.end()


# ─────────────────────────────────────────────────────────────
#  AVATAR helper
# ─────────────────────────────────────────────────────────────
def _avatar_path(gender: str) -> str:
    g = (gender or "").strip().lower()
    if g in ("female", "f"):
        return resource_path("assets/female_patient.png")
    return resource_path("assets/male_patient.png")


def _status_color(status: str) -> str:
    s = (status or "").strip()
    if s == "Positive":
        return RED
    if s in ("PreCancer", "Pre Cancer"):
        return ORANGE
    return GREEN


# ─────────────────────────────────────────────────────────────
#  DASHBOARD CONTENT
# ─────────────────────────────────────────────────────────────
class DashboardContent(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_MAIN};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build()
        self._update(DashboardData.load())

    def refresh(self):
        """Re-query DB and update only the data — no widget rebuild."""
        self._update(DashboardData.load())

    # ── build the fixed skeleton once ─────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── STAT CARDS ────────────────────────────────────────
        stat_row = QHBoxLayout(); stat_row.setSpacing(10)

        self._card_total    = StatCard(resource_path("assets/stat_patients.png"),  "Total Patients",  "0", "+0 this week", BLUE)
        self._card_positive = StatCard(resource_path("assets/stat_positive.png"),  "Cancer Positive", "0", "+0 this week", RED)
        self._card_negative = StatCard(resource_path("assets/stat_negative.png"),  "Cancer Negative", "0", "+0 this week", GREEN)
        self._card_pre      = StatCard(resource_path("assets/stat_accuracy.png"),  "Pre Cancer",      "0", "+0 this week", ORANGE)

        for c in (self._card_total, self._card_positive,
                  self._card_negative, self._card_pre):
            stat_row.addWidget(c)
        root.addLayout(stat_row, 1)

        # ── MIDDLE: bar + pie ─────────────────────────────────
        mid = QHBoxLayout(); mid.setSpacing(10)

        bar_card = SectionCard("Cancer Stage Distribution")
        self._bar = BarChart([("Stage 1", 0), ("Stage 2", 0), ("Stage 3", 0)], BLUE)
        bar_card.body().addWidget(self._bar)
        bar_card.setMinimumHeight(220)
        bar_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mid.addWidget(bar_card, 3)

        pie_card = SectionCard("Cancer Detection Results")
        self._pie = PieChart({"Positive": 0, "Negative": 0, "PreCancer": 0})
        pie_card.body().addWidget(self._pie)
        pie_card.setMinimumHeight(220)
        pie_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mid.addWidget(pie_card, 2)

        root.addLayout(mid, 3)

        # ── BOTTOM ────────────────────────────────────────────
        bot = QHBoxLayout(); bot.setSpacing(10)

        # Frequent patients — container holds header + rows body
        freq_card = SectionCard("Most Frequent Patients")
        freq_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # header
        header = QWidget(); header.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(4, 2, 4, 6); hl.setSpacing(0)
        def hdr(text, stretch=1, align=Qt.AlignLeft | Qt.AlignVCenter):
            l = QLabel(text)
            f = QFont(CAIRO, 9); f.setWeight(QFont.Weight.DemiBold)
            l.setFont(f)
            l.setStyleSheet(f"color:{TEXT_MID}; background:transparent;")
            l.setAlignment(align)
            return l, stretch
        for lw, s in [hdr("Patient Name", 3),
                      hdr("Visits", 1, Qt.AlignCenter),
                      hdr("Last Visit", 1, Qt.AlignCenter)]:
            hl.addWidget(lw, s)
        freq_card.body().addWidget(header)
        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet(f"background:{CARD_BORDER};")
        freq_card.body().addWidget(div)

        # scrollable rows body
        self._freq_body = QWidget(); self._freq_body.setStyleSheet("background:transparent;")
        self._freq_vl   = QVBoxLayout(self._freq_body)
        self._freq_vl.setContentsMargins(0,0,0,0); self._freq_vl.setSpacing(0)
        freq_card.body().addWidget(self._freq_body, 1)
        bot.addWidget(freq_card, 2)

        right_col = QVBoxLayout(); right_col.setSpacing(10)

        line_card = SectionCard("Monthly Cancer Cases")
        self._line = LineChart([(m, 0) for m in MONTH_NAMES])
        self._line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        line_card.body().addWidget(self._line, 1)
        line_card.setMinimumHeight(180)
        line_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_col.addWidget(line_card, 3)

        recent_card = SectionCard("Recent Patients")
        recent_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rdiv = QFrame(); rdiv.setFixedHeight(1)
        rdiv.setStyleSheet(f"background:{CARD_BORDER};")
        recent_card.body().addWidget(rdiv)
        self._recent_body = QWidget(); self._recent_body.setStyleSheet("background:transparent;")
        self._recent_vl   = QVBoxLayout(self._recent_body)
        self._recent_vl.setContentsMargins(0,0,0,0); self._recent_vl.setSpacing(0)
        recent_card.body().addWidget(self._recent_body)
        recent_card.body().addStretch()
        right_col.addWidget(recent_card, 2)

        bot.addLayout(right_col, 3)
        root.addLayout(bot, 4)

    # ── push fresh data into existing widgets ──────────────────
    def _update(self, d: DashboardData):
        # Stat cards
        self._card_total._set_values(f"{d.total_patients:,}",
                                     f"+{d.new_patients_week} this week")
        self._card_positive._set_values(f"{d.cancer_positive:,}",
                                        f"+{d.new_positive_week} this week")
        self._card_negative._set_values(f"{d.cancer_negative:,}",
                                        f"+{d.new_negative_week} this week")
        self._card_pre._set_values(f"{d.pre_cancer:,}",
                                   f"+{d.new_precancer_week} this week")

        # Bar chart
        bar_data = [
            ("Stage 1", d.stage_distribution.get("Stage 1", 0)),
            ("Stage 2", d.stage_distribution.get("Stage 2", 0)),
            ("Stage 3", d.stage_distribution.get("Stage 3", 0)),
        ]
        bar_max  = max((v for _, v in bar_data), default=0)
        self._bar._data   = bar_data
        self._bar._y_max  = max(10, math.ceil(bar_max / 10) * 10)
        self._bar._y_step = max(1, self._bar._y_max // 5)
        self._bar.update()

        # Pie chart
        self._pie._data = d.detection_results
        self._pie.update()

        # Line chart
        self._line._data = d.monthly_cancer
        self._line.update()

        # Frequent patients rows — clear and repopulate
        while self._freq_vl.count():
            item = self._freq_vl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not d.frequent_patients:
            no = QLabel("No data yet"); no.setFont(_semi(10))
            no.setStyleSheet(f"color:{TEXT_MID}; background:transparent;")
            no.setAlignment(Qt.AlignCenter)
            self._freq_vl.addWidget(no)
        else:
            for i, (name, gender, visits, last_visit) in enumerate(d.frequent_patients):
                row_w = QWidget(); row_w.setStyleSheet("background:transparent; border:none;")
                row_hl = QHBoxLayout(row_w)
                row_hl.setContentsMargins(4,6,4,6); row_hl.setSpacing(8)

                av = QLabel(); av.setFixedSize(30,30); av.setAlignment(Qt.AlignCenter)
                av.setStyleSheet("background:transparent; border:none;")
                pix = QPixmap(_avatar_path(gender))
                if not pix.isNull():
                    av.setPixmap(pix.scaled(28,28,Qt.KeepAspectRatio,Qt.SmoothTransformation))

                name_lbl = QLabel(name)
                nf = QFont(CAIRO,10); nf.setWeight(QFont.Weight.DemiBold)
                name_lbl.setFont(nf)
                name_lbl.setStyleSheet(f"color:{TEXT_DARK}; background:transparent; border:none;")

                nc = QWidget(); nc.setStyleSheet("background:transparent; border:none;")
                nc_hl = QHBoxLayout(nc); nc_hl.setContentsMargins(0,0,0,0); nc_hl.setSpacing(8)
                nc_hl.addWidget(av); nc_hl.addWidget(name_lbl); nc_hl.addStretch()

                vf = QFont(CAIRO,10); vf.setWeight(QFont.Weight.DemiBold)
                vl2 = QLabel(str(visits)); vl2.setFont(vf)
                vl2.setStyleSheet(f"color:{BLUE}; background:transparent; border:none;")
                vl2.setAlignment(Qt.AlignCenter)

                ll = QLabel(last_visit); ll.setFont(vf)
                ll.setStyleSheet(f"color:{BLUE}; background:transparent; border:none;")
                ll.setAlignment(Qt.AlignCenter)

                row_hl.addWidget(nc,3); row_hl.addWidget(vl2,1); row_hl.addWidget(ll,1)
                self._freq_vl.addWidget(row_w)

                if i < len(d.frequent_patients) - 1:
                    sep = QFrame(); sep.setFixedHeight(1)
                    sep.setStyleSheet(f"background:{CARD_BORDER};")
                    self._freq_vl.addWidget(sep)

        self._freq_vl.addStretch()

        # Recent patients rows — clear and repopulate
        while self._recent_vl.count():
            item = self._recent_vl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not d.recent_patients:
            no = QLabel("No recent examinations"); no.setFont(_semi(10))
            no.setStyleSheet(f"color:{TEXT_MID}; background:transparent;")
            no.setAlignment(Qt.AlignCenter)
            self._recent_vl.addWidget(no)
        else:
            for i, (name, gender, status, stage, exam_date) in enumerate(d.recent_patients):
                self._recent_vl.addWidget(
                    self._recent_row(
                        name, status, _status_color(status),
                        stage if status == "Positive" else "–",
                        exam_date,
                        add_divider_above=(i > 0),
                        avatar_path=_avatar_path(gender),
                    ))

    def _recent_row(self, name, status, color, stage, exam_date,
                    add_divider_above=False, avatar_path=resource_path("assets/male_patient.png")):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wvl = QVBoxLayout(wrapper)
        wvl.setContentsMargins(0, 0, 0, 0)
        wvl.setSpacing(0)

        if add_divider_above:
            sep = QFrame(); sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: {CARD_BORDER};")
            wvl.addWidget(sep)

        row = QWidget(); row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(4, 8, 4, 8)
        hl.setSpacing(10)

        def lbl(text, c=BLUE, fw=None,
                align=Qt.AlignLeft | Qt.AlignVCenter):
            l = QLabel(text); l.setFont(_semi(10))
            l.setStyleSheet(
                f"color: {c}; background: transparent; border: none;")
            l.setAlignment(align)
            if fw: l.setFixedWidth(fw)
            return l

        av = QLabel(); av.setFixedSize(28, 28)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("background: transparent; border: none;")
        pix = QPixmap(avatar_path)
        if not pix.isNull():
            av.setPixmap(pix.scaled(26, 26, Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation))
        hl.addWidget(av)
        hl.addWidget(lbl(name))
        hl.addStretch()

        badge = QLabel(f" {status} ")
        badge.setFont(_semi(9)); badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(24)
        badge.setStyleSheet(
            f"background:{color}; color:white; border-radius:12px;"
            f" padding:0 12px; border: none;")
        hl.addWidget(badge)
        hl.addWidget(lbl(stage,     BLUE, 70, Qt.AlignCenter))
        hl.addWidget(lbl(exam_date, BLUE, 80, Qt.AlignRight | Qt.AlignVCenter))
        wvl.addWidget(row)
        return wrapper


# ─────────────────────────────────────────────────────────────
#  DASHBOARD SCREEN
# ─────────────────────────────────────────────────────────────
class DashboardScreen(MainLayout):
    def __init__(self, manager=None, parent=None):
        super().__init__(manager, active_page="Dashboard", parent=parent)
        self._dash = DashboardContent()
        self.set_content(self._dash)

    def refresh(self):
        """Called by AppManager when navigating back to Dashboard."""
        self._dash.refresh()

    def set_logged_in_user(self, user):
        name = user.username
        if not name.lower().startswith("dr"):
            name = f"Dr.{name}"
        self.set_doctor_name(name)

    def on_nav(self, label: str):
        pass