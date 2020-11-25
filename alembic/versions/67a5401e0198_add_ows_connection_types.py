"""add ows connection types

Revision ID: 67a5401e0198
Revises: 961f20b3f8e6
Create Date: 2020-11-25 16:37:31.546907

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67a5401e0198'
down_revision = '961f20b3f8e6'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: recreate connection_type, as the following does not work inside
    #       a transaction
    # Manual execution:
    # psql service=soconfig_services -c "ALTER TYPE gdi_knoten.connection_type ADD VALUE 'wms'"
    # psql service=soconfig_services -c "ALTER TYPE gdi_knoten.connection_type ADD VALUE 'wmts'"

    sql = sa.sql.text("""
        ALTER TYPE gdi_knoten.connection_type
          RENAME TO connection_type_old;

        CREATE TYPE gdi_knoten.connection_type AS
          ENUM ('database','directory', 'wms', 'wmts');

        ALTER TABLE gdi_knoten.data_source
          ALTER COLUMN connection_type TYPE gdi_knoten.connection_type
          USING connection_type::text::gdi_knoten.connection_type;

        DROP TYPE gdi_knoten.connection_type_old;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        DELETE FROM gdi_knoten.data_source
          WHERE connection_type IN ('wms', 'wmts');

        ALTER TYPE gdi_knoten.connection_type
          RENAME TO connection_type_old;

        CREATE TYPE gdi_knoten.connection_type AS
          ENUM ('database','directory');

        ALTER TABLE gdi_knoten.data_source
          ALTER COLUMN connection_type TYPE gdi_knoten.connection_type
          USING connection_type::text::gdi_knoten.connection_type;

        DROP TYPE gdi_knoten.connection_type_old;
    """)

    conn = op.get_bind()
    conn.execute(sql)
