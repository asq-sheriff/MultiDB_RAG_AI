# 🏗️ Infrastructure and IaC Guide
> **Terraform Infrastructure-as-Code Implementation**

**Objective**: Complete guide to Infrastructure-as-Code using Terraform for local development and production deployment  
**Audience**: DevOps Engineers, Infrastructure Engineers, System Administrators

---

## 📋 Key Concepts

### Infrastructure-as-Code Mandate
**Policy**: All infrastructure MUST be managed via Terraform. Manual Docker commands are prohibited.
**Benefits**: Reproducible environments, version-controlled infrastructure, automated deployment

### Architecture Pattern
- **Local Development**: Terraform + Docker Provider
- **Production**: Terraform + Cloud Provider (AWS/GCP/Azure)
- **Staging**: Terraform modules with environment-specific variables

---

## 🛠️ Implementation Details

### Terraform Configuration Structure

```
terraform/
├── local/                    # Local development environment
│   ├── main.tf              # Core infrastructure definition
│   ├── outputs.tf           # Connection details and summaries  
│   ├── terraform.tfvars     # Sensitive configuration (excluded from Git)
│   └── terraform.tfvars.example  # Template for secrets
└── production/              # Future: Production environment
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

### Local Development Infrastructure

**Core Resources** (`terraform/local/main.tf`):
```hcl
# Shared network for inter-service communication
resource "docker_network" "multidb_network" {
  name = "${var.project_name}-network"
  driver = "bridge"
  ipam_config {
    subnet = "172.20.0.0/16"
  }
}

# Persistent volumes for data preservation
resource "docker_volume" "postgres_data" {
  name = "${var.project_name}-postgres-data"
}

# Database containers with health checks
resource "docker_container" "postgres" {
  name  = "${var.project_name}-postgres"
  image = "pgvector/pgvector:pg15"
  
  env = [
    "POSTGRES_DB=chatbot_app",
    "POSTGRES_USER=chatbot_user", 
    "POSTGRES_PASSWORD=${var.postgres_password}"
  ]
  
  healthcheck {
    test = ["CMD-SHELL", "pg_isready -U chatbot_user"]
    interval = "10s"
    timeout = "5s" 
    retries = 5
  }
}
```

---

## 🚀 How-To Guide

### First-Time Setup

**1. Install Prerequisites**:
```bash
# Install Terraform
brew install terraform  # macOS
# or download from https://terraform.io/downloads

# Verify installation
terraform --version  # Should be >= 1.0
```

**2. Initialize Infrastructure**:
```bash
# From project root
make terraform-init

# Configure secrets
cp terraform/local/terraform.tfvars.example terraform/local/terraform.tfvars
# Edit terraform.tfvars with your passwords
```

**3. Deploy Infrastructure**:
```bash
# Preview changes
make terraform-plan

# Deploy infrastructure
make terraform-apply

# Verify deployment
make terraform-status
```

### Daily Development Workflow

**Start Development Environment**:
```bash
# Deploy all infrastructure
make terraform-apply

# Check service health
docker ps --filter "label=project=multidb-chatbot"

# Initialize databases
python init_database.py
```

**Stop Development Environment**:
```bash
# Destroy all infrastructure (saves resources)
make terraform-destroy

# Or keep running (faster restart)  
# Infrastructure persists until manually destroyed
```

### Infrastructure Updates

**Modifying Configuration**:
```bash
# After changing .tf files
cd terraform/local

# Preview changes
terraform plan

# Apply changes
terraform apply

# Verify changes
terraform output
```

---

## 📊 Production Deployment Considerations

### Cloud Provider Migration

**AWS Deployment Example**:
```hcl
# terraform/production/main.tf
resource "aws_rds_instance" "postgres" {
  identifier = "${var.project_name}-postgres"
  engine = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"
  
  db_name = "chatbot_app"
  username = "chatbot_user"
  password = var.postgres_password
  
  # HIPAA compliance requirements
  storage_encrypted = true
  backup_retention_period = 7
  backup_window = "03:00-04:00"
  maintenance_window = "sun:04:00-sun:05:00"
  
  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name = aws_db_subnet_group.main.name
}
```

### Security & Compliance

**Encryption at Rest**:
- All volumes encrypted with AES-256
- Database encryption enabled by default
- Key management via cloud provider KMS

**Network Security**:
- Private subnets for databases
- VPC endpoints for service communication
- Security groups with least-privilege access

**Backup Strategy**:
- Automated daily backups with 7-day retention
- Cross-region backup replication  
- Point-in-time recovery capability

---

## 🧪 Testing & Validation

### Infrastructure Tests

**Terraform Validation** (Built into test runner):
```python
# tests/infrastructure/test_terraform.py
async def test_terraform_configuration():
    """Validate Terraform configuration"""
    result = subprocess.run(
        ["terraform", "validate"], 
        cwd="terraform/local",
        capture_output=True
    )
    assert result.returncode == 0

async def test_infrastructure_deployment():
    """Test infrastructure can be deployed"""  
    # Plan should execute without errors
    result = subprocess.run(
        ["terraform", "plan"], 
        cwd="terraform/local",
        capture_output=True
    )
    assert result.returncode == 0
    assert "Error:" not in result.stderr.decode()
```

**Container Health Validation**:
```bash
# Automated health check script
#!/bin/bash
echo "🔍 Validating infrastructure health..."

# Check all containers are running
containers=(postgres mongodb redis scylla-node1 scylla-node2 scylla-node3)
for container in "${containers[@]}"; do
    if docker ps --filter "name=multidb-chatbot-$container" --filter "status=running" | grep -q $container; then
        echo "✅ $container: Running"
    else
        echo "❌ $container: Failed" 
        exit 1
    fi
done

echo "🎉 All infrastructure components healthy!"
```

### Integration with Test Runner

**Running Infrastructure Tests**:
```bash
# Test Terraform configuration only
python scripts/test_runner.py --terraform

# Include infrastructure in comprehensive tests  
python scripts/test_runner.py --all --report

# Makefile integration
make terraform-test
```

---

## 🔧 Configuration Reference

### Environment Variables

```bash
# Terraform Configuration
TF_VAR_project_name=multidb-chatbot
TF_VAR_postgres_password=your_secure_password
TF_VAR_mongo_password=your_mongo_password

# Docker Configuration  
DOCKER_HOST=unix:///var/run/docker.sock
COMPOSE_PROJECT_NAME=multidb-chatbot
COMPOSE_FILE=docker-compose.yml
```

### Resource Limits

**Development Environment**:
```yaml
PostgreSQL: 512MB memory, 1 CPU core
MongoDB: 1GB memory, 2 CPU cores  
Redis: 128MB memory, 0.5 CPU core
ScyllaDB: 750MB memory per node, 1 CPU core each
```

**Production Scaling**:
```yaml
PostgreSQL: 8GB+ memory, 4+ CPU cores
MongoDB: 16GB+ memory, 8+ CPU cores
Redis: 2GB+ memory, 2+ CPU cores  
ScyllaDB: 32GB+ memory per node, 8+ CPU cores each
```

---

## 📚 Best Practices

### Infrastructure as Code Guidelines

1. **Version Everything**: All `.tf` files in Git, `.tfvars` excluded
2. **State Management**: Remote state for production, local state for development
3. **Module Composition**: Reusable modules for different environments
4. **Security First**: Encrypted storage, private networks, least-privilege access

### Development Workflow

1. **Plan Before Apply**: Always run `terraform plan` before `terraform apply`
2. **Incremental Changes**: Small, focused infrastructure changes  
3. **Environment Parity**: Development mirrors production architecture
4. **Automated Testing**: Infrastructure changes trigger automated validation

### Monitoring & Maintenance

1. **Regular State Refresh**: Weekly `terraform refresh` to sync actual infrastructure
2. **Security Scanning**: Terraform security validation in CI/CD
3. **Resource Cleanup**: Automated removal of orphaned resources
4. **Cost Monitoring**: Track infrastructure costs and optimize resource allocation