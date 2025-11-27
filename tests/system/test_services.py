#!/usr/bin/env python3
"""Test AI services (embedding and generation)"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def test_embedding_service():
    """Test embedding service"""
    try:
        from app.dependencies import embedding_service

        if not embedding_service:
            print("❌ Embedding: Service not initialized")
            return False

        # Test single embedding
        start = time.time()
        embedding = await embedding_service.embed_query("Test query for embedding")
        elapsed = time.time() - start

        if len(embedding) == 768:
            print(f"✅ Embedding: Working (768D, {elapsed:.2f}s)")
            return True
        else:
            print(f"❌ Embedding: Wrong dimension ({len(embedding)})")
            return False

    except Exception as e:
        print(f"❌ Embedding: {str(e)[:100]}")
        return False


async def test_generation_service():
    """Test generation service"""
    try:
        from app.dependencies import generation_service

        if not generation_service:
            print("❌ Generation: Service not initialized")
            return False

        # Test generation
        start = time.time()
        response = await generation_service.generate(
            "Hello, how are you?", max_tokens=20
        )
        elapsed = time.time() - start

        if response and len(response) > 0:
            print(f"✅ Generation: Working ({elapsed:.2f}s)")
            return True
        else:
            print("❌ Generation: No response")
            return False

    except Exception as e:
        print(f"❌ Generation: {str(e)[:100]}")
        return False


async def test_knowledge_service():
    """Test knowledge/RAG service"""
    try:
        from app.dependencies import knowledge_service

        if not knowledge_service:
            print("❌ Knowledge: Service not initialized")
            return False

        # Test search
        result = await knowledge_service.search_router(
            query="test query", top_k=3, route="auto"
        )

        if result and "results" in result:
            print(f"✅ Knowledge: Working ({len(result['results'])} results)")
            return True
        else:
            print("❌ Knowledge: No results")
            return False

    except Exception as e:
        print(f"❌ Knowledge: {str(e)[:100]}")
        return False


async def test_chatbot_service():
    """Test chatbot service"""
    try:
        from app.dependencies import chatbot_service

        if not chatbot_service:
            print("❌ Chatbot: Service not initialized")
            return False

        # Test chat
        response = await chatbot_service.answer_user_message(
            user_id="test_user", message="Hello"
        )

        if response and "answer" in response:
            print("✅ Chatbot: Working")
            return True
        else:
            print("❌ Chatbot: No response")
            return False

    except Exception as e:
        print(f"❌ Chatbot: {str(e)[:100]}")
        return False


async def main():
    print("\n🤖 AI SERVICE TESTS")
    print("=" * 50)

    results = []
    results.append(await test_embedding_service())
    results.append(await test_generation_service())
    results.append(await test_knowledge_service())
    results.append(await test_chatbot_service())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} services working")
        return 0
    else:
        print(f"⚠️ {passed}/{total} services working")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
