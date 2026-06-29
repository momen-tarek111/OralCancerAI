"""
core/initializer.py
────────────────────
Creates all DB tables and seeds the default admin account on first run.
Import all models here so SQLAlchemy's metadata picks them up before
Base.metadata.create_all() is called.
"""

import os
from sqlalchemy.orm import Session
from core.database import engine, Base, SessionLocal, DB_PATH
from core.utils import resource_path
from models.user import ApplicationUser
from core.security import hash_password

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_PROFILE_IMAGE  = resource_path("assets/profile.png")


def initialize_database():
    # Import every model so its table is registered with Base.metadata
    from models.patient import Patient          # noqa: F401
    from models.examination import Examination  # noqa: F401

    first_run = not os.path.exists(DB_PATH)

    # Creates any missing tables (safe to call on every startup)
    Base.metadata.create_all(bind=engine)

    if first_run:
        session: Session = SessionLocal()
        existing = session.query(ApplicationUser).filter_by(
            username=DEFAULT_ADMIN_USERNAME
        ).first()

        if not existing:
            default_admin = ApplicationUser(
                username             = DEFAULT_ADMIN_USERNAME,
                password_hashed      = hash_password(DEFAULT_ADMIN_PASSWORD),
                email                = "admin@local.com",
                phone_number         = "",
                address              = "System Default",
                profile_image        = DEFAULT_PROFILE_IMAGE,
                role                 = "ADMIN",
                gender               = None,
                must_change_password = False,
                is_active            = True,
            )
            session.add(default_admin)
            session.commit()

        session.close()
        return True

    return False