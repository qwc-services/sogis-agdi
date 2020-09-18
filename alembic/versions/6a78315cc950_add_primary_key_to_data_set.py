"""add primary_key to data_set

Revision ID: 6a78315cc950
Revises: 8bd1169d4a9d
Create Date: 2019-01-21 13:35:33.255636

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a78315cc950'
down_revision = '8bd1169d4a9d'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'primary_key' to gdi_knoten.data_set
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set
          ADD COLUMN primary_key character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'primary_key' from gdi_knoten.data_set
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set DROP COLUMN primary_key;
    """)

    conn = op.get_bind()
    conn.execute(sql)
