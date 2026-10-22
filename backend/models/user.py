"""users 표. 회원 (2차). 1차에는 테스트 사용자 한 줄(번호 1)만 쓴다."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # 원래 값으로 되돌릴 수 없는 해시
    terms_agreed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 3차
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
