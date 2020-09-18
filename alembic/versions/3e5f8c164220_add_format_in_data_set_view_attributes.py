"""Add format in data_set_view_attributes

Revision ID: 3e5f8c164220
Revises: d061b0051d00
Create Date: 2019-07-07 00:17:42.270713

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e5f8c164220'
down_revision = 'd061b0051d00'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'format' to gdi_knoten.data_set_view_attributes
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view_attributes ADD COLUMN format character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'format' from gdi_knoten.data_set_view_attributes
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view_attributes DROP COLUMN format;
    """)

    conn = op.get_bind()
    conn.execute(sql)
