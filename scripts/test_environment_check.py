#!/usr/bin/env python3
"""
Test Environment Diagnostic Script
==================================
This script verifies that all components needed for AI quality testing are working.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def check_mongodb():
    """Check MongoDB connection and capabilities."""
    logger.info("🔍 Checking MongoDB connection...")

    try:
        from app.database.mongo_connection import init_enhanced_mongo, get_mongo_manager, close_enhanced_mongo

        # Initialize MongoDB
        success = await init_enhanced_mongo()
        if not success:
            logger.error("❌ MongoDB initialization failed")
            return False

        # Get manager and check health
        manager = get_mongo_manager()
        health = await manager.health_check()

        logger.info(f"✅ MongoDB Status: {health.get('status')}")
        logger.info(f"   Connected: {health.get('connected')}")
        logger.info(f"   Database: {health.get('database')}")
        logger.info(f"   Connection Type: {health.get('connection_type')}")
        logger.info(f"   Vector Search: {health.get('vector_search_available')}")

        # Test basic operations
        try:
            docs_coll = manager.documents()
            count = await docs_coll.count_documents({})
            logger.info(f"   Documents collection accessible: {count} documents")
        except Exception as e:
            logger.warning(f"⚠️ Documents collection issue: {e}")

        await close_enhanced_mongo()
        return True

    except Exception as e:
        logger.error(f"❌ MongoDB check failed: {e}")
        return False


async def check_services():
    """Check that all required services can be initialized."""
    logger.info("🔍 Checking service initialization...")

    try:
        from app.dependencies import (
            get_embedding_service,
            get_knowledge_service,
            get_chatbot_service
        )

        # Test embedding service
        logger.info("   Checking embedding service...")
        embedding_service = get_embedding_service()
        if embedding_service:
            logger.info("   ✅ Embedding service initialized")
        else:
            logger.warning("   ⚠️ Embedding service is None")

        # Test knowledge service
        logger.info("   Checking knowledge service...")
        knowledge_service = get_knowledge_service()
        if knowledge_service:
            logger.info("   ✅ Knowledge service initialized")
        else:
            logger.warning("   ⚠️ Knowledge service is None")

        # Test chatbot service
        logger.info("   Checking chatbot service...")
        chatbot_service = get_chatbot_service()
        if chatbot_service:
            logger.info("   ✅ Chatbot service initialized")
        else:
            logger.warning("   ⚠️ Chatbot service is None")

        return True

    except Exception as e:
        logger.error(f"❌ Service check failed: {e}")
        return False


async def check_document_processor():
    """Check that document processing works."""
    logger.info("🔍 Checking document processor...")

    try:
        from app.utils.document_processor import EnhancedDocumentProcessor
        import tempfile

        processor = EnhancedDocumentProcessor()

        # Create a test document
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            # UPDATED: Create a longer test document (>100 chars for minimum chunk size)
            test_content = """This is a test document for processing. It contains multiple sentences 
to ensure it meets the minimum chunk size requirements. The document 
processor should be able to extract and chunk this content successfully.
This additional content ensures we have enough text for proper testing.
The minimum chunk size is 100 characters, so we need sufficient content."""

            test_file.write_text(test_content)

            # Process the document
            chunks = await processor.process_directory(temp_dir)

            if chunks:
                logger.info(f"   ✅ Document processor created {len(chunks)} chunks")
                return True
            else:
                logger.warning("   ⚠️ Document processor returned no chunks")
                return False

    except Exception as e:
        logger.error(f"❌ Document processor check failed: {e}")
        return False


async def run_mini_ai_test():
    """Run a minimal AI pipeline test."""
    logger.info("🔍 Running mini AI pipeline test...")

    try:
        # Initialize MongoDB
        from app.database.mongo_connection import init_enhanced_mongo, close_enhanced_mongo
        await init_enhanced_mongo()

        # Get services
        from app.dependencies import get_embedding_service
        embedding_service = get_embedding_service()

        if not embedding_service:
            logger.error("❌ Embedding service not available")
            return False

        # Test embedding generation
        test_text = "This is a test sentence for embedding generation."
        vector = await embedding_service.embed_query(test_text)

        if vector is not None and len(vector) > 0:
            logger.info(f"   ✅ Generated embedding vector of dimension {len(vector)}")
        else:
            logger.error("   ❌ Failed to generate embedding vector")
            return False

        # Cleanup
        await close_enhanced_mongo()
        return True

    except Exception as e:
        logger.error(f"❌ Mini AI test failed: {e}")
        return False


async def main():
    """Run all diagnostic checks."""
    logger.info("🔬 Starting Test Environment Diagnostics")
    logger.info("=" * 50)

    checks = [
        ("MongoDB Connection", check_mongodb),
        ("Service Initialization", check_services),
        ("Document Processor", check_document_processor),
        ("Mini AI Pipeline", run_mini_ai_test),
    ]

    results = {}

    for check_name, check_func in checks:
        logger.info(f"\n🧪 Running: {check_name}")
        try:
            result = await check_func()
            results[check_name] = result
        except Exception as e:
            logger.error(f"❌ {check_name} failed with exception: {e}")
            results[check_name] = False

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 DIAGNOSTIC SUMMARY")
    logger.info("=" * 50)

    all_passed = True
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {status}: {check_name}")
        if not result:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 ALL CHECKS PASSED!")
        logger.info("✅ Your environment is ready for AI quality testing")
        return 0
    else:
        logger.info("\n⚠️ SOME CHECKS FAILED")
        logger.info("❌ Please address the issues above before running AI quality tests")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)