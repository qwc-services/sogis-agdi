"""Refactor template_data_set

Revision ID: 91befd507f70
Revises: d88f152c25d4
Create Date: 2018-10-18 16:01:16.949229

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91befd507f70'
down_revision = 'd88f152c25d4'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        -- create gdi_knoten.template_ows_layer
        CREATE TABLE gdi_knoten.template_ows_layer (
            gdi_oid_template_jasper bigint NOT NULL,
            gdi_oid_ows_layer bigint NOT NULL,
            CONSTRAINT template_jasper_fk FOREIGN KEY (gdi_oid_template_jasper)
                REFERENCES gdi_knoten.template_jasper (gdi_oid) MATCH FULL
                ON UPDATE CASCADE ON DELETE RESTRICT,
            CONSTRAINT ows_layer_fk FOREIGN KEY (gdi_oid_ows_layer)
                REFERENCES gdi_knoten.ows_layer (gdi_oid) MATCH FULL
                ON UPDATE CASCADE ON DELETE RESTRICT
        );
        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON gdi_knoten.template_ows_layer
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');
        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON gdi_knoten.template_ows_layer
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');

        -- migrate existing gdi_knoten.template_data_set
        INSERT INTO gdi_knoten.template_ows_layer
            (gdi_oid_template_jasper, gdi_oid_ows_layer)
            SELECT ds.gdi_oid_template_jasper, l.gdi_oid
            FROM gdi_knoten.template_data_set ds
            JOIN gdi_knoten.ows_layer_data l ON 
                l.gdi_oid_data_set_view = ds.gdi_oid_data_set_view;

        -- replace gdi_knoten.template_data_set
        DROP TABLE gdi_knoten.template_data_set;

        CREATE TABLE gdi_knoten.template_data_set (
            gdi_oid_template_jasper bigint NOT NULL,
            gdi_oid_data_set bigint NOT NULL,
            CONSTRAINT template_jasper_fk FOREIGN KEY (gdi_oid_template_jasper)
                REFERENCES gdi_knoten.template_jasper (gdi_oid) MATCH FULL
                ON UPDATE CASCADE ON DELETE RESTRICT,
            CONSTRAINT data_set_fk FOREIGN KEY (gdi_oid_data_set)
                REFERENCES gdi_knoten.data_set (gdi_oid) MATCH FULL
                ON UPDATE CASCADE ON DELETE RESTRICT
        );
        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON gdi_knoten.template_data_set
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');
        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON gdi_knoten.template_data_set
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        -- revert gdi_knoten.template_data_set
        DROP TABLE gdi_knoten.template_data_set;

        CREATE TABLE gdi_knoten.template_data_set (
            gdi_oid_template_jasper bigint NOT NULL,
            gdi_oid_data_set_view bigint NOT NULL,
            CONSTRAINT template_jasper_fk FOREIGN KEY (gdi_oid_template_jasper)
                REFERENCES gdi_knoten.template_jasper (gdi_oid) MATCH FULL
                ON UPDATE CASCADE ON DELETE RESTRICT,
            CONSTRAINT data_set_view_fk FOREIGN KEY (gdi_oid_data_set_view)
                REFERENCES gdi_knoten.data_set_view (gdi_oid) MATCH FULL
                ON UPDATE CASCADE ON DELETE RESTRICT
        );
        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON gdi_knoten.template_data_set
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');
        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON gdi_knoten.template_data_set
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');

        -- migrate template_ows_layer back to old template_data_set
        -- NOTE: relations to group layers are lost
        INSERT INTO gdi_knoten.template_data_set
            (gdi_oid_template_jasper, gdi_oid_data_set_view)
            SELECT tl.gdi_oid_template_jasper, dl.gdi_oid_data_set_view
            FROM gdi_knoten.template_ows_layer tl
            JOIN gdi_knoten.ows_layer l ON l.gdi_oid = tl.gdi_oid_ows_layer
            JOIN gdi_knoten.ows_layer_data dl ON dl.gdi_oid = l.gdi_oid
            WHERE l.type = 'data';

        -- remove gdi_knoten.template_ows_layer
        DROP TABLE gdi_knoten.template_ows_layer;
    """)

    conn = op.get_bind()
    conn.execute(sql)
