"""governance_and_security_audit

Revision ID: 0007_governance_and_security_audit
Revises: 0006_multi_agent_checkpoints
Create Date: 2026-09-29 01:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_governance_and_security_audit"
down_revision: str | Sequence[str] | None = "0006_multi_agent_checkpoints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to include security incidents and PII audit logs tables."""
    # 1. security_incidents table
    op.create_table(
        "security_incidents",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("severity", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("rule_name", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column(
            "description",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "prompt_preview",
            sqlmodel.sql.sqltypes.AutoString(length=1000),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "details_json",
            sqlmodel.sql.sqltypes.AutoString(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_incidents_tenant_id"),
        "security_incidents",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_security_incidents_tenant_created",
        "security_incidents",
        ["tenant_id", "created_at"],
        unique=False,
    )

    # 2. pii_audit_logs table
    op.create_table(
        "pii_audit_logs",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("entity_type", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("masked_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("raw_hash_sha256", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pii_audit_logs_tenant_id"),
        "pii_audit_logs",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_pii_audit_logs_created",
        "pii_audit_logs",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema removing security incidents and PII audit logs tables."""
    op.drop_table("pii_audit_logs")
    op.drop_table("security_incidents")
