"""Move search metadata into data_set_view

Revision ID: b20eb2663be7
Revises: 3bf03e54e444
Create Date: 2019-07-02 15:48:19.137174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b20eb2663be7'
down_revision = '3bf03e54e444'
branch_labels = None
depends_on = None


def upgrade():
    # add Solr columns to gdi_knoten.data_set_view
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN synonyms character varying;
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN keywords character varying;
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN feature_id_column character varying;
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN facet character varying;
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN filter_word character varying;
        ALTER TABLE gdi_knoten.data_set_view
          ADD COLUMN searchable smallint NOT NULL DEFAULT 0;
    """)

    conn = op.get_bind()
    conn.execute(sql)

    # remove Solr columns from gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN synonyms;
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN keywords;
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN feature_id_column;
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN filter_word;
        ALTER TABLE gdi_knoten.ows_layer
          DROP COLUMN searchable;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    # add Solr columns to gdi_knoten.ows_layer
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN synonyms character varying;
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN keywords character varying;
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN feature_id_column character varying;
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN filter_word character varying;
        ALTER TABLE gdi_knoten.ows_layer
          ADD COLUMN searchable smallint NOT NULL DEFAULT 0;
    """)

    conn = op.get_bind()
    conn.execute(sql)

    # remove Solr columns from gdi_knoten.data_set_view
    sql = sa.sql.text("""
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN synonyms;
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN keywords;
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN feature_id_column;
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN facet;
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN filter_word;
        ALTER TABLE gdi_knoten.data_set_view
          DROP COLUMN searchable;
    """)

    conn = op.get_bind()
    conn.execute(sql)
