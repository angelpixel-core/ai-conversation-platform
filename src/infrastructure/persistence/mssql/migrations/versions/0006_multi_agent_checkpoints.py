"""multi_agent_checkpoints

Revision ID: 0006_multi_agent_checkpoints
Revises: 0005_tools_and_hitl_approvals
Create Date: 2026-09-28 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_multi_agent_checkpoints"
down_revision: str | Sequence[str] | None = "0005_tools_and_hitl_approvals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to include workflow instances and checkpoints tables."""
    # 1. workflow_instances table
    op.create_table(
        "workflow_instances",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            server_default="RUNNING",
            nullable=False,
        ),
        sa.Column("current_node", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column(
            "state_json",
            sqlmodel.sql.sqltypes.AutoString(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_instances_tenant_id"),
        "workflow_instances",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_workflow_instances_tenant_status",
        "workflow_instances",
        ["tenant_id", "status"],
        unique=False,
    )

    # 2. workflow_checkpoints table
    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("workflow_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("node_id", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column("state_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            server_default="RUNNING",
            nullable=False,
        ),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_checkpoints_tenant_id"),
        "workflow_checkpoints",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_workflow_checkpoints_workflow_version",
        "workflow_checkpoints",
        ["tenant_id", "workflow_id", "version"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema removing workflow instances and checkpoints tables."""
    op.drop_table("workflow_checkpoints")
    op.drop_table("workflow_instances")
