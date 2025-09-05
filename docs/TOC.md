---
title: Documentation Table of Contents
owner: Documentation Team
last_updated: 2025-09-01
status: authoritative
---

# Documentation Table of Contents

> **Complete navigation for MultiDB Therapeutic AI Chatbot documentation**

## 📖 Getting Started

- **[README.md](../README.md)** - Project overview, quick start, and service directory
- **[ARCHITECTURE.md](architecture/ARCHITECTURE.md)** - System architecture and design decisions
- **[GLOSSARY.md](GLOSSARY.md)** - Technical terms and healthcare terminology
- **[CHANGELOG.md](CHANGELOG.md)** - System evolution and version history

## 🏗️ Architecture & Design

### System Architecture
- **[ARCHITECTURE.md](architecture/ARCHITECTURE.md)** - Complete system architecture with C4 diagrams
- **[DIAGRAMS.md](DIAGRAMS.md)** - Comprehensive system diagrams and flowcharts
- **[00_System_Architecture_Overview.md](00_System_Architecture_Overview.md)** - Legacy architecture overview
- **[04_Microservices_Architecture.md](04_Microservices_Architecture.md)** - Microservices design patterns

### Data & AI Systems
- **[01_RAG_Implementation.md](01_RAG_Implementation.md)** - Retrieval-augmented generation pipeline
- **[02_AI_Model_Quality.md](ai/AI_Model_Quality.md)** - Model selection and evaluation metrics
- **[03_Data_Stores_and_Schemas.md](architecture/Data_Stores_and_Schemas.md)** - Multi-database architecture
- **[05_Performance_and_Caching.md](architecture/Performance_and_Caching.md)** - Performance optimization strategies

## 🔒 Security & Compliance

### HIPAA Compliance
- **[compliance/HIPAA_Controls_Matrix.md](compliance/HIPAA_Controls_Matrix.md)** - Technical safeguards mapping
- **[compliance/PHI_Data_Inventory.md](compliance/PHI_Data_Inventory.md)** - Protected health information inventory
- **[compliance/Audit_Trail_Guide.md](compliance/Audit_Trail_Guide.md)** - Audit logging implementation
- **[compliance/Consent_Management.md](compliance/Consent_Management.md)** - Patient consent workflows
- **[08_HIPAA_Compliance_Controls.md](08_HIPAA_Compliance_Controls.md)** - Legacy compliance documentation

### Security Architecture
- **[security/Security_Architecture.md](security/Security_Architecture.md)** - Authentication and authorization
- **[security/Threat_Model.md](security/Threat_Model.md)** - Threat assessment and mitigations
- **[security/Encryption_Standards.md](security/Encryption_Standards.md)** - Cryptographic implementations
- **[security/Access_Control_Model.md](security/Access_Control_Model.md)** - Role-based access control
- **[07_Security_Architecture.md](07_Security_Architecture.md)** - Legacy security documentation

## 🚀 Operations & Deployment

### Deployment & Infrastructure
- **[operations/Deployment_Guide.md](operations/Deployment_Guide.md)** - Production deployment procedures
- **[operations/Runbooks.md](operations/Runbooks.md)** - Incident response and troubleshooting
- **[operations/Monitoring_and_Alerting.md](operations/Monitoring_and_Alerting.md)** - Observability setup
- **[operations/Backup_and_Recovery.md](operations/Backup_and_Recovery.md)** - Data protection procedures
- **[06_Infrastructure_and_IaC.md](Infrastructure_and_IaC.md)** - Infrastructure as Code guide

## 🤖 AI & Machine Learning

### AI Architecture
- **[ai/AI_Architecture.md](ai/AI_Architecture.md)** - Model registry and evaluation strategy
- **[ai/RAG_Pipeline.md](ai/RAG_Pipeline.md)** - Retrieval-augmented generation implementation
- **[ai/Safety_and_Therapeutic_Guards.md](ai/Safety_and_Therapeutic_Guards.md)** - Safety filters and crisis detection

### AI Services Documentation
- **[ai_services/README.md](../ai_services/README.md)** - Python AI services overview
- **[ai_services/core/README.md](../ai_services/core/README.md)** - Core AI service components
- **[ai_services/ingestion_pipeline/README.md](../ai_services/ingestion_pipeline/README.md)** - Document ingestion pipeline
- **[host_services/README.md](../host_services/README.md)** - GPU-accelerated AI host services

## 🐹 Microservices Documentation

### Core Business Services
- **[microservices/api-gateway/README.md](../microservices/api-gateway/README.md)** - Request routing and load balancing
- **[microservices/auth-rbac/README.md](../microservices/auth-rbac/README.md)** - Authentication and RBAC
- **[microservices/chat-history/README.md](../microservices/chat-history/README.md)** - Conversation storage
- **[microservices/consent/README.md](../microservices/consent/README.md)** - HIPAA consent management

### Healthcare Services
- **[microservices/content-safety/README.md](../microservices/content-safety/README.md)** - PHI detection and safety
- **[microservices/audit-logging/README.md](../microservices/audit-logging/README.md)** - Compliance audit trails
- **[microservices/emergency-access/README.md](../microservices/emergency-access/README.md)** - Emergency protocols
- **[microservices/relationship-management/README.md](../microservices/relationship-management/README.md)** - Patient relationships

### Business Services
- **[microservices/billing/README.md](../microservices/billing/README.md)** - Usage tracking and billing
- **[microservices/user-subscription/README.md](../microservices/user-subscription/README.md)** - Subscription management
- **[microservices/background-tasks/README.md](../microservices/background-tasks/README.md)** - Async task processing

## 💼 Business Context

### Strategic Documentation
- **[Business_Value_Proposition.md](Business_Value_Proposition.md)** - ROI and competitive analysis
- **[Internal_Product_Roadmap.md](Internal_Product_Roadmap.md)** - 18-month strategic roadmap
- **[09_Strategic_Technology_Roadmap.md](Strategic_Technology_Roadmap.md)** - Technology evolution plan

### Product Documentation  
- **[ai_persona_schema.md](ai_persona_schema.md)** - AI personality and behavior configuration
- **[Senior Care Enhancement.md](Senior Care Enhancement.md)** - Senior care product features
- **[Senior Empathic Companion v1.md](Senior Empathic Companion v1.md)** - Therapeutic companion specifications

### Market Context
- **[business-context/lilo-customer-bvp.md](business-context/lilo-customer-bvp.md)** - Customer value proposition
- **[business-context/lilo-investor-bvp.md](business-context/lilo-investor-bvp.md)** - Investor presentation materials
- **[business-context/lilo-sales-bvp.md](business-context/lilo-sales-bvp.md)** - Sales enablement materials

## 🧪 Testing & Quality

### Testing Framework
- **[../TESTING_GUIDE.md](../TESTING_GUIDE.md)** - Comprehensive testing framework
- **[../tests/README.md](../tests/README.md)** - Test structure and execution
- **[../tests/integration/README.md](../tests/integration/README.md)** - Integration test guide

### Quality Assurance
- **[02_AI_Model_Quality.md](ai/AI_Model_Quality.md)** - AI model evaluation and benchmarks
- **[05_Performance_and_Caching.md](architecture/Performance_and_Caching.md)** - Performance testing and optimization

## 🎭 Demo & User Interface

### Demo Documentation
- **[../demo/README.md](../demo/README.md)** - Interactive demo setup and usage
- **[demo_cl.md](demo_cl.md)** - Demo command line interface
- **[sequence_diagrams.md](sequence_diagrams.md)** - User interaction flows

### User Interface
- **[web-ui/User_Guide.md](web-ui/User_Guide.md)** - End-user feature guide
- **[web-ui/ui_implementation_plan.md](web-ui/ui_implementation_plan.md)** - UI development roadmap
- **[web-ui/ui_prd.md](web-ui/ui_prd.md)** - Product requirements document

## 📊 Legacy Documentation

### Historical Context
- **[00_Current_State_Analysis.md](00_Current_State_Analysis.md)** - System analysis snapshot
- **[services.md](services.md)** - Service catalog and descriptions

### Specialized Documentation
- **[Scenario Bank 100 Safe T Policy Graph v1.md](Scenario Bank 100 Safe T Policy Graph v1.md)** - Safety policy scenarios
- **[Senior Empathic Companion 50 Cards.md](Senior Empathic Companion 50 Cards.md)** - Conversation patterns

## 🗂️ Documentation Categories

### By Audience
- **👨‍💻 Developers**: Architecture, AI docs, microservices READMEs
- **🏥 Healthcare Teams**: HIPAA controls, safety guides, user documentation
- **🔧 SRE/DevOps**: Operations, deployment, monitoring guides
- **💼 Business**: Value propositions, roadmaps, market analysis
- **🧪 QA Engineers**: Testing guides, quality documentation

### By Phase
- **📋 Phase 1 (Current)**: All current implementation documentation
- **🔮 Phase 2 (Planned)**: Go microservices migration documentation
- **🚀 Phase 3 (Future)**: Advanced AI and scaling documentation

## 🔍 Quick Navigation

### Most Frequently Accessed
1. **[README.md](../README.md)** - Start here
2. **[ARCHITECTURE.md](architecture/ARCHITECTURE.md)** - System overview
3. **[compliance/HIPAA_Controls_Matrix.md](compliance/HIPAA_Controls_Matrix.md)** - Compliance reference
4. **[operations/Deployment_Guide.md](operations/Deployment_Guide.md)** - Deployment procedures
5. **[ai/RAG_Pipeline.md](ai/RAG_Pipeline.md)** - AI implementation

### By Development Task
- **Setting up development**: README.md → ARCHITECTURE.md → Deployment Guide
- **Understanding compliance**: HIPAA Controls Matrix → PHI Data Inventory → Audit Trail Guide  
- **Working with AI**: AI Architecture → RAG Pipeline → Therapeutic Guards
- **Deploying services**: Deployment Guide → Runbooks → Monitoring Guide
- **Contributing code**: README.md → Testing Guide → relevant service README

---

**Last Updated**: 2025-09-01 | **Maintained By**: Documentation Team | **Review Cycle**: Monthly