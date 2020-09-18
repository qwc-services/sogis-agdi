"""add uploaded_qml to ows_layer_data

Revision ID: f0bd68122aa2
Revises: 91befd507f70
Create Date: 2018-10-19 16:51:40.540437

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0bd68122aa2'
down_revision = '91befd507f70'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'uploaded_qml' to gdi_knoten.ows_layer_data
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer_data
          ADD COLUMN uploaded_qml character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'uploaded_qml' from gdi_knoten.ows_layer_data
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer_data
          DROP COLUMN uploaded_qml;
    """)

    conn = op.get_bind()
    conn.execute(sql)
