from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, Text, UniqueConstraint
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("checkout_ref"),
        UniqueConstraint("square_payment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # reference created BEFORE checkout
    checkout_ref: Mapped[str] = mapped_column(String(128), nullable=False)

    # added once webhook fires
    square_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    buyer_email: Mapped[str] = mapped_column(String(320), nullable=False)

    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending|paid|fulfilled|failed

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(Integer, nullable=False)

    email_status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # sent|error

    provider_message_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )