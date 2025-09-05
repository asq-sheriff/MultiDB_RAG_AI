# Lilo_EmotionalAI_Backend Unified Makefile
# =================================
#
# Intuitive development commands for HIPAA-compliant therapeutic AI system.
# Updated for hybrid architecture: Python main API + AI host services + planned Go microservices
#
.PHONY: help setup start stop test clean dev infrastructure health demo

# Colors for terminal output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
CYAN=\033[0;36m
WHITE=\033[1;37m
NC=\033[0m # No Color

# ASCII Art Header
define HEADER
╔════════════════════════════════════════════════════════════════╗
║    🏥 HIPAA-Compliant Therapeutic AI Chatbot (Phase 1)        ║  
║          Hybrid Architecture with Multi-Database RAG          ║
╚════════════════════════════════════════════════════════════════╝
endef
export HEADER

# Default target - show help
all: help

help:
	@echo "$$HEADER"
	@echo ""
	@echo "${CYAN}🚀 QUICK START (New Users):${NC}"
	@echo "${WHITE}  make setup${NC}              🛠️  First-time setup (run this first!)"
	@echo "${WHITE}  make start${NC}              🏃  Start all services (infrastructure + AI)"
	@echo "${WHITE}  make test${NC}               ⚡  Run quick validation tests"
	@echo "${WHITE}  make health${NC}             📊  Check all service health"
	@echo ""
	@echo "${CYAN}🧪 TESTING:${NC}"
	@echo "${WHITE}  make test${NC}               ⚡  Quick smoke tests (3-5 min)"
	@echo "${WHITE}  make test-all${NC}           🧪  Full test suite (15-20 min)"
	@echo "${WHITE}  make test-hipaa${NC}         🏥  HIPAA compliance (REQUIRED)"
	@echo "${WHITE}  make test-ai${NC}            🤖  AI quality benchmarks"
	@echo "${WHITE}  make test-security${NC}      🔒  Security audit tests"
	@echo ""
	@echo "${BLUE}🔧 DEVELOPMENT:${NC}"
	@echo "${WHITE}  make dev${NC}                💻  Start development with auto-reload"
	@echo "${WHITE}  make dev-host${NC}           🖥️  Start GPU host services only"
	@echo "${WHITE}  make validate${NC}           ✅  Validate setup and configuration"
	@echo "${WHITE}  make clean${NC}              🧹  Clean caches and temporary files"
	@echo ""
	@echo "${YELLOW}🏗️ INFRASTRUCTURE:${NC}"
	@echo "${WHITE}  make infrastructure${NC}     🚀  Deploy all infrastructure (Terraform)"
	@echo "${WHITE}  make database${NC}           🗄️  Setup databases and run migrations"
	@echo "${WHITE}  make seed${NC}               🌱  Seed healthcare knowledge base"
	@echo ""
	@echo "${GREEN}🎯 COMMON WORKFLOWS:${NC}"
	@echo "${WHITE}  make demo${NC}               🎭  Interactive therapeutic AI demo"
	@echo "${WHITE}  make reset${NC}              🔄  Complete system reset"
	@echo "${WHITE}  make production-ready${NC}   🚀  Full deployment readiness check"
	@echo ""
	@echo "${CYAN}💡 FIRST TIME? Run: make setup && make infrastructure && make start && make test${NC}"

# =============================================================================
# SETUP AND INITIALIZATION
# =============================================================================

setup:
	@echo "$$HEADER"
	@echo ""
	@echo "${CYAN}🛠️ FIRST-TIME SETUP${NC}"
	@echo "===================="
	@echo ""
	@echo "${YELLOW}📋 Checking system requirements...${NC}"
	@python3 --version || (echo "${RED}❌ Python 3.11+ required${NC}" && exit 1)
	@echo "${GREEN}✅ Python 3 found${NC}"
	@echo ""
	@echo "${YELLOW}📋 Installing dependencies...${NC}"
	@pip install -r requirements.txt
	@echo "${GREEN}✅ Dependencies installed${NC}"
	@echo ""
	@echo "${YELLOW}📋 Setting up configuration...${NC}"
	@if [ ! -f ".env" ]; then \
		cp .env.example .env && echo "${GREEN}✅ .env file created${NC}"; \
	else \
		echo "${BLUE}ℹ️ .env file already exists${NC}"; \
	fi
	@echo ""
	@echo "${YELLOW}📋 Checking Docker...${NC}"
	@docker --version > /dev/null 2>&1 && echo "${GREEN}✅ Docker found${NC}" || echo "${YELLOW}⚠️ Docker required for infrastructure${NC}"
	@echo ""
	@echo "${YELLOW}📋 Checking Terraform...${NC}"
	@terraform --version > /dev/null 2>&1 && echo "${GREEN}✅ Terraform found${NC}" || echo "${YELLOW}⚠️ Terraform required for infrastructure${NC}"
	@echo ""
	@echo "${GREEN}🎉 Setup complete!${NC}"
	@echo ""
	@echo "${CYAN}Next steps:${NC}"
	@echo "  1. ${WHITE}make infrastructure${NC}    - Deploy databases"
	@echo "  2. ${WHITE}make start${NC}             - Start AI services"
	@echo "  3. ${WHITE}make test${NC}              - Validate system"

# =============================================================================
# INFRASTRUCTURE MANAGEMENT (Terraform)
# =============================================================================

infrastructure:
	@echo "${CYAN}🏗️ DEPLOYING INFRASTRUCTURE${NC}"
	@echo "============================"
	@echo ""
	@echo "${YELLOW}📋 Starting Terraform deployment...${NC}"
	@cd terraform/local && terraform init -upgrade
	@cd terraform/local && terraform apply -auto-approve
	@echo ""
	@echo "${GREEN}✅ Infrastructure deployed!${NC}"
	@echo "${BLUE}💡 Use 'make health' to verify database health${NC}"

terraform-init:
	@echo "${YELLOW}🏗️ Initializing Terraform...${NC}"
	@cd terraform/local && terraform init -upgrade
	@echo "${GREEN}✅ Terraform initialized${NC}"

terraform-apply:
	@echo "${YELLOW}🚀 Applying Terraform...${NC}"
	@cd terraform/local && terraform apply
	@echo "${GREEN}✅ Infrastructure deployed${NC}"

terraform-destroy:
	@echo "${RED}💥 Destroying infrastructure...${NC}"
	@cd terraform/local && terraform destroy
	@echo "${GREEN}✅ Infrastructure destroyed${NC}"

terraform-status:
	@echo "${CYAN}📊 INFRASTRUCTURE STATUS${NC}"
	@echo "========================"
	@cd terraform/local && terraform output
	@echo ""
	@echo "${YELLOW}Docker containers:${NC}"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================

database:
	@echo "${CYAN}🗄️ DATABASE SETUP${NC}"
	@echo "=================="
	@echo ""
	@echo "${YELLOW}📋 Running database migrations...${NC}"
	@alembic upgrade head
	@echo "${GREEN}✅ Database schema updated${NC}"
	@echo ""
	@echo "${YELLOW}📋 Testing database connections...${NC}"
	@python init_database.py
	@echo "${GREEN}✅ Database setup complete${NC}"

seed:
	@echo "${CYAN}🌱 SEEDING KNOWLEDGE BASE${NC}"
	@echo "========================="
	@echo ""
	@echo "${YELLOW}📋 Seeding healthcare knowledge base...${NC}"
	@python run_seeding.py
	@echo "${GREEN}✅ Knowledge base seeded${NC}"

# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================

start:
	@echo "${CYAN}🚀 STARTING ALL SERVICES${NC}"
	@echo "========================="
	@echo ""
	@echo "${YELLOW}📋 Starting infrastructure...${NC}"
	@make infrastructure > /dev/null 2>&1 || echo "${BLUE}ℹ️ Infrastructure already running${NC}"
	@echo ""
	@echo "${YELLOW}📋 Starting AI services...${NC}"
	@echo "${BLUE}ℹ️ This will start all services including GPU-accelerated AI models${NC}"
	@python start.py &
	@echo ""
	@echo "${GREEN}✅ All services started!${NC}"
	@echo "${CYAN}💡 Use 'make health' to check service status${NC}"

stop:
	@echo "${CYAN}🛑 STOPPING ALL SERVICES${NC}"
	@echo "========================"
	@echo ""
	@echo "${YELLOW}📋 Stopping Python services...${NC}"
	@pkill -f "python.*start.py" 2>/dev/null || echo "${BLUE}ℹ️ No Python services running${NC}"
	@pkill -f "uvicorn.*ai_services.main" 2>/dev/null || echo "${BLUE}ℹ️ No API Gateway running${NC}"
	@pkill -f "python.*embed_server.py" 2>/dev/null || echo "${BLUE}ℹ️ No BGE server running${NC}"
	@pkill -f "python.*generation_server.py" 2>/dev/null || echo "${BLUE}ℹ️ No Qwen server running${NC}"
	@echo ""
	@echo "${YELLOW}📋 Stopping Docker containers...${NC}"
	@cd terraform/local && terraform destroy -auto-approve > /dev/null 2>&1 || echo "${BLUE}ℹ️ Infrastructure already stopped${NC}"
	@echo ""
	@echo "${GREEN}✅ All services stopped${NC}"

restart: stop start

# =============================================================================
# DEVELOPMENT ENVIRONMENT
# =============================================================================

dev:
	@echo "${CYAN}💻 DEVELOPMENT ENVIRONMENT${NC}"
	@echo "=========================="
	@echo ""
	@echo "${YELLOW}📋 Starting development with auto-reload...${NC}"
	@make infrastructure > /dev/null 2>&1 || echo "${BLUE}ℹ️ Infrastructure check${NC}"
	@echo ""
	@echo "${YELLOW}📋 Starting main API with auto-reload...${NC}"
	@PYTHONPATH=. uvicorn ai_services.main:app --reload --port 8000 --host 0.0.0.0

dev-host:
	@echo "${CYAN}🖥️ GPU HOST SERVICES${NC}"
	@echo "==================="
	@echo ""
	@echo "${YELLOW}📋 Starting GPU-accelerated AI host services...${NC}"
	@echo "${BLUE}ℹ️ Terminal 1: BGE Embedding Server (Port 8008)${NC}"
	@echo "${BLUE}ℹ️ Terminal 2: Qwen Generation Server (Port 8007)${NC}"
	@echo ""
	@echo "${WHITE}Run these in separate terminals:${NC}"
	@echo "cd host_services && python embed_server.py"
	@echo "cd host_services && python generation_server.py"

# =============================================================================
# TESTING FRAMEWORK
# =============================================================================

test:
	@echo "${CYAN}⚡ QUICK VALIDATION${NC}"
	@echo "=================="
	@echo ""
	@echo "${YELLOW}📋 Running quick tests (3-5 minutes)...${NC}"
	@python scripts/test_runner.py --quick
	@echo ""
	@echo "${GREEN}🎉 Quick validation complete!${NC}"

test-all:
	@echo "${CYAN}🧪 COMPREHENSIVE TEST SUITE${NC}"
	@echo "============================"
	@echo ""
	@echo "${YELLOW}📋 Running full test suite (15-20 minutes)...${NC}"
	@echo "${RED}⚠️ This requires all services to be running${NC}"
	@python scripts/test_runner.py --all --report
	@echo ""
	@echo "${GREEN}🎉 Comprehensive testing complete!${NC}"

test-hipaa:
	@echo "${CYAN}🏥 HIPAA COMPLIANCE AUDIT${NC}"
	@echo "========================="
	@echo "${RED}⚠️ CRITICAL: These tests MUST pass 100% for healthcare deployment${NC}"
	@echo ""
	@python scripts/test_runner.py --hipaa --report
	@echo ""
	@echo "${GREEN}✅ HIPAA compliance verified${NC}"

test-ai:
	@echo "${CYAN}🤖 AI QUALITY BENCHMARKS${NC}"
	@echo "========================"
	@echo ""
	@python scripts/test_runner.py --performance --benchmark
	@echo ""
	@echo "${GREEN}✅ AI quality benchmarks complete${NC}"

test-security:
	@echo "${CYAN}🔒 SECURITY AUDIT${NC}"
	@echo "=================="
	@echo ""
	@python scripts/test_runner.py --security --report
	@echo ""
	@echo "${GREEN}✅ Security audit complete${NC}"

# =============================================================================
# HEALTH MONITORING
# =============================================================================

health:
	@echo "${CYAN}📊 SYSTEM HEALTH CHECK${NC}"
	@echo "======================="
	@echo ""
	@echo "${YELLOW}🐳 Database containers:${NC}"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|mongo|redis|scylla)" || echo "${YELLOW}⚠️ No database containers running${NC}"
	@echo ""
	@echo "${YELLOW}🌐 Service endpoints:${NC}"
	@echo "   • Main API Gateway:    http://localhost:8000/health"
	@echo "   • Search Service:      http://localhost:8001/health"  
	@echo "   • BGE Host Service:    http://localhost:8008/health"
	@echo "   • AI Embedding:       http://localhost:8005/health"
	@echo "   • Qwen Host Service:   http://localhost:8007/health"
	@echo "   • AI Generation:      http://localhost:8006/health"
	@echo ""
	@echo "${YELLOW}📊 Quick health test:${NC}"
	@curl -s http://localhost:8000/health 2>/dev/null && echo "${GREEN}✅ Main API healthy${NC}" || echo "${RED}❌ Main API not responding${NC}"

validate:
	@echo "${CYAN}✅ SYSTEM VALIDATION${NC}"
	@echo "===================="
	@echo ""
	@echo "${YELLOW}🔍 Checking project structure...${NC}"
	@[ -d "app" ] && echo "${GREEN}✅ App directory found${NC}" || echo "${RED}❌ App directory missing${NC}"
	@[ -d "host_services" ] && echo "${GREEN}✅ Host services directory found${NC}" || echo "${RED}❌ Host services missing${NC}"
	@[ -d "ai_services" ] && echo "${GREEN}✅ AI services directory found${NC}" || echo "${RED}❌ AI services missing${NC}"
	@[ -d "services" ] && echo "${GREEN}✅ Services directory found${NC}" || echo "${RED}❌ Services directory missing${NC}"
	@[ -d "tests" ] && echo "${GREEN}✅ Tests directory found${NC}" || echo "${RED}❌ Tests directory missing${NC}"
	@[ -d "alembic" ] && echo "${GREEN}✅ Alembic migrations found${NC}" || echo "${RED}❌ Alembic missing${NC}"
	@echo ""
	@echo "${YELLOW}🔍 Checking configuration...${NC}"
	@[ -f ".env" ] && echo "${GREEN}✅ Environment file found${NC}" || echo "${YELLOW}⚠️ .env missing (run 'make setup')${NC}"
	@[ -f "start.py" ] && echo "${GREEN}✅ Service orchestrator found${NC}" || echo "${RED}❌ start.py missing${NC}"
	@[ -f "scripts/test_runner.py" ] && echo "${GREEN}✅ Test runner found${NC}" || echo "${RED}❌ Test runner missing${NC}"
	@echo ""
	@echo "${YELLOW}🔍 Testing Python imports...${NC}"
	@PYTHONPATH=. python -c "from app.database.postgres_models import User; print('${GREEN}✅ Database models work${NC}')" 2>/dev/null || echo "${RED}❌ Database import issues${NC}"
	@echo ""
	@echo "${GREEN}🎯 System validation complete!${NC}"

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

clean:
	@echo "${CYAN}🧹 CLEANING SYSTEM${NC}"
	@echo "==================="
	@echo ""
	@echo "${YELLOW}📋 Cleaning Python caches...${NC}"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "${GREEN}✅ Python caches cleaned${NC}"
	@echo ""
	@echo "${YELLOW}📋 Cleaning test artifacts...${NC}"
	@find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage test_reports/*.xml 2>/dev/null || true
	@echo "${GREEN}✅ Test artifacts cleaned${NC}"

reset:
	@echo "${CYAN}🔄 COMPLETE SYSTEM RESET${NC}"
	@echo "========================="
	@echo ""
	@echo "${YELLOW}⚠️ This will stop all services and reset data${NC}"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@make stop
	@make clean
	@cd terraform/local && terraform destroy -auto-approve
	@docker volume prune -f
	@echo ""
	@echo "${GREEN}✅ System reset complete${NC}"
	@echo "${CYAN}💡 Run 'make infrastructure && make start' to restart${NC}"

# =============================================================================
# DEMO AND PRESENTATION
# =============================================================================

demo:
	@echo "${CYAN}🎭 THERAPEUTIC AI DEMO${NC}"
	@echo "======================"
	@echo ""
	@echo "${YELLOW}📋 Starting interactive demo...${NC}"
	@echo "${BLUE}ℹ️ This will demonstrate therapeutic conversation capabilities${NC}"
	@python simple_gradio_ui.py

production-ready:
	@echo "${CYAN}🚀 PRODUCTION READINESS CHECK${NC}"
	@echo "=============================="
	@echo ""
	@echo "${YELLOW}📋 Step 1: System validation...${NC}"
	@make validate
	@echo ""
	@echo "${YELLOW}📋 Step 2: Comprehensive tests...${NC}"
	@make test-all
	@echo ""
	@echo "${YELLOW}📋 Step 3: HIPAA compliance...${NC}"
	@make test-hipaa
	@echo ""
	@echo "${YELLOW}📋 Step 4: Security audit...${NC}"
	@make test-security
	@echo ""
	@echo "${GREEN}🎉 PRODUCTION READINESS VERIFIED!${NC}"
	@echo "${CYAN}✅ System is ready for healthcare deployment${NC}"

# =============================================================================
# CONVENIENT ALIASES
# =============================================================================

# Common aliases
install: setup
up: start  
down: stop
ps: health
status: health
logs:
	@docker-compose logs -f

# Development aliases  
run: dev
serve: dev
watch: dev

# Testing aliases
test-quick: test
quick: test
full: test-all
hipaa: test-hipaa
security: test-security
ai: test-ai

# Infrastructure aliases
deploy: infrastructure
infra: infrastructure
tf-init: terraform-init
tf-apply: terraform-apply
tf-destroy: terraform-destroy

# =============================================================================
# HELP AND DOCUMENTATION
# =============================================================================

docs:
	@echo "${CYAN}📚 DOCUMENTATION LINKS${NC}"
	@echo "======================"
	@echo ""
	@echo "${YELLOW}🏗️ Architecture & Design:${NC}"
	@echo "   • System Overview:     docs/00_System_Architecture_Overview.md"
	@echo "   • RAG Implementation:  docs/01_RAG_Implementation.md"
	@echo "   • AI Model Quality:    docs/02_AI_Model_Quality.md"
	@echo "   • Data Stores:         docs/03_Data_Stores_and_Schemas.md"
	@echo ""
	@echo "${YELLOW}🔒 Security & Compliance:${NC}"
	@echo "   • Security Architecture: docs/07_Security_Architecture.md"
	@echo "   • HIPAA Controls:        docs/08_HIPAA_Compliance_Controls.md"
	@echo ""
	@echo "${YELLOW}💼 Business Context:${NC}"
	@echo "   • Business Value:      docs/Business_Value_Proposition.md"
	@echo "   • Product Roadmap:     docs/Internal_Product_Roadmap.md"
	@echo "   • User Guide:          docs/User_Guide.md"
	@echo ""
	@echo "${YELLOW}🧪 Development:${NC}"
	@echo "   • Testing Guide:       TESTING_GUIDE.md"
	@echo "   • Development Guide:   DEVELOPMENT.md"
	@echo "   • API Docs:            http://localhost:8000/docs (when running)"

troubleshoot:
	@echo "${CYAN}🔧 TROUBLESHOOTING GUIDE${NC}"
	@echo "========================"
	@echo ""
	@echo "${YELLOW}Common issues and solutions:${NC}"
	@echo ""
	@echo "${WHITE}Issue: Services won't start${NC}"
	@echo "   Solution: make infrastructure && make start"
	@echo ""
	@echo "${WHITE}Issue: Database connection errors${NC}"
	@echo "   Solution: make infrastructure && make database"
	@echo ""
	@echo "${WHITE}Issue: AI services failing${NC}"
	@echo "   Solution: Check GPU support with 'python -c \"import torch; print(torch.backends.mps.is_available())\"'"
	@echo ""
	@echo "${WHITE}Issue: Tests failing${NC}"
	@echo "   Solution: make validate && make health && make test"
	@echo ""
	@echo "${WHITE}Issue: Port conflicts${NC}"
	@echo "   Solution: make stop && make start"
	@echo ""
	@echo "${CYAN}💡 Still stuck? Check docs/00_System_Architecture_Overview.md${NC}"