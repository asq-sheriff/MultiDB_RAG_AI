#!/bin/bash

# AI Quality Test Runner
# This script runs only the AI quality tests to validate the RAG pipeline

echo "🔬 Running AI Quality Tests for RAG Pipeline"
echo "=============================================="

# Set environment variables for testing
export USE_REAL_EMBEDDINGS=1
export USE_REAL_GENERATION=1
export LOG_LEVEL=INFO

# Check if MongoDB is running
echo "📡 Checking MongoDB connection..."
python -c "
import asyncio
import sys
sys.path.append('.')
from app.database.mongo_connection import init_enhanced_mongo, close_enhanced_mongo

async def check_mongo():
    try:
        success = await init_enhanced_mongo()
        if success:
            print('✅ MongoDB is accessible')
            await close_enhanced_mongo()
            return True
        else:
            print('❌ MongoDB connection failed')
            return False
    except Exception as e:
        print(f'❌ MongoDB error: {e}')
        return False

result = asyncio.run(check_mongo())
exit(0 if result else 1)
"

# Check the exit code properly (removed the negation)
if [ $? -eq 0 ]; then
    echo "✅ MongoDB connection verified"
else
    echo "❌ MongoDB is not accessible. Please ensure MongoDB is running."
    echo "💡 Try: docker-compose up mongodb"
    exit 1
fi

# Run the AI quality tests specifically
echo ""
echo "🧪 Running AI Quality Tests..."
echo "==============================="

# Run with verbose output to see test progress
pytest tests/system/test_ai_quality.py \
    -v \
    --tb=short \
    --log-cli-level=INFO \
    --log-cli-format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s' \
    --capture=no

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 AI Quality Tests PASSED!"
    echo "✅ Your RAG pipeline is producing high-quality, accurate results"
    echo ""
    echo "📊 What was tested:"
    echo "   ✔ Document processing and storage"
    echo "   ✔ Embedding generation and storage"
    echo "   ✔ Semantic search and retrieval quality"
    echo "   ✔ Generation faithfulness to source material"
    echo "   ✔ End-to-end pipeline integration"
else
    echo ""
    echo "❌ AI Quality Tests FAILED!"
    echo "🔍 Check the output above for specific failures"
    echo ""
    echo "💡 Common issues:"
    echo "   - MongoDB not properly initialized"
    echo "   - Embedding service not working"
    echo "   - Vector search index missing"
    echo "   - Generation service not available"
    exit 1
fi