"""Add permitted_groups column to permalinks

Revision ID: 2953daf0c4c8
Revises: 67a5401e0198
Create Date: 2026-07-20 10:39:45.475842

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2953daf0c4c8'
down_revision = '67a5401e0198'
branch_labels = None
depends_on = None


def upgrade():
    sql = sa.sql.text("""
        ALTER TABLE public.permalinks
        ADD COLUMN permitted_group text;
    """)
    conn = op.get_bind()
    conn.execute(sql)


def downgrade():
    sql = sa.sql.text("""
        ALTER TABLE public.user_infos
        DROP COLUMN permitted_group;
    """)
    conn = op.get_bind()
    conn.execute(sql)
