"""knowledge_documents_and_vectors

Revision ID: 0004_knowledge_documents_and_vectors
Revises: 0003_multi_tenant_and_budgets
Create Date: 2026-09-28 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_knowledge_documents_and_vectors"
down_revision: str | Sequence[str] | None = "0003_multi_tenant_and_budgets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to include knowledge documents and vector chunks."""
    # 1. knowledge_documents table
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "content_type",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            server_default="text/plain",
            nullable=False,
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=20),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("total_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_documents_tenant_id"),
        "knowledge_documents",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_documents_tenant_status",
        "knowledge_documents",
        ["tenant_id", "status"],
        unique=False,
    )

    # 2. knowledge_document_chunks table
    op.create_table(
        "knowledge_document_chunks",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("document_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("embedding_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_chunks_tenant_id"),
        "knowledge_document_chunks",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_chunks_tenant_doc",
        "knowledge_document_chunks",
        ["tenant_id", "document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema removing knowledge tables."""
    op.drop_table("knowledge_document_chunks")
    op.drop_table("knowledge_documents")
