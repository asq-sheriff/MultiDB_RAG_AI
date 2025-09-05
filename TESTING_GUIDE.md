# 🧪 Testing Guide - MultiDB-Chatbot

## Quick Start Commands

### 🚀 Development Workflow
```bash
# Daily development check (3-5 min)
python scripts/test_runner.py --quick

# Before committing code
python scripts/test_runner.py --unit --integration
```

### 🏥 Production Deployment 
```bash
# Complete production readiness check (15-20 min)
python scripts/test_runner.py --all --report

# Healthcare compliance audit (REQUIRED)
python scripts/test_runner.py --hipaa --report
```

### 🔧 Specific Testing

```bash
# Test only Python AI/ML services
python scripts/test_runner.py --unit --system

# Test only Go microservices  
python scripts/test_runner.py --go

# Test Infrastructure-as-Code
python scripts/test_runner.py --terraform --report

# Performance benchmarking
python scripts/test_runner.py --performance --benchmark

# Security audit
python scripts/test_runner.py --security --report
```

## Test Architecture

### Python Tests (AI/ML Focus)
- **Unit Tests**: `tests/unit/` - Core AI/ML service logic
- **System Tests**: `tests/system/` - AI service integration
- **Integration Tests**: `tests/integration/` - Multi-database coordination

### Go Microservices Tests
- **Location**: `microservices/*/` 
- **Coverage**: Auth, billing, HIPAA compliance, user management
- **Runner**: `scripts/run_go_tests.sh`

### Infrastructure Tests (Terraform)
- **Location**: `terraform/local/`
- **Coverage**: IaC validation, container deployment, network setup
- **Runner**: Built into test runner

## Service Boundaries

### ✅ Python Services (Keep)
- `knowledge_service` - RAG/embedding search
- `chatbot_service` - AI text generation  
- `http_clients` - AI service HTTP adapters
- `multi_db_service` - Data coordination only

### ✅ Go Microservices (Direct HTTP calls)
- `auth-rbac` - Authentication & authorization
- `billing` - Subscription & usage tracking
- `user-subscription` - User lifecycle
- `consent` - HIPAA consent management

## Report Outputs

### HTML Reports (`test_reports/`)
- **Location**: `test_report_YYYYMMDD_HHMMSS.html`
- **Use**: Human-readable results with metrics
- **Contains**: Pass/fail status, timing, coverage

### JSON Reports (`test_reports/`)
- **Location**: `test_report_YYYYMMDD_HHMMSS.json` 
- **Use**: CI/CD integration, automated analysis
- **Contains**: Machine-readable test data

### JUnit XML (`test_reports/`)
- **Files**: `junit_*.xml` per test category
- **Use**: IDE integration, CI systems
- **Contains**: Standard test result format

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Fix: Ensure you're in project root
cd /path/to/Lilo_EmotionalAI_Backend
python scripts/test_runner.py
```

**Database Connection Errors**  
```bash
# Fix: Start required services
make services-up
python scripts/test_runner.py --unit  # Skip DB tests
```

**Slow Performance**
```bash  
# Fix: Use quick mode for development
python scripts/test_runner.py --quick
```

### Test Categories Explained

| Category | Purpose | Duration | When to Use |
|----------|---------|----------|-------------|
| `--quick` | Smoke test | 3-5 min | Daily development |
| `--unit` | Core logic | 2-3 min | Before commits |
| `--integration` | Multi-service | 5-10 min | Feature testing |
| `--system` | Full stack | 10-15 min | Release prep |
| `--all` | Production ready | 15-20 min | Before deployment |
| `--hipaa` | Compliance | 5 min | Healthcare deployments |
| `--performance` | Benchmarks | 8 min | After optimization |
| `--terraform` | Infrastructure | 1 min | IaC validation |

## CI/CD Integration

```yaml
# Example GitHub Actions
- name: Run Tests
  run: python scripts/test_runner.py --all --json --quiet
  
- name: Upload Reports  
  uses: actions/upload-artifact@v3
  with:
    path: test_reports/
```