"""add legend_filename to ows_layer

Revision ID: bd0e98ef10bd
Revises: f0bd68122aa2
Create Date: 2018-10-22 13:56:31.136981

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd0e98ef10bd'
down_revision = 'f0bd68122aa2'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'legend_filename' to gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN legend_filename character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'legend_filename' from gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN legend_filename;
    """)

    conn = op.get_bind()
    conn.execute(sql)
