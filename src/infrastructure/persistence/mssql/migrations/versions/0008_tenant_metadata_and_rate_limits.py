"""tenant_metadata_and_rate_limits

Revision ID: 0008_tenant_metadata_and_rate_limits
Revises: 0007_governance_and_security_audit
Create Date: 2026-10-15 15:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_tenant_metadata_and_rate_limits"
down_revision: str | Sequence[str] | None = "0007_governance_and_security_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add contact_email to tenants and max_requests_per_minute to tenant_policies."""
    op.add_column(
        "tenants",
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.add_column(
        "tenant_policies",
        sa.Column(
            "max_requests_per_minute",
            sa.Integer(),
            server_default="60",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove contact_email from tenants and max_requests_per_minute from tenant_policies."""
    op.drop_column("tenant_policies", "max_requests_per_minute")
    op.drop_column("tenants", "contact_email")
