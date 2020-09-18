"""create permalink table

Revision ID: 155a8af61a14
Revises: 
Create Date: 2018-02-23 13:22:23.280217

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '155a8af61a14'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        CREATE TABLE public.permalinks (
            data text,
            key char(10),
            date date,
            PRIMARY KEY(key)
        );
    """)

    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("DROP TABLE public.permalinks;")

    conn = op.get_bind()
    conn.execute(sql)
