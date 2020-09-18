"""Move dataproduct metadata back to ows_layer

Revision ID: d061b0051d00
Revises: b20eb2663be7
Create Date: 2019-07-04 14:48:49.948806

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd061b0051d00'
down_revision = 'b20eb2663be7'
branch_labels = None
depends_on = None


def upgrade():
    # add Solr columns to gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN synonyms character varying;
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN keywords character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)

    # remove Solr columns from gdi_knoten.data_set_view
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN synonyms;
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN keywords;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # add Solr columns to gdi_knoten.data_set_view
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN synonyms character varying;
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN keywords character varying;
    """)

    conn = op.get_bind()
    conn.execute(sql)

    # remove Solr columns from gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN synonyms;
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN keywords;
    """)

    conn = op.get_bind()
    conn.execute(sql)
