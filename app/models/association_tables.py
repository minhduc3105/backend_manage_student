# backend/app/models/association_tables.py
from sqlalchemy import Table, Column, Integer, ForeignKey
from app.database import Base
import enum

# ---- User-Roles association ----
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True),
)
