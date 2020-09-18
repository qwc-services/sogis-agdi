"""add uploaded_report to template_jasper

Revision ID: 7a404c3a7c50
Revises: bd0e98ef10bd
Create Date: 2018-10-22 16:23:03.950524

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a404c3a7c50'
down_revision = 'bd0e98ef10bd'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'uploaded_report' to gdi_knoten.template_jasper
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_jasper
          ADD COLUMN uploaded_report character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'uploaded_report' from gdi_knoten.template_jasper
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_jasper
          DROP COLUMN uploaded_report;
    """)

    conn = op.get_bind()
    conn.execute(sql)
