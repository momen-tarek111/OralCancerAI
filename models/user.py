from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from core.database import Base

class ApplicationUser(Base):
    __tablename__ = "application_users"

    id                   = Column(Integer, primary_key=True)
    username             = Column(String, unique=True)
    password_hashed      = Column(String)
    email                = Column(String)
    phone_number         = Column(String, default="")
    address              = Column(String)
    profile_image        = Column(String)
    role                 = Column(String)
    gender               = Column(String, nullable=True, default=None)
    added_by             = Column(Integer, ForeignKey("application_users.id"), nullable=True)
    must_change_password = Column(Boolean, default=False)
    is_active            = Column(Boolean, default=True)   # False = blocked by admin