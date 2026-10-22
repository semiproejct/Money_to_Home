"""loan_products 표. 대출 상품. 두 줄이다. "대출 없이 계산"은 상품이 아니라 줄이 없다."""
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class LoanProduct(Base):
    __tablename__ = "loan_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 카드를 이 순서로 보여 준다
    name: Mapped[str] = mapped_column(String(100))
    institution: Mapped[str] = mapped_column(String(50))
    max_limit: Mapped[int] = mapped_column(BigInteger)  # 최대 한도. 원
    ltv_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 3))  # 대출 비율. 70%면 0.700
    annual_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 3))  # 대표 금리. 연 4.0%면 4.000
    repayment_years_options: Mapped[str] = mapped_column(String(50))  # "10,15,20,30"처럼 쉼표로 이은 글자
    max_house_price: Mapped[int | None] = mapped_column(BigInteger)  # 대상 주택 가격 상한. 원. 없으면 비운다
    eligibility_summary: Mapped[str] = mapped_column(String(200))
    eligibility_text: Mapped[str] = mapped_column(Text)
    base_date: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(String(500))

    @property
    def repayment_years_list(self) -> list[int]:
        """상환 기간 선택지를 숫자의 목록으로. "10,15,20,30" -> [10, 15, 20, 30]"""
        return [int(years) for years in self.repayment_years_options.split(",") if years.strip()]
