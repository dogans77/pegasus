"""create prediction snapshots

Revision ID: 20260718_03
Revises: 20260718_02
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260718_03"
down_revision = "20260718_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("chaos_index", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prediction_snapshots_race_id", "prediction_snapshots", ["race_id"])
    op.create_index("ix_prediction_snapshots_model_version", "prediction_snapshots", ["model_version"])
    op.create_index("ix_prediction_snapshots_generated_at", "prediction_snapshots", ["generated_at"])


def downgrade() -> None:
    op.drop_index("ix_prediction_snapshots_generated_at", table_name="prediction_snapshots")
    op.drop_index("ix_prediction_snapshots_model_version", table_name="prediction_snapshots")
    op.drop_index("ix_prediction_snapshots_race_id", table_name="prediction_snapshots")
    op.drop_table("prediction_snapshots")