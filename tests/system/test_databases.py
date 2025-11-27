#!/usr/bin/env python3
"""Test all database connections"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment from .env
from dotenv import load_dotenv

load_dotenv()


async def test_postgresql():
    """Test PostgreSQL connection"""
    try:
        from app.database.postgres_connection import postgres_manager

        await postgres_manager.initialize()

        if await postgres_manager.test_connection():
            async with postgres_manager.get_session() as session:
                result = await session.execute("SELECT COUNT(*) FROM users")
                count = result.scalar()
                print(f"✅ PostgreSQL: Connected (Users: {count})")
                return True
    except Exception as e:
        print(f"❌ PostgreSQL: {str(e)[:100]}")
    return False


async def test_mongodb():
    """Test MongoDB with vector search"""
    try:
        from app.database.mongo_connection import enhanced_mongo_manager

        if not enhanced_mongo_manager.is_connected:
            await enhanced_mongo_manager.connect()

        db = enhanced_mongo_manager.get_database()

        # Test basic connection
        count = await db.embeddings.count_documents({})

        # Test vector search
        test_vector = [0.1] * 768
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_idx_embeddings_embedding",
                    "path": "embedding",
                    "queryVector": test_vector,
                    "numCandidates": 10,
                    "limit": 1,
                }
            }
        ]

        try:
            await db.embeddings.aggregate(pipeline).to_list(1)
            vector_works = True
        except Exception:
            vector_works = False

        print(f"✅ MongoDB: Connected (Docs: {count}, Vector Search: {vector_works})")
        return True
    except Exception as e:
        print(f"❌ MongoDB: {str(e)[:100]}")
    return False


def test_redis():
    """Test Redis connection"""
    try:
        from app.database.redis_connection import redis_manager

        redis_manager.initialize()

        if redis_manager.is_connected:
            redis_manager.client.set("test", "value", ex=5)
            value = redis_manager.client.get("test")
            redis_manager.client.delete("test")

            if value == b"value":
                print("✅ Redis: Connected")
                return True
    except Exception as e:
        print(f"❌ Redis: {str(e)[:100]}")
    return False


def test_scylladb():
    """Test ScyllaDB connection"""
    try:
        from app.database.scylla_connection import scylla_manager

        if not scylla_manager.is_connected():
            scylla_manager.connect()

        session = scylla_manager.get_session()
        result = session.execute("SELECT release_version FROM system.local")
        version = result.one()

        if version:
            print(f"✅ ScyllaDB: Connected (v{version.release_version})")
            return True
    except Exception as e:
        print(f"❌ ScyllaDB: {str(e)[:100]}")
    return False


async def main():
    print("\n🔍 DATABASE CONNECTION TESTS")
    print("=" * 50)

    results = []
    results.append(await test_postgresql())
    results.append(await test_mongodb())
    results.append(test_redis())
    results.append(test_scylladb())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} databases connected")
        return 0
    else:
        print(f"⚠️ {passed}/{total} databases connected")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
