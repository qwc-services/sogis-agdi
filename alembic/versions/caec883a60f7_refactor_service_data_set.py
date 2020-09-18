"""Refactor service_data_set to service_data_product

Revision ID: caec883a60f7
Revises: b15431bdd45d
Create Date: 2019-07-16 13:02:57.734115

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'caec883a60f7'
down_revision = 'b15431bdd45d'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        -- rename column
        ALTER TABLE gdi_knoten.service_data_set
          RENAME gdi_oid_data_set_view TO gdi_oid_data_product;
        -- drop FK constraint
        ALTER TABLE gdi_knoten.service_data_set
          DROP CONSTRAINT data_set_view_fk;
        COMMENT ON COLUMN gdi_knoten.service_data_set.gdi_oid_data_product
          IS 'DataProduct is a GDI Resource from data_set_view or ows_layer_group\nUse this as FK to gdi_resource';
        -- rename table
        ALTER TABLE gdi_knoten.service_data_set
          RENAME TO service_data_product;
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        -- rename column
        ALTER TABLE gdi_knoten.service_data_product
          RENAME gdi_oid_data_product TO gdi_oid_data_set_view;
        -- restore FK constraint
        ALTER TABLE gdi_knoten.service_data_product
          ADD CONSTRAINT data_set_view_fk FOREIGN KEY (gdi_oid_data_set_view)
            REFERENCES gdi_knoten.data_set_view (gdi_oid) MATCH FULL
            ON UPDATE CASCADE ON DELETE RESTRICT;
        COMMENT ON COLUMN gdi_knoten.service_data_product.gdi_oid_data_set_view
          IS '';
        -- rename table
        ALTER TABLE gdi_knoten.service_data_product
          RENAME TO service_data_set;
    """)

    conn = op.get_bind()
    conn.execute(sql)
