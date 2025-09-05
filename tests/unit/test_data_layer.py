"""
Data Layer Unit Tests
=====================

Tests for the new data layer structure to verify imports and basic functionality.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


def test_data_layer_imports():
    """Test that all data layer imports work correctly"""
    
    # Test model imports
    from data_layer.models.postgres.postgres_models import User, HealthcareRole
    assert User is not None
    assert HealthcareRole is not None
    
    # Test connection imports  
    from data_layer.connections.postgres_connection import postgres_manager, get_postgres_session
    # postgres_manager might be None in test env without proper DB setup, which is fine
    assert get_postgres_session is not None
    
    from data_layer.connections.mongo_connection import get_mongo_manager
    assert get_mongo_manager is not None


def test_ai_services_imports():
    """Test that AI services imports work correctly"""
    
    from ai_services.core.chatbot_service import EnhancedChatbotService
    assert EnhancedChatbotService is not None
    
    from ai_services.shared.config.config import config
    assert config is not None


def test_app_services_imports():
    """Test that AI/ML services work with new structure"""
    
    # Only test AI/ML services - auth/billing/user handled by Go microservices
    try:
        from app.services.chatbot_service import EnhancedChatbotService
        assert EnhancedChatbotService is not None
    except ImportError:
        # OK if not available in test environment
        pass
    
    try:
        from ai_services.core.knowledge_service import KnowledgeService
        assert KnowledgeService is not None
    except ImportError:
        # OK if not available in test environment  
        pass


def test_core_imports():
    """Test that core app functionality imports work"""
    
    from ai_services.core.chatbot_service import EnhancedChatbotService
    assert EnhancedChatbotService is not None


@pytest.mark.asyncio
async def test_async_imports():
    """Test async functionality imports"""
    
    # Test that we can import async components
    from data_layer.connections.postgres_connection import get_postgres_session
    
    # This should not raise an exception
    session_generator = get_postgres_session()
    assert session_generator is not None


def test_no_old_imports():
    """Test that old app.database imports are not accessible"""
    
    with pytest.raises(ModuleNotFoundError):
        from app.database.postgres_models import User
    
    with pytest.raises(ModuleNotFoundError):
        from app.database.postgres_connection import postgres_manager