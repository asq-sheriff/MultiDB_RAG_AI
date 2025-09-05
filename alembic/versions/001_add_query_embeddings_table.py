"""Add query embeddings table for semantic conversation memory

Revision ID: 001_query_embeddings
Revises: 
Create Date: 2025-08-29 17:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers
revision = '001_query_embeddings'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create query embeddings table for semantic conversation memory"""
    
    # Create query_embeddings table
    op.create_table(
        'query_embeddings',
        sa.Column('query_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_embedding', Vector(1024), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        
        # RAG Performance Metrics
        sa.Column('search_results_count', sa.Integer(), nullable=True),
        sa.Column('avg_similarity_score', sa.Float(), nullable=True),
        sa.Column('route_used', sa.String(50), nullable=True),
        sa.Column('response_quality_score', sa.Float(), nullable=True),
        
        # Conversation Context Linking
        sa.Column('conversation_turn', sa.Integer(), nullable=True),
        sa.Column('followup_to_query_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Metadata for analytics
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('embedding_model', sa.String(100), nullable=False, server_default='BAAI/bge-large-en-v1.5'),
        
        # Foreign key for conversation linking
        sa.ForeignKeyConstraint(['followup_to_query_id'], ['query_embeddings.query_id'], ondelete='SET NULL'),
    )
    
    # Create optimized indexes for semantic search
    op.create_index(
        'idx_query_embeddings_vector_cosine',
        'query_embeddings',
        ['query_embedding'],
        postgresql_using='ivfflat',
        postgresql_with={'lists': 100},
        postgresql_ops={'query_embedding': 'vector_cosine_ops'}
    )
    
    # Performance indexes
    op.create_index('idx_query_embeddings_user_timestamp', 'query_embeddings', ['user_id', 'timestamp'])
    op.create_index('idx_query_embeddings_session_turn', 'query_embeddings', ['session_id', 'conversation_turn'])
    op.create_index('idx_query_embeddings_quality', 'query_embeddings', ['response_quality_score'])
    
    # Create conversation_analytics table for aggregated insights
    op.create_table(
        'conversation_analytics',
        sa.Column('analytics_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query_cluster_id', sa.String(50), nullable=False),
        sa.Column('cluster_centroid', Vector(1024), nullable=False),
        sa.Column('cluster_size', sa.Integer(), nullable=False),
        sa.Column('avg_response_quality', sa.Float(), nullable=True),
        sa.Column('most_common_route', sa.String(50), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    
    # Index for user query pattern analysis
    op.create_index('idx_conversation_analytics_user', 'conversation_analytics', ['user_id', 'last_seen'])


def downgrade() -> None:
    """Remove query embeddings tables"""
    op.drop_table('conversation_analytics')
    op.drop_table('query_embeddings')