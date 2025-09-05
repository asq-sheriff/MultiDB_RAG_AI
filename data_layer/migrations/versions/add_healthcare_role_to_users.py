"""add healthcare role to users

Revision ID: a1b2c3d4e5f6
Revises: 09dbb6e2818c
Create Date: 2025-08-27 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'a1b2c3d4e5f6'
down_revision = '09dbb6e2818c'
branch_labels = None
depends_on = None


def upgrade():
    """Add healthcare_role enum and column to users table"""
    
    # Create healthcare_role enum type
    healthcare_role_enum = postgresql.ENUM(
        'resident',
        'family',
        'care_staff',
        'care_manager', 
        'admin',
        'hp_member',
        'case_manager',
        name='healthcare_role',
        create_type=False
    )
    
    # Check if enum already exists and create if not
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'healthcare_role') THEN
                CREATE TYPE healthcare_role AS ENUM (
                    'resident',
                    'family', 
                    'care_staff',
                    'care_manager',
                    'admin',
                    'hp_member',
                    'case_manager'
                );
            END IF;
        END
        $$;
    """)
    
    # Add healthcare_role column to users table
    op.add_column(
        'users',
        sa.Column(
            'healthcare_role',
            healthcare_role_enum,
            nullable=False,
            server_default="'resident'",
        ),
        schema='auth'
    )
    
    # Create index on healthcare_role for efficient role-based queries
    op.create_index(
        'idx_users_healthcare_role',
        'users',
        ['healthcare_role'],
        schema='auth'
    )


def downgrade():
    """Remove healthcare_role column and enum"""
    
    # Drop the index
    op.drop_index('idx_users_healthcare_role', table_name='users', schema='auth')
    
    # Drop the column
    op.drop_column('users', 'healthcare_role', schema='auth')
    
    # Drop the enum type (only if no other tables use it)
    op.execute("DROP TYPE IF EXISTS healthcare_role")