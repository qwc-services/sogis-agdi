"""add template_filename to template_info

Revision ID: 1670115c5f8e
Revises: bdbb6f90436b
Create Date: 2018-10-22 17:51:39.264560

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1670115c5f8e'
down_revision = 'bdbb6f90436b'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'template_filename' to gdi_knoten.template_info
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_info
          ADD COLUMN template_filename character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'template_filename' from gdi_knoten.template_info
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_info
          DROP COLUMN template_filename;
    """)

    conn = op.get_bind()
    conn.execute(sql)
