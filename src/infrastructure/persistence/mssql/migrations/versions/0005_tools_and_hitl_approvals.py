"""tools_and_hitl_approvals

Revision ID: 0005_tools_and_hitl_approvals
Revises: 0004_knowledge_documents_and_vectors
Create Date: 2026-09-28 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_tools_and_hitl_approvals"
down_revision: str | Sequence[str] | None = "0004_knowledge_documents_and_vectors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to include tool approvals and execution audit tables."""
    # 1. tool_approvals table
    op.create_table(
        "tool_approvals",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("conversation_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("call_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tool_name", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column("arguments_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=20),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("operator_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("justification", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("resolved_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tool_approvals_tenant_id"),
        "tool_approvals",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_approvals_tenant_status",
        "tool_approvals",
        ["tenant_id", "status"],
        unique=False,
    )

    # 2. tool_execution_audits table
    op.create_table(
        "tool_execution_audits",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("conversation_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("call_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tool_name", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column("arguments_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("output_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_error", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("execution_time_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tool_execution_audits_tenant_id"),
        "tool_execution_audits",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_audits_call_id",
        "tool_execution_audits",
        ["call_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema removing tool tables."""
    op.drop_table("tool_execution_audits")
    op.drop_table("tool_approvals")
