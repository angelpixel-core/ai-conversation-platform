"""Template canónico para Modelos SQLModel de Tenancy (Infraestructura).

Reglas:
- Pertenecen a src/infrastructure/persistence/mssql/models.py.
- Define tablas relacionales 'tenants' y 'tenant_policies' compatibles con Microsoft SQL Server.
- Utiliza Decimal con max_digits=12 y decimal_places=4 para precisión monetaria.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class TenantModel(SQLModel, table=True):
    """Modelo relacional físico para la tabla 'tenants'."""

    __tablename__ = "tenants"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True, max_length=64, nullable=False)
    name: str = Field(max_length=200, nullable=False)
    status: str = Field(default="ACTIVE", max_length=20, nullable=False)
    balance_usd: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=4, nullable=False)
    reserved_usd: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=4, nullable=False)
    currency: str = Field(default="USD", max_length=3, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    policy: Optional["TenantPolicyModel"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False, "lazy": "joined"},
    )


class TenantPolicyModel(SQLModel, table=True):
    """Modelo relacional físico para la tabla 'tenant_policies'."""

    __tablename__ = "tenant_policies"  # pyright: ignore[reportAssignmentType]

    tenant_id: str = Field(
        primary_key=True,
        foreign_key="tenants.id",
        max_length=64,
        nullable=False,
        ondelete="CASCADE",
    )
    tier: str = Field(default="FREE", max_length=20, nullable=False)
    max_tokens_per_request: int = Field(default=4096, nullable=False)
    monthly_budget_usd: Decimal = Field(default=Decimal("50.00"), max_digits=12, decimal_places=4, nullable=False)
    allowed_models_json: str = Field(
        default='["gpt-4o-mini", "gemini-1.5-flash"]',
        nullable=False,
    )

    tenant: Optional[TenantModel] = Relationship(back_populates="policy")
