from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Numeric, ForeignKey, JSON, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PaymentEventType


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subscription_id: Mapped[UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[PaymentEventType] = mapped_column(
        Enum(PaymentEventType), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="payment_events"
    )

    def __repr__(self) -> str:
        return f"<PaymentEvent(id={self.id}, event_type={self.event_type}, amount={self.amount})>"
