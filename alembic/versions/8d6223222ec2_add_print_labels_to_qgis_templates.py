"""add print_labels to QGIS templates

Revision ID: 8d6223222ec2
Revises: 155a8af61a14
Create Date: 2018-02-26 13:29:39.609935

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d6223222ec2'
down_revision = '155a8af61a14'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_qgis
            ADD COLUMN print_labels character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_qgis
            DROP COLUMN print_labels;
    """)

    conn = op.get_bind()
    conn.execute(sql)
