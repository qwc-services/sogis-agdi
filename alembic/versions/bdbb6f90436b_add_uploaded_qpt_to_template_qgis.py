"""add uploaded_qpt to template_qgis

Revision ID: bdbb6f90436b
Revises: 7a404c3a7c50
Create Date: 2018-10-22 17:15:35.176402

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdbb6f90436b'
down_revision = '7a404c3a7c50'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'uploaded_qpt' to gdi_knoten.template_qgis
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_qgis
          ADD COLUMN uploaded_qpt character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # remove column 'uploaded_qpt' from gdi_knoten.template_qgis
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_qgis
          DROP COLUMN uploaded_qpt;
    """)

    conn = op.get_bind()
    conn.execute(sql)
