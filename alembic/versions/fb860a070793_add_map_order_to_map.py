"""Add map_order to map

Revision ID: fb860a070793
Revises: 6a78315cc950
Create Date: 2019-04-24 13:02:35.235673

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb860a070793'
down_revision = '6a78315cc950'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'map_order' to gdi_knoten.map
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.map
          ADD COLUMN map_order integer NOT NULL DEFAULT 0;
        -- set initial order by name
        UPDATE gdi_knoten.map
            SET map_order = rows.row_number - 1
                FROM (
                    SELECT row_number() OVER (ORDER BY title), *
                    FROM gdi_knoten.map
                ) rows
                WHERE rows.gdi_oid = gdi_knoten.map.gdi_oid;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'map_order' from gdi_knoten.map
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.map
          DROP COLUMN map_order;
    """)

    conn = op.get_bind()
    conn.execute(sql)
