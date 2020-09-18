"""add Solr fields to ows_layer

Revision ID: 3bf03e54e444
Revises: fb860a070793
Create Date: 2019-06-27 15:59:26.223241

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3bf03e54e444'
down_revision = 'fb860a070793'
branch_labels = None
depends_on = None


def upgrade():
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


def downgrade():
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
