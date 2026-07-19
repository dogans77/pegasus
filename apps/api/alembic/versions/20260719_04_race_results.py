"""create race results

Revision ID: 20260719_04
Revises: 20260718_03
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260719_04"
down_revision = "20260718_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "race_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id", ondelete="CASCADE"), nullable=False),
        sa.Column("winner_entry_id", sa.Integer(), sa.ForeignKey("race_entries.id"), nullable=False),
        sa.Column("official_order", sa.JSON(), nullable=False),
        sa.Column("official_time", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("race_id", name="uq_race_results_race_id"),
    )
    op.create_index("ix_race_results_race_id", "race_results", ["race_id"])


def downgrade() -> None:
    op.drop_index("ix_race_results_race_id", table_name="race_results")
    op.drop_table("race_results")