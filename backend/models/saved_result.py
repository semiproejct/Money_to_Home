"""saved_results 표. 저장한 시나리오 결과 (3차). 저장할 때의 값을 그대로 남긴다."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SavedResult(Base):
    __tablename__ = "saved_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    apartment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="SET NULL"))
    loan_product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("loan_products.id", ondelete="SET NULL"))
    # 찜할 때 고른 재무정보. 그 재무정보를 지우면 비워진다 ("삭제된 재무정보", 2026-10-21)
    profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"))

    # 저장 당시의 아파트
    apartment_name: Mapped[str] = mapped_column(String(100))
    gu: Mapped[str] = mapped_column(String(10))
    dong: Mapped[str] = mapped_column(String(20))
    area_band: Mapped[int] = mapped_column(SmallInteger)
    exclusive_area: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    supply_area: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    avg_price: Mapped[int] = mapped_column(BigInteger)

    # 저장 당시의 조건
    current_assets: Mapped[int] = mapped_column(BigInteger)
    monthly_saving: Mapped[int] = mapped_column(BigInteger)
    target_years: Mapped[int] = mapped_column(SmallInteger)
    loan_choice: Mapped[str] = mapped_column(Enum("product", "none", name="saved_loan_choice"))
    loan_product_name: Mapped[str | None] = mapped_column(String(100))
    repayment_years: Mapped[int | None] = mapped_column(SmallInteger)

    # 저장 당시의 계산 결과
    accumulated_saving: Mapped[int] = mapped_column(BigInteger)
    loan_amount: Mapped[int | None] = mapped_column(BigInteger)
    monthly_payment: Mapped[int | None] = mapped_column(BigInteger)
    shortage: Mapped[int] = mapped_column(BigInteger)  # 음수면 그 절댓값이 여유자금
    required_monthly_saving: Mapped[int | None] = mapped_column(BigInteger)
    allowed_growth_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))  # 연 %
    category: Mapped[str] = mapped_column(Enum("now", "within", "lack", name="saved_category"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
