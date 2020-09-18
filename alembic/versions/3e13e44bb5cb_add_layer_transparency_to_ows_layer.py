"""add layer_transparency to ows_layer

Revision ID: 3e13e44bb5cb
Revises: 617bf4751ff9
Create Date: 2018-06-13 10:56:45.033977

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e13e44bb5cb'
down_revision = '617bf4751ff9'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'layer_transparency' to gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
            ADD COLUMN layer_transparency smallint NOT NULL DEFAULT 0;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
            DROP COLUMN layer_transparency;
    """)

    conn = op.get_bind()
    conn.execute(sql)
