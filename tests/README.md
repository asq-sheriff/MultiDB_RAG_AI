# MultiDB-Chatbot Test Suite
=====================

Comprehensive test suite for the MultiDB-Chatbot therapeutic AI system with restructured architecture support.

## 🚀 Quick Start

### Run Default Tests (Recommended)
```bash
# Quick smoke tests with HTML report
python test.py

# Full test suite
python test.py --all

# HIPAA compliance verification
python test.py --hipaa
```

### Advanced Usage
```bash
# Use the full test runner for more options
python scripts/test_runner.py --help

# Performance benchmarking
python scripts/test_runner.py --performance --benchmark

# Generate coverage reports
python scripts/test_runner.py --all --coverage --report
```

## 📁 Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_data_layer.py   # Data layer structure tests
│   ├── test_rbac.py         # Role-based access control tests
│   └── test_hipaa_rbac.py   # HIPAA compliance tests
├── integration/             # Integration tests
│   ├── test_hipaa_cache.py  # HIPAA cache integration (consolidated)
│   ├── test_comprehensive_hipaa_integration.py
│   └── test_therapeutic_ai_integration.py
├── system/                  # System/end-to-end tests
│   ├── test_databases.py    # Database connectivity tests
│   ├── test_ai_quality.py   # AI quality and accuracy tests
│   └── test_api.py          # API endpoint tests
├── performance/             # Performance and benchmark tests
│   └── test_service_benchmarks.py
└── conftest.py             # Shared test configuration
```

## 🎯 Test Categories

### Unit Tests (`--unit`)
- **Purpose**: Test individual components in isolation
- **Duration**: ~5-10 seconds
- **Coverage**: Data layer, RBAC, core services
- **When to run**: After code changes, before commits

### Integration Tests (`--integration`) 
- **Purpose**: Test component interactions and workflows
- **Duration**: ~30-60 seconds  
- **Coverage**: HIPAA compliance, cache integration, service communication
- **When to run**: Before releases, after major changes

### System Tests (`--system`)
- **Purpose**: End-to-end functionality verification
- **Duration**: ~1-3 minutes
- **Coverage**: Database connectivity, AI quality, full user paths
- **When to run**: Before deployment, weekly validation

### Performance Tests (`--performance`)
- **Purpose**: Performance metrics and benchmarking
- **Duration**: ~3-8 minutes
- **Coverage**: Response times, throughput, resource usage
- **When to run**: Before releases, after optimization

### HIPAA Tests (`--hipaa`)
- **Purpose**: Healthcare compliance verification
- **Duration**: ~1-2 minutes
- **Coverage**: PHI protection, audit logging, encryption, consent management
- **When to run**: **REQUIRED** before healthcare deployments

### Security Tests (`--security`)
- **Purpose**: Security audit and penetration testing
- **Duration**: ~2-4 minutes
- **Coverage**: Authentication, authorization, data protection
- **When to run**: Weekly security checks, before releases

## 🏥 HIPAA Compliance Testing

### Critical HIPAA Test Requirements

Before any healthcare deployment, these tests **MUST PASS 100%**:

```bash
# Full HIPAA compliance suite
python scripts/test_runner.py --hipaa --report

# Specific HIPAA categories
python -m pytest tests/integration/test_hipaa_cache.py -v
python -m pytest tests/unit/test_hipaa_rbac.py -v
python -m pytest tests/integration/test_comprehensive_hipaa_integration.py -v
```

### HIPAA Test Coverage
- ✅ PHI Detection and Classification
- ✅ Data Encryption (at rest and in transit)
- ✅ Access Control and Authorization
- ✅ Audit Trail Generation
- ✅ Patient Consent Management
- ✅ Emergency Access Procedures
- ✅ Data Anonymization
- ✅ Breach Detection

## 📊 Test Reporting

### HTML Reports
Generated in `test_reports/` directory with:
- Visual test results dashboard
- Performance metrics and trends
- Coverage analysis
- Failed test details with stack traces

### JSON Reports  
Machine-readable format for CI/CD integration:
```bash
python scripts/test_runner.py --all --json --quiet
```

### Coverage Reports
Code coverage analysis:
```bash
python scripts/test_runner.py --unit --integration --coverage
```

## 🔧 Development Workflows

### Daily Development
```bash
# Quick validation
python test.py

# Focus on specific area
python scripts/test_runner.py --unit --verbose
```

### Pre-Commit
```bash
# Comprehensive check
python test.py --all

# HIPAA check if healthcare code changed
python test.py --hipaa
```

### Pre-Release
```bash  
# Full production readiness
python scripts/test_runner.py --all --performance --coverage --report

# Security audit
python scripts/test_runner.py --security --report
```

### CI/CD Integration
```bash
# Quiet mode with JSON output
python scripts/test_runner.py --all --json --quiet

# Parallel execution for faster CI
python scripts/test_runner.py --unit --integration --json
```

## 🏗️ Test Architecture Updates

### New Restructured Project Support

The test suite has been updated to support the new project structure:

- ✅ **Data Layer**: Tests for `data_layer/` directory structure
- ✅ **AI Services**: Tests for `ai_services/` directory structure  
- ✅ **Go Microservices**: Tests for `microservices/` directory structure
- ✅ **Import Updates**: All import statements updated to new paths
- ✅ **Service Stubs**: Stub implementations for missing services

### Migration from Old Structure

The following changes were made during restructuring:

1. **Consolidated HIPAA Tests**: Multiple redundant HIPAA test files merged into `test_hipaa_cache.py`
2. **Updated Imports**: All `app.database.*` imports changed to `data_layer.*`
3. **Service Stubs**: Added stub implementations for auth/billing/user services
4. **Path Updates**: Test discovery updated for new directory structure

### Test Configuration

Key configuration in `conftest.py`:
- Automatic service initialization with new structure
- Database connection management for restructured data layer
- Fixture management for both old and new components
- Environment variable setup for testing

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes project root
2. **Database Connections**: Check database services are running
3. **Service Dependencies**: Verify Go microservices are available for integration tests
4. **Permission Errors**: Ensure test reports directory is writable

### Debug Mode
```bash
python scripts/test_runner.py --debug --verbose
```

### Environment Setup
```bash
# Required environment variables
export TESTING=true
export USE_REAL_EMBEDDINGS=0
export USE_REAL_GENERATION=0
export RAG_SYNTHETIC_QUERY_EMBEDDINGS=1
```

## 📈 Performance Baselines

Current performance targets:

- **API Response Time**: < 500ms (95th percentile)
- **Database Query Time**: < 100ms (average)
- **Cache Hit Ratio**: > 80%
- **Memory Usage**: < 512MB per service
- **CPU Usage**: < 70% under load

Run benchmarks with:
```bash
python scripts/test_runner.py --performance --benchmark --compare-baseline
```

## 🔒 Security Testing

Security test coverage includes:

- Authentication bypass attempts
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Input validation
- Output sanitization
- Session management

## 📝 Contributing

### Adding New Tests

1. **Choose the right category**: unit/integration/system/performance
2. **Follow naming conventions**: `test_<component>_<functionality>.py`
3. **Use appropriate markers**: `@pytest.mark.hipaa`, `@pytest.mark.security`, etc.
4. **Include docstrings**: Document test purpose and expected behavior
5. **Mock external dependencies**: Use fixtures for database/service mocking

### Test Markers

Available pytest markers:
- `@pytest.mark.hipaa` - HIPAA compliance tests
- `@pytest.mark.security` - Security-focused tests  
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.asyncio` - Async tests

### Example Test
```python
@pytest.mark.hipaa
@pytest.mark.asyncio
async def test_phi_detection_in_cache():
    """Test that PHI is properly detected and encrypted in cache"""
    # Test implementation
    pass
```

---

For questions or issues with the test suite, see the main project documentation or create an issue in the repository.