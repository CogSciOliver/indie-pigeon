from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, Text, UniqueConstraint
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint("order_ref"),
        UniqueConstraint("square_payment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # internal order reference used to match Square webhook events
    order_ref: Mapped[str] = mapped_column(String(128), nullable=False)

    # kept for backward compatibility with existing DBs
    checkout_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Square identifiers
    square_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    square_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checkout_link_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # product information
    item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # payment data
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # order state machine
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending_payment",
    )

    # email data
    buyer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    delivery_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    email_source: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    email_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(Integer, nullable=False)

    email_status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # sent | error

    provider_message_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    __table_args__ = (
        UniqueConstraint("provider", "event_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )