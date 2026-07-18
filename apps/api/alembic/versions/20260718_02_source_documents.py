"""archive raw TJK source documents

Revision ID: 20260718_02
Revises: 20260718_01
"""
import sqlalchemy as sa
from alembic import op
revision = "20260718_02"
down_revision = "20260718_01"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("source_documents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("provider", sa.String(32), nullable=False, server_default="tjk"), sa.Column("document_type", sa.String(64), nullable=False), sa.Column("source_url", sa.Text(), nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("race_date", sa.Date(), nullable=False), sa.Column("city", sa.String(80), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.UniqueConstraint("source_url"))
    op.create_index("ix_source_documents_race_date", "source_documents", ["race_date"])
    op.create_index("ix_source_documents_city", "source_documents", ["city"])
def downgrade():
    op.drop_index("ix_source_documents_city", table_name="source_documents")
    op.drop_index("ix_source_documents_race_date", table_name="source_documents")
    op.drop_table("source_documents")
