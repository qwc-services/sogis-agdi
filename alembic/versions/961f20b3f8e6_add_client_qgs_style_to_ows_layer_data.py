"""Add client QGS style to ows_layer_data

Revision ID: 961f20b3f8e6
Revises: caec883a60f7
Create Date: 2019-07-31 13:05:40.612474

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '961f20b3f8e6'
down_revision = 'caec883a60f7'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer_data
          ADD COLUMN client_qgs_style text;
        ALTER TABLE gdi_knoten.ows_layer_data
          ADD COLUMN uploaded_client_qml character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer_data
          DROP COLUMN client_qgs_style;
        ALTER TABLE gdi_knoten.ows_layer_data
          DROP COLUMN uploaded_client_qml;
    """)

    conn = op.get_bind()
    conn.execute(sql)
