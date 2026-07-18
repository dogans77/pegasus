"""create Pegasus race domain

Revision ID: 20260718_01
Revises:
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260718_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("horses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("country", sa.String(50)), sa.Column("birth_year", sa.Integer()), sa.Column("gender", sa.String(20)), sa.Column("father", sa.String(150)), sa.Column("mother", sa.String(150)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_horses_name", "horses", ["name"])
    op.create_table("tracks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("city", sa.String(80), nullable=False), sa.Column("country", sa.String(2), nullable=False, server_default="TR"), sa.UniqueConstraint("name"))
    op.create_index("ix_tracks_name", "tracks", ["name"])
    op.create_index("ix_tracks_city", "tracks", ["city"])
    for table_name in ("jockeys", "trainers"):
        op.create_table(table_name, sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("country", sa.String(2), nullable=False, server_default="TR"), sa.UniqueConstraint("name"))
        op.create_index(f"ix_{table_name}_name", table_name, ["name"])
    op.create_table("races", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id"), nullable=False), sa.Column("race_date", sa.Date(), nullable=False), sa.Column("race_number", sa.Integer(), nullable=False), sa.Column("scheduled_time", sa.Time()), sa.Column("distance_meters", sa.Integer(), nullable=False), sa.Column("surface", sa.String(32), nullable=False), sa.Column("race_class", sa.String(64)), sa.Column("status", sa.String(24), nullable=False, server_default="scheduled"), sa.UniqueConstraint("track_id", "race_date", "race_number", name="uq_race_program"))
    op.create_index("ix_races_track_id", "races", ["track_id"])
    op.create_index("ix_races_race_date", "races", ["race_date"])
    op.create_table("race_entries", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id", ondelete="CASCADE"), nullable=False), sa.Column("horse_id", sa.Integer(), sa.ForeignKey("horses.id"), nullable=False), sa.Column("jockey_id", sa.Integer(), sa.ForeignKey("jockeys.id")), sa.Column("trainer_id", sa.Integer(), sa.ForeignKey("trainers.id")), sa.Column("program_number", sa.Integer(), nullable=False), sa.Column("barrier", sa.Integer()), sa.Column("weight_kg", sa.Numeric(5, 2)), sa.Column("handicap_rating", sa.Integer()), sa.Column("agf_percent", sa.Numeric(5, 2)), sa.UniqueConstraint("race_id", "program_number", name="uq_race_program_number"))
    op.create_index("ix_race_entries_race_id", "race_entries", ["race_id"])
    op.create_index("ix_race_entries_horse_id", "race_entries", ["horse_id"])
    op.create_table("crawler_runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source", sa.String(64), nullable=False, server_default="tjk"), sa.Column("job_name", sa.String(120), nullable=False), sa.Column("status", sa.String(24), nullable=False, server_default="queued"), sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"), sa.Column("error_message", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("finished_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_table("crawler_runs")
    op.drop_index("ix_race_entries_horse_id", table_name="race_entries")
    op.drop_index("ix_race_entries_race_id", table_name="race_entries")
    op.drop_table("race_entries")
    op.drop_index("ix_races_race_date", table_name="races")
    op.drop_index("ix_races_track_id", table_name="races")
    op.drop_table("races")
    for table_name in ("trainers", "jockeys"):
        op.drop_index(f"ix_{table_name}_name", table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("ix_tracks_city", table_name="tracks")
    op.drop_index("ix_tracks_name", table_name="tracks")
    op.drop_table("tracks")
    op.drop_index("ix_horses_name", table_name="horses")
    op.drop_table("horses")
