# 🏗️ Terraform Infrastructure-as-Code (IaC)

## Overview

This directory contains Terraform configuration for managing the MultiDB-Chatbot local development environment using Infrastructure-as-Code principles.

## 📋 Requirements

- **Terraform** >= 1.0 ([Install Guide](https://learn.hashicorp.com/terraform/getting-started/install))
- **Docker** running locally
- **Git** (for version control)

## 🚀 Quick Start

### 1. First-Time Setup
```bash
# From project root
make terraform-init
```

### 2. Configure Secrets
```bash
# Copy template and add your passwords
cp terraform/local/terraform.tfvars.example terraform/local/terraform.tfvars
edit terraform/local/terraform.tfvars
```

### 3. Plan Infrastructure
```bash
make terraform-plan
```

### 4. Deploy Infrastructure  
```bash
make terraform-apply
```

### 5. Check Status
```bash
make terraform-status
```

## 📁 File Structure

```
terraform/local/
├── main.tf                    # Main Terraform configuration
├── outputs.tf                 # Output definitions  
├── terraform.tfvars.example   # Template for secrets
├── terraform.tfvars          # Your secrets (excluded from Git)
└── README.md                 # This file
```

## 🏗️ Infrastructure Components

### Docker Network
- **Name**: `multidb-chatbot-network`
- **Type**: Bridge network with subnet `172.20.0.0/16`
- **Purpose**: Inter-service communication

### Persistent Volumes
- **PostgreSQL**: `multidb-chatbot-postgres-data`
- **Redis**: `multidb-chatbot-redis-data`  
- **MongoDB**: `multidb-chatbot-mongo-data`
- **ScyllaDB**: `multidb-chatbot-scylla-data[1-3]`

### Container Services
- **PostgreSQL**: `pgvector/pgvector:pg15` on port 5432
- **Redis**: `redis:6-alpine` on port 6379
- **MongoDB**: `mongodb-atlas-local` on port 27017  
- **ScyllaDB**: 3-node cluster on ports 9042-9044

## 🔒 Security & Configuration

### Sensitive Data Management
```bash
# terraform.tfvars (NOT in Git)
project_name = "multidb-chatbot"
postgres_password = "your_secure_password"
mongo_password = "your_secure_password"
```

### Validation
```bash
# Test Terraform configuration
make terraform-test
```

## 📋 Common Commands

| Command | Purpose | Duration |
|---------|---------|----------|
| `make terraform-init` | Initialize Terraform | ~30s |
| `make terraform-plan` | Preview changes | ~10s |
| `make terraform-apply` | Deploy infrastructure | ~60s |
| `make terraform-destroy` | Remove all resources | ~30s |
| `make terraform-status` | Check current state | ~5s |
| `make terraform-test` | Validate configuration | ~15s |

## 🔄 Development Workflow

### Daily Development
```bash
# Start infrastructure
make terraform-apply

# Develop...

# Stop infrastructure  
make terraform-destroy
```

### Infrastructure Updates
```bash
# After changing .tf files
make terraform-plan    # Review changes
make terraform-apply   # Apply changes
```

### Troubleshooting
```bash
# Check Terraform state
cd terraform/local
terraform show

# Force refresh state
terraform refresh

# Import existing resources (if needed)
terraform import docker_container.postgres container_id
```

## 🧪 Testing Integration

The Terraform infrastructure is integrated into the test suite:

```bash
# Test infrastructure separately
python scripts/test_runner.py --terraform

# Include in comprehensive tests
python scripts/test_runner.py --all
```

### Test Coverage
- ✅ Terraform initialization
- ✅ Configuration validation
- ✅ Plan generation (dry-run)
- ✅ Container health checks
- ✅ Network connectivity

## 🚨 Important Notes

1. **Manual Docker Commands Prohibited**: Always use Terraform for infrastructure
2. **Secrets Management**: Never commit `terraform.tfvars` to Git  
3. **State Management**: Terraform state files are excluded from Git
4. **Version Control**: All `.tf` files are committed to Git

## 📈 Benefits

- **Reproducible**: Same environment every time
- **Version Controlled**: Infrastructure changes tracked in Git
- **Secure**: Sensitive data properly managed
- **Validated**: Automated testing of infrastructure
- **Documented**: Clear resource definitions