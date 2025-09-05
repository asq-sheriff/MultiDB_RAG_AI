"""Add HIPAA-compliant consent framework tables

Revision ID: da4078a66da6
Revises: a1b2c3d4e5f6
Create Date: 2025-08-27 13:34:36.020783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da4078a66da6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add HIPAA-compliant consent framework tables."""
    
    # Create enums
    op.execute("CREATE TYPE accesspurpose AS ENUM ('treatment', 'payment', 'operations', 'emergency', 'patient_request', 'legal_requirement', 'family_care')")
    op.execute("CREATE TYPE relationshiptype AS ENUM ('primary_care', 'specialist', 'consultant', 'emergency_contact', 'spouse', 'child', 'parent', 'sibling', 'guardian', 'power_of_attorney', 'healthcare_proxy', 'authorized_representative')")
    op.execute("CREATE TYPE consentstatus AS ENUM ('pending', 'active', 'expired', 'revoked')")
    
    # Create patient_consents table
    op.create_table('patient_consents',
        sa.Column('consent_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('grantor_id', sa.UUID(), nullable=False),
        sa.Column('grantee_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.Enum('treatment', 'payment', 'operations', 'emergency', 'patient_request', 'legal_requirement', 'family_care', name='accesspurpose'), nullable=False),
        sa.Column('data_types', sa.ARRAY(sa.Text()), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', sa.UUID(), nullable=True),
        sa.Column('consent_document_path', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'active', 'expired', 'revoked', name='consentstatus'), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('consent_id'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grantor_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grantee_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.user_id'], ondelete='SET NULL')
    )
    
    # Create indexes for patient_consents
    op.create_index('idx_patient_consents_patient', 'patient_consents', ['patient_id'])
    op.create_index('idx_patient_consents_grantee', 'patient_consents', ['grantee_id'])
    op.create_index('idx_patient_consents_status', 'patient_consents', ['status'])
    op.create_index('idx_patient_consents_purpose', 'patient_consents', ['purpose'])
    op.create_index('idx_patient_consents_expires', 'patient_consents', ['expires_at'])
    
    # Create treatment_relationships table
    op.create_table('treatment_relationships',
        sa.Column('relationship_id', sa.UUID(), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.Enum('primary_care', 'specialist', 'consultant', 'emergency_contact', 'spouse', 'child', 'parent', 'sibling', 'guardian', 'power_of_attorney', 'healthcare_proxy', 'authorized_representative', name='relationshiptype'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('authorized_by', sa.UUID(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('relationship_id'),
        sa.ForeignKeyConstraint(['provider_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['authorized_by'], ['users.user_id'], ondelete='CASCADE')
    )
    
    # Create indexes for treatment_relationships
    op.create_index('idx_treatment_relationships_provider', 'treatment_relationships', ['provider_id'])
    op.create_index('idx_treatment_relationships_patient', 'treatment_relationships', ['patient_id'])
    op.create_index('idx_treatment_relationships_active', 'treatment_relationships', ['is_active'])
    
    # Create family_relationships table
    op.create_table('family_relationships',
        sa.Column('relationship_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('family_member_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.Enum('primary_care', 'specialist', 'consultant', 'emergency_contact', 'spouse', 'child', 'parent', 'sibling', 'guardian', 'power_of_attorney', 'healthcare_proxy', 'authorized_representative', name='relationshiptype'), nullable=False),
        sa.Column('legal_document_path', sa.Text(), nullable=True),
        sa.Column('authorized_data_types', sa.ARRAY(sa.Text()), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('relationship_id'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_member_id'], ['users.user_id'], ondelete='CASCADE')
    )
    
    # Create indexes for family_relationships
    op.create_index('idx_family_relationships_patient', 'family_relationships', ['patient_id'])
    op.create_index('idx_family_relationships_family', 'family_relationships', ['family_member_id'])
    op.create_index('idx_family_relationships_active', 'family_relationships', ['is_active'])
    
    # Create emergency_access_log table
    op.create_table('emergency_access_log',
        sa.Column('access_id', sa.UUID(), nullable=False),
        sa.Column('accessor_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('emergency_type', sa.Text(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('data_accessed', sa.ARRAY(sa.Text()), nullable=False),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('approved', sa.Boolean(), nullable=True),
        sa.Column('patient_notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('access_id'),
        sa.ForeignKeyConstraint(['accessor_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.user_id'], ondelete='SET NULL')
    )
    
    # Create indexes for emergency_access_log
    op.create_index('idx_emergency_access_accessor', 'emergency_access_log', ['accessor_id'])
    op.create_index('idx_emergency_access_patient', 'emergency_access_log', ['patient_id'])
    op.create_index('idx_emergency_access_time', 'emergency_access_log', ['accessed_at'])
    
    # Create phi_access_log table
    op.create_table('phi_access_log',
        sa.Column('log_id', sa.UUID(), nullable=False),
        sa.Column('accessor_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.Enum('treatment', 'payment', 'operations', 'emergency', 'patient_request', 'legal_requirement', 'family_care', name='accesspurpose'), nullable=False),
        sa.Column('data_types_accessed', sa.ARRAY(sa.Text()), nullable=False),
        sa.Column('consent_id', sa.UUID(), nullable=True),
        sa.Column('relationship_id', sa.UUID(), nullable=True),
        sa.Column('access_granted', sa.Boolean(), nullable=False),
        sa.Column('denial_reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('log_id'),
        sa.ForeignKeyConstraint(['accessor_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['consent_id'], ['patient_consents.consent_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['relationship_id'], ['treatment_relationships.relationship_id'], ondelete='SET NULL')
    )
    
    # Create indexes for phi_access_log (critical for audit performance)
    op.create_index('idx_phi_access_accessor', 'phi_access_log', ['accessor_id'])
    op.create_index('idx_phi_access_patient', 'phi_access_log', ['patient_id'])
    op.create_index('idx_phi_access_time', 'phi_access_log', ['accessed_at'])
    op.create_index('idx_phi_access_granted', 'phi_access_log', ['access_granted'])
    op.create_index('idx_phi_access_purpose', 'phi_access_log', ['purpose'])


def downgrade() -> None:
    """Remove HIPAA-compliant consent framework tables."""
    
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('phi_access_log')
    op.drop_table('emergency_access_log')
    op.drop_table('family_relationships')
    op.drop_table('treatment_relationships')
    op.drop_table('patient_consents')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS accesspurpose")
    op.execute("DROP TYPE IF EXISTS relationshiptype")
    op.execute("DROP TYPE IF EXISTS consentstatus")
