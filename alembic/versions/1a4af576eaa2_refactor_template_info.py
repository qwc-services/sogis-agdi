"""Refactor template_info

Revision ID: 1a4af576eaa2
Revises: 1670115c5f8e
Create Date: 2018-11-28 11:26:34.911594

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a4af576eaa2'
down_revision = '1670115c5f8e'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        CREATE TYPE gdi_knoten.template_info_type AS ENUM
          ('sql', 'module', 'wms');

        ALTER TABLE gdi_knoten.template_info
          ADD COLUMN info_type gdi_knoten.template_info_type NOT NULL
          DEFAULT 'wms';
        ALTER TABLE gdi_knoten.template_info
          ALTER COLUMN info_type DROP DEFAULT;
        ALTER TABLE gdi_knoten.template_info
          ADD COLUMN info_sql text;
        ALTER TABLE gdi_knoten.template_info
          ADD COLUMN info_module character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.template_info
          DROP COLUMN info_type;
        ALTER TABLE gdi_knoten.template_info
          DROP COLUMN info_sql;
        ALTER TABLE gdi_knoten.template_info
          DROP COLUMN info_module;

        DROP TYPE gdi_knoten.template_info_type;
    """)

    conn = op.get_bind()
    conn.execute(sql)
