"""enterprise_auditing_and_idempotency

Revision ID: 0002_enterprise_auditing
Revises: d60987c4b536
Create Date: 2026-09-27 21:07:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_enterprise_auditing"
down_revision: str | Sequence[str] | None = "d60987c4b536"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to include enterprise auditing, idempotency, and stream buffer."""
    # 1. idempotency_keys table
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        op.f("ix_idempotency_keys_status"),
        "idempotency_keys",
        ["status"],
        unique=False,
    )

    # 2. audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("actor_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("resource_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("resource_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("tokens_consumed", sa.Integer(), nullable=False),
        sa.Column("payload_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("occurred_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_actor_id"),
        "audit_logs",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_event_name"),
        "audit_logs",
        ["event_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_id"),
        "audit_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_resource_id"),
        "audit_logs",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_resource_type"),
        "audit_logs",
        ["resource_type"],
        unique=False,
    )

    # 3. stream_buffer_chunks table
    op.create_table(
        "stream_buffer_chunks",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("stream_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stream_buffer_chunks_sequence_number"),
        "stream_buffer_chunks",
        ["sequence_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stream_buffer_chunks_stream_id"),
        "stream_buffer_chunks",
        ["stream_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_stream_buffer_chunks_stream_id"),
        table_name="stream_buffer_chunks",
    )
    op.drop_index(
        op.f("ix_stream_buffer_chunks_sequence_number"),
        table_name="stream_buffer_chunks",
    )
    op.drop_table("stream_buffer_chunks")

    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_name"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        op.f("ix_idempotency_keys_status"),
        table_name="idempotency_keys",
    )
    op.drop_table("idempotency_keys")
