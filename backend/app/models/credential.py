"""Credential model: encrypted secrets attached to a target."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Credential(Base):
    __tablename__ = "credentials"
    __table_args__ = (
        UniqueConstraint(
            "target_id", "identity_name", name="uq_credentials_target_identity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
