"""Add search vector trigger

Revision ID: 002
Revises: 001
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create function to update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION users_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.full_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.email, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER users_search_vector_trigger
        BEFORE INSERT OR UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION users_search_vector_update();
    """)

    # Update existing rows
    op.execute("""
        UPDATE users SET search_vector =
            setweight(to_tsvector('english', COALESCE(full_name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(email, '')), 'B');
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS users_search_vector_trigger ON users;")
    op.execute("DROP FUNCTION IF EXISTS users_search_vector_update();")
