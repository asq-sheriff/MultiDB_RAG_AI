# app/__init__.py
"""
Application initialization with lazy loading to prevent circular imports
"""

import logging

logger = logging.getLogger(__name__)

# Lazy loading for seed_data to prevent circular imports
_seed_main = None
SEED_AVAILABLE = False


def get_seed_main():
    """Lazy load seed_main to avoid circular imports"""
    global _seed_main, SEED_AVAILABLE

    if _seed_main is None:
        try:
            # Import only when needed, not at module load time
            from app.utils.seed_data import main as seed_main_import

            _seed_main = seed_main_import
            SEED_AVAILABLE = True
            logger.info("✅ Seed data module loaded successfully")
        except ImportError as e:
            logger.warning(f"Seed data module not available: {e}")
            SEED_AVAILABLE = False
            _seed_main = None

    return _seed_main


def seed_knowledge_base():
    """Seed knowledge base with lazy loading"""
    import asyncio

    seed_func = get_seed_main()
    if seed_func:
        try:
            return asyncio.run(seed_func())
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            return False
    else:
        logger.error("Seed data module not available")
        return False


def get_sample_questions():
    """Return sample questions for testing"""
    return [
        "What is Redis?",
        "How does Python work?",
        "What is machine learning?",
        "How do I reset my password?",
        "What is the policy for refunds?",
        "How do I contact support?",
    ]


# Export public interface
__all__ = [
    "seed_knowledge_base",
    "get_sample_questions",
    "get_seed_main",
    "SEED_AVAILABLE",
]
