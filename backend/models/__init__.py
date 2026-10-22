"""DB의 표를 옮긴 클래스. 표 하나에 클래스 하나, 파일 하나다.

표는 db/schema.sql로 만든다. 여기의 클래스는 이미 있는 표에 맞춰 이름을 적은 것이다.
칸을 더하거나 고칠 때는 db/schema.sql과 docs/04_database_design.md를 먼저 고친 뒤 여기를 맞춘다.

    from backend.models import Apartment, ApartmentPrice
"""
from backend.models.apartment import Apartment
from backend.models.apartment_facility import ApartmentFacility
from backend.models.apartment_price import ApartmentPrice
from backend.models.bus_stop import BusStop
from backend.models.data_collection import DataCollection
from backend.models.loan_product import LoanProduct
from backend.models.profile import Profile
from backend.models.saved_result import SavedResult
from backend.models.trade import Trade
from backend.models.user import User

__all__ = [
    "Apartment",
    "ApartmentFacility",
    "ApartmentPrice",
    "BusStop",
    "DataCollection",
    "LoanProduct",
    "Profile",
    "SavedResult",
    "Trade",
    "User",
]
