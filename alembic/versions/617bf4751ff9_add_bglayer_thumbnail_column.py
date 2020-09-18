"""Add bglayer thumbnail column

Revision ID: 617bf4751ff9
Revises: b73152a81fe9
Create Date: 2018-04-25 13:21:52.069590

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '617bf4751ff9'
down_revision = 'b73152a81fe9'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'thumbnail_image' to gdi_knoten.background_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.background_layer ADD COLUMN thumbnail_image character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'thumbnail_image' from gdi_knoten.background_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.background_layer DROP COLUMN thumbnail_image;
    """)

    conn = op.get_bind()
    conn.execute(sql)
