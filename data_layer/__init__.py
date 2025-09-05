"""
Unified Data Layer for Lilo_EmotionalAI_Backend

This module provides unified access to all database systems:
- PostgreSQL (primary OLTP)
- MongoDB (documents + vector search)  
- Redis (high-speed cache)
- ScyllaDB (high-throughput analytics)
"""

# Re-export models for easy access
from .models.postgres.postgres_models import *
from .models.redis.redis_models import *  
from .models.scylla.scylla_models import *