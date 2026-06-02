from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.base import Base


class SellerApplication(Base):
    __tablename__ = "seller_applications"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger
    )

    full_name: Mapped[str] = mapped_column(
        String(255)
    )

    phone: Mapped[str] = mapped_column(
        String(30)
    )

    shop_name: Mapped[str] = mapped_column(
        String(255)
    )

    card_number: Mapped[str] = mapped_column(
        String(30)
    )

    passport_photo: Mapped[str] = mapped_column(
        Text
    )

    selfie_photo: Mapped[str] = mapped_column(
        Text
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
