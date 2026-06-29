"""
models/examination.py  — ADD patch_labels column
"""

import os, re, uuid, shutil, json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from core.database import Base, APP_FOLDER

EXAM_ROOT = os.path.join(APP_FOLDER, "Examinations")


def _safe_name(name: str) -> str:
    clean = re.sub(r'[^A-Za-z0-9_\- ]+', '_', (name or "unknown").strip())
    return clean.strip('_') or "unknown"


def save_exam_image(patient_name, exam_date, src_path, category):
    if not src_path or not os.path.exists(src_path):
        return ""
    try:
        datetime_str = exam_date.strftime("%Y-%m-%d_%H-%M-%S")
        dest_dir = os.path.join(
            EXAM_ROOT, _safe_name(patient_name), datetime_str, category)
        os.makedirs(dest_dir, exist_ok=True)
        ext      = os.path.splitext(src_path)[1].lower() or ".png"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest     = os.path.join(dest_dir, filename)
        shutil.copy2(src_path, dest)
        return dest
    except Exception as e:
        print(f"[save_exam_image] error copying {category}: {e}")
        return ""


class Examination(Base):
    __tablename__ = "examinations"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    patient_id         = Column(Integer, ForeignKey("patients.id"),          nullable=False)
    doctor_id          = Column(Integer, ForeignKey("application_users.id"), nullable=False)
    original_image     = Column(String,  nullable=True)
    segmentation_image = Column(String,  nullable=True)
    heatmap_image      = Column(String,  nullable=True)
    classified_image   = Column(String,  nullable=True)
    status             = Column(String,  nullable=True)
    stage              = Column(String,  nullable=True)
    patch_labels       = Column(Text,    nullable=True)   # ← NEW: JSON list of 16 labels
    created_at         = Column(DateTime, default=datetime.utcnow)


# ── Helpers for patch_labels ──────────────────────────────────

def encode_patch_labels(labels: list) -> str:
    """Convert list[16] of label strings to a JSON string for DB storage."""
    return json.dumps(labels) if labels else ""


def decode_patch_labels(value: str) -> list:
    """Convert stored JSON string back to list[16], or [] on failure."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except Exception:
        return []