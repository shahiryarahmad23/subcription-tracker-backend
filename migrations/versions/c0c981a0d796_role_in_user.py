"""Role_in_User

Revision ID: c0c981a0d796
Revises: 48eaf2e61cea
Create Date: 2026-10-20 20:30:08.954464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0c981a0d796'
down_revision: Union[str, Sequence[str], None] = '48eaf2e61cea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role = sa.Enum('user', 'admin', name='user_role')
    user_role.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'users',
        sa.Column(
            'role',
            user_role,
            server_default='user',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'role')
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)
