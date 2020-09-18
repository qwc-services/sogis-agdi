"""add displayfield attr

Revision ID: 291ef4b7c45a
Revises: 3e13e44bb5cb
Create Date: 2018-07-18 18:16:39.478929

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '291ef4b7c45a'
down_revision = '3e13e44bb5cb'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'displayfield' to gdi_knoten.data_set_view_attributes
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view_attributes ADD COLUMN displayfield boolean NOT NULL DEFAULT false;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'displayfield' from gdi_knoten.data_set_view_attributes
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view_attributes DROP COLUMN displayfield;
    """)

    conn = op.get_bind()
    conn.execute(sql)
