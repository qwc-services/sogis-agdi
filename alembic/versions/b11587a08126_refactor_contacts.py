"""refactor contacts

Revision ID: b11587a08126
Revises: 0a213bde7bdb
Create Date: 2018-03-08 15:08:30.316913

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b11587a08126'
down_revision = '0a213bde7bdb'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        -- replace contact
        CREATE TYPE contacts.contact_type AS ENUM ('person', 'organisation');

        DROP TABLE IF EXISTS contacts.contact CASCADE;
        CREATE TABLE contacts.contact(
            id bigint NOT NULL DEFAULT nextval('contacts.contact_id_seq'::regclass),
            type contacts.contact_type NOT NULL,
            id_organisation bigint,
            name character varying NOT NULL,
            street character varying,
            house_no character varying,
            zip character varying,
            city character varying,
            country_code character(3),
            CONSTRAINT contact_pk PRIMARY KEY (id)
        );

        -- replace person
        DROP SEQUENCE IF EXISTS contacts.person_id_seq CASCADE;

        DROP TABLE IF EXISTS contacts.person CASCADE;
        CREATE TABLE contacts.person(
            id bigint NOT NULL,
            function character varying NOT NULL,
            email character varying,
            phone character varying,
            CONSTRAINT person_pk PRIMARY KEY (id)
        );

        -- replace organisation
        DROP SEQUENCE IF EXISTS contacts.organisation_id_seq CASCADE;

        DROP TABLE IF EXISTS contacts.organisation CASCADE;
        CREATE TABLE contacts.organisation(
            id bigint NOT NULL,
            unit character varying,
            abbreviation character varying,
            CONSTRAINT organisation_pk PRIMARY KEY (id)
        );

        -- update resource_contact
        ALTER TABLE contacts.resource_contact RENAME contact_id_contact TO id_contact;

        -- FK constraints
        ALTER TABLE contacts.contact ADD CONSTRAINT organisation_fk FOREIGN KEY (id_organisation)
            REFERENCES contacts.organisation (id) MATCH FULL
            ON DELETE RESTRICT ON UPDATE CASCADE;

        ALTER TABLE contacts.person ADD CONSTRAINT contact_fk FOREIGN KEY (id)
            REFERENCES contacts.contact (id) MATCH FULL
            ON DELETE CASCADE ON UPDATE CASCADE;

        ALTER TABLE contacts.organisation ADD CONSTRAINT contact_fk FOREIGN KEY (id)
            REFERENCES contacts.contact (id) MATCH FULL
            ON DELETE CASCADE ON UPDATE CASCADE;

        ALTER TABLE contacts.resource_contact ADD CONSTRAINT contact_fk FOREIGN KEY (id_contact)
            REFERENCES contacts.contact (id) MATCH FULL
            ON DELETE RESTRICT ON UPDATE CASCADE;

        -- audit triggers
        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON contacts.contact
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON contacts.contact
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON contacts.person
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON contacts.person
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON contacts.organisation
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON contacts.organisation
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        -- revert contact
        DROP TYPE IF EXISTS contacts.contact_type CASCADE;

        DROP TABLE IF EXISTS contacts.contact CASCADE;
        CREATE TABLE contacts.contact
        (
            contact_id bigint NOT NULL DEFAULT nextval('contacts.contact_id_seq'::regclass),
            street character varying,
            house_no character varying,
            zip character varying,
            city character varying,
            country_code character(3),
            id_organisation bigint,
            id_person bigint,
            CONSTRAINT contact_pk PRIMARY KEY (contact_id)
        );

        -- revert person
        CREATE SEQUENCE contacts.person_id_seq
            INCREMENT BY 1
            MINVALUE 1
            MAXVALUE 9223372036854775807
            START WITH 1
            CACHE 1
            NO CYCLE
            OWNED BY NONE;

        DROP TABLE IF EXISTS contacts.person CASCADE;
        CREATE TABLE contacts.person
        (
            id bigint NOT NULL DEFAULT nextval('contacts.person_id_seq'::regclass),
            name character varying,
            surname character varying,
            telephone_nr character varying,
            e_mail character varying,
            CONSTRAINT person_pk PRIMARY KEY (id)
        );

        -- revert organisation
        CREATE SEQUENCE contacts.organisation_id_seq
            INCREMENT BY 1
            MINVALUE 1
            MAXVALUE 9223372036854775807
            START WITH 1
            CACHE 1
            NO CYCLE
            OWNED BY NONE;

        DROP TABLE IF EXISTS contacts.organisation CASCADE;
        CREATE TABLE contacts.organisation
        (
            id bigint NOT NULL DEFAULT nextval('contacts.organisation_id_seq'::regclass),
            company character varying,
            departement character varying,
            office character varying,
            office_short character varying,
            CONSTRAINT organisation_pk PRIMARY KEY (id)
        );

        -- revert resource_contact
        ALTER TABLE contacts.resource_contact RENAME id_contact TO contact_id_contact;

        -- FK constraints
        ALTER TABLE contacts.contact ADD CONSTRAINT organisation_fk FOREIGN KEY (id_organisation)
              REFERENCES contacts.organisation (id) MATCH FULL
              ON UPDATE CASCADE ON DELETE SET NULL;
        ALTER TABLE contacts.contact ADD CONSTRAINT person_fk FOREIGN KEY (id_person)
              REFERENCES contacts.person (id) MATCH FULL
              ON UPDATE CASCADE ON DELETE SET NULL;

        ALTER TABLE contacts.resource_contact ADD CONSTRAINT contact_fk FOREIGN KEY (contact_id_contact)
            REFERENCES contacts.contact (contact_id) MATCH FULL
            ON DELETE RESTRICT ON UPDATE CASCADE;

        -- audit triggers
        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON contacts.contact
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON contacts.contact
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON contacts.person
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON contacts.person
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_row
            AFTER INSERT OR DELETE OR UPDATE
            ON contacts.organisation
            FOR EACH ROW
            EXECUTE PROCEDURE audit.if_modified_func('true');

        CREATE TRIGGER audit_trigger_stm
            AFTER TRUNCATE
            ON contacts.organisation
            FOR EACH STATEMENT
            EXECUTE PROCEDURE audit.if_modified_func('true');
    """)

    conn = op.get_bind()
    conn.execute(sql)
