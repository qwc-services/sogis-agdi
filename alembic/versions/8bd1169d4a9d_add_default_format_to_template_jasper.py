"""Add default_format to template_jasper

Revision ID: 8bd1169d4a9d
Revises: 1a4af576eaa2
Create Date: 2018-12-05 17:05:17.827647

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8bd1169d4a9d'
down_revision = '1a4af576eaa2'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'default_format' to gdi_knoten.template_jasper
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_jasper
          ADD COLUMN default_format character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'default_format' from gdi_knoten.template_jasper
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_jasper
          DROP COLUMN default_format;
    """)

    conn = op.get_bind()
    conn.execute(sql)
