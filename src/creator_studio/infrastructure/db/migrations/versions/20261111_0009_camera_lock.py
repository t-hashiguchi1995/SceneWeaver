"""Camera Lock Studio P0a persistence."""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0009"
down_revision = "20261023_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "camera_rigs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("frame_json", sa.JSON, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("view_json", sa.JSON, nullable=False),
        sa.Column("anchor_asset_id", sa.String(32), nullable=True),
        sa.Column("background_mask_asset_id", sa.String(32), nullable=True),
        sa.Column("preservation_mode", sa.String(256), nullable=False),
        sa.Column("camera_device_visibility", sa.String(256), nullable=False),
        sa.Column("face_policy", sa.String(256), nullable=False),
        sa.Column("qc_profile_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_camera_rigs_project_id", "camera_rigs", ["project_id"])
    op.create_table(
        "camera_anchors",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("rig_id", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("image_asset_id", sa.String(32), nullable=False),
        sa.Column("bg_mask_asset_id", sa.String(32), nullable=True),
        sa.Column("sha256", sa.String(256), nullable=False),
        sa.Column("face_visibility", sa.String(256), nullable=False),
        sa.Column("face_check_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rig_id", "revision", name="uq_camera_anchor_revision"),
    )
    op.create_index("ix_camera_anchors_rig_id", "camera_anchors", ["rig_id"])
    op.create_table(
        "shot_camera_bindings",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("shot_id", sa.String(32), nullable=False, unique=True),
        sa.Column("rig_id", sa.String(32), nullable=False),
        sa.Column("rig_revision", sa.Integer, nullable=False),
        sa.Column("anchor_asset_sha256", sa.String(256), nullable=False),
        sa.Column("face_policy", sa.String(256), nullable=False),
        sa.Column("subject_motion", sa.String(256), nullable=True),
        sa.Column("subject_distance_class", sa.String(256), nullable=True),
        sa.Column("edit_mask_asset_id", sa.String(32), nullable=True),
        sa.Column("pose_asset_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "camera_qc_reports",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("attempt_id", sa.String(32), nullable=False),
        sa.Column("candidate_asset_id", sa.String(32), nullable=False),
        sa.Column("scores_json", sa.JSON, nullable=False),
        sa.Column("decision", sa.String(256), nullable=False),
        sa.Column("reason_codes_json", sa.JSON, nullable=False),
        sa.Column("version", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_camera_qc_reports_attempt_id", "camera_qc_reports", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_camera_qc_reports_attempt_id", table_name="camera_qc_reports")
    op.drop_table("camera_qc_reports")
    op.drop_table("shot_camera_bindings")
    op.drop_index("ix_camera_anchors_rig_id", table_name="camera_anchors")
    op.drop_table("camera_anchors")
    op.drop_index("ix_camera_rigs_project_id", table_name="camera_rigs")
    op.drop_table("camera_rigs")
