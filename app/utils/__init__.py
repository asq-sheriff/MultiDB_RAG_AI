"""Utils module initialization with lazy loading to prevent circular imports"""

import importlib
import logging

logger = logging.getLogger(__name__)

# Check if document processor is available
try:
    _dp = importlib.import_module("app.utils.document_processor")
    DOCUMENT_PROCESSOR_AVAILABLE = hasattr(_dp, "EnhancedDocumentProcessor")
except Exception:
    DOCUMENT_PROCESSOR_AVAILABLE = False

# Lazy loading for seed_data to prevent circular imports
SEED_AVAILABLE = False
seed_main = None


def get_seed_main():
    """Lazy load seed_main to avoid circular imports"""
    global seed_main, SEED_AVAILABLE

    if seed_main is None:
        try:
            from app.utils.seed_data import main as _seed_main

            seed_main = _seed_main
            SEED_AVAILABLE = True
            logger.info("✅ Seed data module loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import seed_data: {e}")
            SEED_AVAILABLE = False

    return seed_main


def seed_knowledge_base():
    """Seed knowledge base with lazy loading"""
    import asyncio

    main_func = get_seed_main()
    if main_func:
        try:
            return asyncio.run(main_func())
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
    "DOCUMENT_PROCESSOR_AVAILABLE",
    "SEED_AVAILABLE",
]

# Only add seed_main if successfully loaded
if get_seed_main():
    __all__.append("seed_main")
