from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id                  = Column(Integer, primary_key=True)
    full_name           = Column(String, nullable=False)
    age                 = Column(String, default="")
    gender              = Column(String, default="")
    phone_number        = Column(String, default="")
    address             = Column(String, default="")
    medical_information = Column(String, default="")
    created_at          = Column(DateTime, default=func.now())
    added_by            = Column(Integer, ForeignKey("application_users.id"), nullable=True)