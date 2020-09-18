"""Add layer_active column to gdi_knoten.group_layer

Revision ID: d88f152c25d4
Revises: 291ef4b7c45a
Create Date: 2018-08-15 17:20:25.806912

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd88f152c25d4'
down_revision = '291ef4b7c45a'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'layer_active' to gdi_knoten.group_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.group_layer ADD COLUMN layer_active boolean NOT NULL DEFAULT true;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'layer_active' from gdi_knoten.group_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.group_layer DROP COLUMN layer_active;
    """)

    conn = op.get_bind()
    conn.execute(sql)
