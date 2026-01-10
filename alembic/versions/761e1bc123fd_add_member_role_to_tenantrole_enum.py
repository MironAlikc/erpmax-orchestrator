"""add_member_role_to_tenantrole_enum

Revision ID: 761e1bc123fd
Revises: fe4ccadee6a7
Create Date: 2026-01-11 00:56:53.786280

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "761e1bc123fd"
down_revision: Union[str, None] = "fe4ccadee6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'MEMBER' value to tenantrole enum (uppercase to match existing values)
    op.execute("ALTER TYPE tenantrole ADD VALUE IF NOT EXISTS 'MEMBER'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # This would require recreating the enum type and updating all references
    pass
