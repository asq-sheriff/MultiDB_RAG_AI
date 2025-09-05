# Integration Tests

This directory contains comprehensive integration tests for the MultiDB Chatbot application, covering all major user paths and system functionality.

## Overview

The integration test suite validates:

- **Document Ingestion Pipeline** - Processing and storing documents from `./data/docs`
- **User Authentication & Management** - Registration, login, and user profile management
- **Search Functionality** - Semantic, keyword, and hybrid search across databases
- **Chat & Conversations** - Message handling, context management, and storage
- **AI Services** - Embedding generation and text generation services
- **Multi-Database Operations** - Cross-database queries and data routing
- **Analytics & Monitoring** - Performance tracking and error reporting
- **Error Handling & Recovery** - Graceful degradation and fault tolerance

## Test Files

### `test_document_ingestion.py`
Comprehensive tests for the document ingestion pipeline:
- **TestBasicIngestion** - MongoDB connectivity and document processing
- **TestMongoDBIngestion** - Database storage, batch operations, and search
- **TestEmbeddingIntegration** - Mock embedding generation and vector operations  
- **TestPerformanceAndScaling** - Performance benchmarks and concurrent operations
- **TestErrorHandlingAndRecovery** - Invalid document handling and connection recovery

### `test_full_user_paths.py` 
End-to-end tests covering all user workflows:
- **TestEnvironmentSetup** - Service health checks and system status
- **TestDocumentIngestion** - Document processing and admin endpoints
- **TestUserAuthFlow** - User registration, login, and authentication
- **TestSearchFunctionality** - All search types with test data
- **TestChatFunctionality** - Chat messages and conversation storage
- **TestAIServices** - Embedding and generation service testing
- **TestAnalyticsAndMonitoring** - Metrics collection and dashboards
- **TestMultiDatabaseOperations** - Hybrid operations and benchmarking
- **TestErrorHandlingAndRecovery** - Error scenarios and timeout handling
- **TestEndToEndWorkflows** - Complete user workflows from start to finish

### `test_seeding.py`
Tests for the seeding pipeline:
- MongoDB connection validation
- Seeding component availability
- Data structure validation after seeding

## Running Tests

### Quick Commands (via Makefile)

```bash
# Quick validation (recommended first)
make test-integration-quick

# Individual test suites
make test-ingestion
make test-user-paths  
make test-seeding

# Comprehensive test suite
make test-integration-all
```

### Direct pytest Commands

```bash
# Run specific test files
pytest tests/integration/test_document_ingestion.py -v
pytest tests/integration/test_full_user_paths.py -v
pytest tests/integration/test_seeding.py -v

# Run specific test classes
pytest tests/integration/test_document_ingestion.py::TestBasicIngestion -v
pytest tests/integration/test_full_user_paths.py::TestSearchFunctionality -v

# Run with custom options
pytest tests/integration/ -v --tb=short --color=yes -x  # Stop on first failure
```

### Using the Test Runner Script

```bash
# Comprehensive test runner with status reporting
./scripts/run_integration_tests.sh all        # All tests
./scripts/run_integration_tests.sh quick      # Quick validation
./scripts/run_integration_tests.sh ingestion  # Document ingestion only
./scripts/run_integration_tests.sh user-paths # User workflows only
./scripts/run_integration_tests.sh seeding    # Seeding pipeline only
```

## Prerequisites

### Required Services
The integration tests require the following services to be running:

```bash
# Start database containers
docker start mongodb-atlas-local chatbot-postgres my-redis

# Verify services are running
docker ps --filter "status=running"
```

### Data Files
The document ingestion tests require data files to be present:

```bash
# Data files should be located at:
./data/docs/
├── Cognitive Stimulation.pdf
├── Conversation Patterns.md
├── Cultural Sensitivity.md
├── Daily Routine Support.pdf
├── Emotional Support.pdf
├── Metadata.md
└── Safety Protocols.md
```

### Environment Configuration
Ensure your `.env` file is configured correctly:

```bash
# MongoDB configuration
MONGO_PASSWORD=example
SEED_DOCS_PATH=./data/docs

# Service endpoints (if testing with external services)
EMBEDDING_SERVICE_URL=http://localhost:8001
GENERATION_SERVICE_URL=http://localhost:8003
```

## Test Results Interpretation

### Success Indicators
- ✅ **Green checkmarks** indicate successful test cases
- **Passed test counts** show how many validations succeeded
- **Performance metrics** demonstrate system capability

### Expected Failures
Some test failures are expected depending on your setup:

- **404 errors** for endpoints not available in your configuration
- **Service unavailable** errors if optional services aren't running
- **Authentication errors** if auth endpoints aren't configured

### Key Metrics
The tests validate several important metrics:

- **Document Processing**: 46+ chunks from 7 healthcare documents
- **Database Operations**: Insert/query performance benchmarks
- **Search Functionality**: Text and vector search capabilities
- **Embedding Generation**: 768-dimensional vectors for semantic search
- **Concurrent Operations**: Multi-threaded ingestion performance

## Test Configuration

### MongoDB Connection
```python
MONGO_URI = "mongodb://root:example@localhost:27017/chatbot_app?authSource=admin&directConnection=true"
```

### Test Collections
Tests use isolated collections to avoid data conflicts:
- `test_ingestion` - For ingestion pipeline tests
- `test_search` - For search functionality tests
- `test_embeddings` - For embedding integration tests

### Performance Thresholds
- **Document Processing**: >10 docs/second for small files
- **Database Insertion**: Batch operations <1 second for 25 documents
- **Query Response**: <100ms for simple queries
- **Concurrent Operations**: 5+ simultaneous database operations

## Troubleshooting

### Common Issues

**MongoDB Connection Failed**
```bash
# Check container status
docker ps | grep mongodb
# Restart if needed
docker restart mongodb-atlas-local
```

**Document Processing Errors**
```bash
# Verify data files exist
ls -la ./data/docs/
# Check permissions
chmod -R 644 ./data/docs/*
```

**Import Errors**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=.
# Or use the Makefile commands which set this automatically
```

**Service Unavailable**
```bash
# Check if services are running on expected ports
netstat -an | grep -E ':(8000|8001|8002|8003)'
# Start services if needed
```

### Debug Mode

Run tests with increased verbosity:

```bash
pytest tests/integration/ -v -s --tb=long --color=yes --log-cli-level=DEBUG
```

### Test Data Cleanup

Tests automatically clean up their data, but if needed:

```bash
# Connect to MongoDB and clean test collections
mongosh "mongodb://root:example@localhost:27017/chatbot_app?authSource=admin"
> db.test_ingestion.deleteMany({})
> db.test_search.deleteMany({})
> db.test_embeddings.deleteMany({})
```

## Development

### Adding New Tests

1. **Follow the existing pattern** - Use similar class and method structure
2. **Include setup/cleanup** - Use pytest fixtures for data management
3. **Test multiple scenarios** - Include success, failure, and edge cases
4. **Add to test runner** - Include new tests in the shell script
5. **Document expected behavior** - Add docstrings and comments

### Test Categories

- **Unit Tests** → `tests/unit/` - Individual component testing
- **Integration Tests** → `tests/integration/` - Multi-component workflows  
- **System Tests** → `tests/system/` - Full system validation
- **Performance Tests** - Included in integration tests as needed

### CI/CD Integration

These tests are designed to be run in CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Integration Tests
  run: |
    make test-integration-quick  # Fast validation
    make test-ingestion         # Core functionality
```

## Continuous Improvement

The integration test suite is continuously improved to:

- **Cover new features** as they're added to the application
- **Improve reliability** by handling edge cases and timeouts
- **Enhance performance** through optimized test execution
- **Increase coverage** of user workflows and error scenarios

For questions or improvements, refer to the main project documentation or create an issue in the repository.