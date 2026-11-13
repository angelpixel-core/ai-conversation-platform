"""message_idempotency_key

Revision ID: 0009_message_idempotency_key
Revises: 0008_tenant_metadata_and_rate_limits
Create Date: 2026-11-13 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_message_idempotency_key"
down_revision: str | Sequence[str] | None = "0008_tenant_metadata_and_rate_limits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add idempotency_key column to messages table."""
    op.add_column(
        "messages",
        sa.Column(
            "idempotency_key",
            sqlmodel.sql.sqltypes.AutoString(length=128),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove idempotency_key column from messages table."""
    op.drop_column("messages", "idempotency_key")

