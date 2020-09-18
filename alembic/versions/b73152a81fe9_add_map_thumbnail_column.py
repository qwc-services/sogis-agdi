"""Add map thumbnail column

Revision ID: b73152a81fe9
Revises: b11587a08126
Create Date: 2018-04-25 10:56:13.484217

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b73152a81fe9'
down_revision = 'b11587a08126'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'thumbnail_image' to gdi_knoten.map
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.map ADD COLUMN thumbnail_image character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'thumbnail_image' from gdi_knoten.map
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.map DROP COLUMN thumbnail_image;
    """)

    conn = op.get_bind()
    conn.execute(sql)
