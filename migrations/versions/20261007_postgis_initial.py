"""Initial PostgreSQL/PostGIS schema

Revision ID: 20261007_postgis_initial
Revises: 
Create Date: 2026-10-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = "20261007_postgis_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("source_crs", sa.String(length=50), nullable=True),
        sa.Column("measurement_crs", sa.String(length=50), nullable=True),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_files_filename"), "files", ["filename"], unique=False)
    op.create_index(op.f("ix_files_file_type"), "files", ["file_type"], unique=False)
    op.create_index(op.f("ix_files_source_crs"), "files", ["source_crs"], unique=False)
    op.create_index(op.f("ix_files_measurement_crs"), "files", ["measurement_crs"], unique=False)
    op.create_index(op.f("ix_files_status"), "files", ["status"], unique=False)
    op.create_index(op.f("ix_files_created_at"), "files", ["created_at"], unique=False)
    op.create_index(op.f("ix_files_processed_at"), "files", ["processed_at"], unique=False)

    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("feature_index", sa.Integer(), nullable=False),
        sa.Column("geometry_type", sa.String(length=50), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("geom", Geometry(geometry_type="GEOMETRY", srid=-1, spatial_index=True, dimension=2), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], name="fk_features_file_id_files"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", "feature_index", name="uq_file_feature_index"),
    )
    op.create_index(op.f("ix_features_file_id"), "features", ["file_id"], unique=False)
    op.create_index(op.f("ix_features_feature_index"), "features", ["feature_index"], unique=False)
    op.create_index(op.f("ix_features_geometry_type"), "features", ["geometry_type"], unique=False)

    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("measurement_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], name="fk_measurements_feature_id_features"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_id", "measurement_type", name="uq_feature_measurement_type"),
    )
    op.create_index(op.f("ix_measurements_feature_id"), "measurements", ["feature_id"], unique=False)
    op.create_index(op.f("ix_measurements_measurement_type"), "measurements", ["measurement_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_measurements_measurement_type"), table_name="measurements")
    op.drop_index(op.f("ix_measurements_feature_id"), table_name="measurements")
    op.drop_table("measurements")

    op.drop_index(op.f("ix_features_geometry_type"), table_name="features")
    op.drop_index(op.f("ix_features_feature_index"), table_name="features")
    op.drop_index(op.f("ix_features_file_id"), table_name="features")
    op.drop_table("features")

    op.drop_index(op.f("ix_files_processed_at"), table_name="files")
    op.drop_index(op.f("ix_files_created_at"), table_name="files")
    op.drop_index(op.f("ix_files_status"), table_name="files")
    op.drop_index(op.f("ix_files_measurement_crs"), table_name="files")
    op.drop_index(op.f("ix_files_source_crs"), table_name="files")
    op.drop_index(op.f("ix_files_file_type"), table_name="files")
    op.drop_index(op.f("ix_files_filename"), table_name="files")
    op.drop_table("files")

    op.execute("DROP EXTENSION IF EXISTS postgis;")
