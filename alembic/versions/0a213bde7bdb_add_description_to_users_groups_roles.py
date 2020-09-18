"""add description to users, groups, roles

Revision ID: 0a213bde7bdb
Revises: cedf1f7f3212
Create Date: 2018-03-07 11:31:35.847861

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a213bde7bdb'
down_revision = 'cedf1f7f3212'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        ALTER TABLE iam.user
            ADD COLUMN description character varying NOT NULL DEFAULT '';
        ALTER TABLE iam.group
            ADD COLUMN description character varying NOT NULL DEFAULT '';
        ALTER TABLE iam.role
            ADD COLUMN description character varying NOT NULL DEFAULT '';
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE iam.user DROP COLUMN description;
        ALTER TABLE iam.group DROP COLUMN description;
        ALTER TABLE iam.role DROP COLUMN description;
    """)

    conn = op.get_bind()
    conn.execute(sql)
