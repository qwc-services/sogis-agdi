"""add title to OWS layers

Revision ID: cedf1f7f3212
Revises: 8d6223222ec2
Create Date: 2018-03-02 10:09:35.781474

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cedf1f7f3212'
down_revision = '8d6223222ec2'
branch_labels = None
depends_on = None


def upgrade():
    # add column 'title' to gdi_knoten.ows_layer with 'name' value as default
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
            ADD COLUMN title character varying;
        UPDATE gdi_knoten.ows_layer SET title = name;
        ALTER TABLE gdi_knoten.ows_layer
            ALTER COLUMN title SET NOT NULL;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
            DROP COLUMN title;
    """)

    conn = op.get_bind()
    conn.execute(sql)
