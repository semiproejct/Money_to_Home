"""profiles 표. 재무정보, 대출 선택, 저축 계획. 회원 한 명에 3줄까지다 (재무정보 1 ~ 3, 2026-10-21)."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.loan_product import LoanProduct


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", "slot", name="uq_profiles_user_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 찜(saved_results.profile_id)이 가리킨다
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(SmallInteger)  # 칸 번호 1, 2, 3
    name: Mapped[str] = mapped_column(String(10))  # 칸 이름. 1 ~ 10자
    age: Mapped[int] = mapped_column(SmallInteger)  # 만 나이. 15 ~ 100. 계산에 쓰지 않는다
    annual_income: Mapped[int] = mapped_column(BigInteger)  # 연 소득. 원. 계산에 쓰지 않는다
    current_assets: Mapped[int] = mapped_column(BigInteger)  # 현재 보유자산. 원
    loan_choice: Mapped[str | None] = mapped_column(Enum("product", "none", name="loan_choice"))  # 비어 있으면 아직 안 고름
    loan_product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("loan_products.id"))
    repayment_years: Mapped[int | None] = mapped_column(SmallInteger)
    monthly_saving: Mapped[int | None] = mapped_column(BigInteger)  # 월 저축 가능액. 원
    target_years: Mapped[int | None] = mapped_column(SmallInteger)  # 0, 3, 5, 10 중 하나. 0은 "지금"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    selected_at: Mapped[datetime | None] = mapped_column(DateTime)  # 시작 화면에서 이 칸을 골라 지도를 본 마지막 시각

    loan_product: Mapped[LoanProduct | None] = relationship(lazy="joined")

    @property
    def loan_product_name(self) -> str | None:
        """고른 상품의 이름. 고르지 않았으면 None"""
        return self.loan_product.name if self.loan_product else None
