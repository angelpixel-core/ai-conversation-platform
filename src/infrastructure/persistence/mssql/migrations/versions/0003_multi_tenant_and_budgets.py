"""multi_tenant_and_budgets

Revision ID: 0003_multi_tenant_and_budgets
Revises: 0002_enterprise_auditing
Create Date: 2026-09-28 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_multi_tenant_and_budgets"
down_revision: str | Sequence[str] | None = "0002_enterprise_auditing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to include multi-tenant tables and tenant_id discriminators."""
    # 1. tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=20),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "balance_usd",
            sa.Numeric(precision=12, scale=4),
            server_default="0.0000",
            nullable=False,
        ),
        sa.Column(
            "reserved_usd",
            sa.Numeric(precision=12, scale=4),
            server_default="0.0000",
            nullable=False,
        ),
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=3),
            server_default="USD",
            nullable=False,
        ),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. tenant_policies table
    op.create_table(
        "tenant_policies",
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column(
            "tier",
            sqlmodel.sql.sqltypes.AutoString(length=20),
            server_default="FREE",
            nullable=False,
        ),
        sa.Column("max_tokens_per_request", sa.Integer(), server_default="4096", nullable=False),
        sa.Column(
            "monthly_budget_usd",
            sa.Numeric(precision=12, scale=4),
            server_default="50.0000",
            nullable=False,
        ),
        sa.Column(
            "allowed_models_json",
            sqlmodel.sql.sqltypes.AutoString(),
            server_default='["gpt-4o-mini", "gemini-1.5-flash"]',
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id"),
    )

    # 3. Add tenant_id discriminator to conversations
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_id",
                sqlmodel.sql.sqltypes.AutoString(length=64),
                server_default="default-tenant",
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_conversations_tenant_id"),
            ["tenant_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_conversations_tenant_id_id",
            ["tenant_id", "id"],
            unique=False,
        )

    # 4. Add tenant_id discriminator to audit_logs
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_id",
                sqlmodel.sql.sqltypes.AutoString(length=64),
                server_default="default-tenant",
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_audit_logs_tenant_id"),
            ["tenant_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_audit_logs_tenant_id_id",
            ["tenant_id", "id"],
            unique=False,
        )

    # 5. Add tenant_id discriminator to stream_buffer_chunks
    with op.batch_alter_table("stream_buffer_chunks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_id",
                sqlmodel.sql.sqltypes.AutoString(length=64),
                server_default="default-tenant",
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_stream_buffer_chunks_tenant_id"),
            ["tenant_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_stream_buffer_chunks_tenant_id_id",
            ["tenant_id", "id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema removing multi-tenant additions."""
    with op.batch_alter_table("stream_buffer_chunks") as batch_op:
        batch_op.drop_index("ix_stream_buffer_chunks_tenant_id_id")
        batch_op.drop_index(batch_op.f("ix_stream_buffer_chunks_tenant_id"))
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_index("ix_audit_logs_tenant_id_id")
        batch_op.drop_index(batch_op.f("ix_audit_logs_tenant_id"))
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_index("ix_conversations_tenant_id_id")
        batch_op.drop_index(batch_op.f("ix_conversations_tenant_id"))
        batch_op.drop_column("tenant_id")

    op.drop_table("tenant_policies")
    op.drop_table("tenants")
