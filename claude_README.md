# 🧠 Claude Code Session Management Guide

> **Prescriptive guide for effective session memory management in the MultiDB Therapeutic AI platform**

## Overview

This guide provides detailed instructions for managing Claude Code sessions to ensure continuous memory, efficient development, and proper healthcare compliance tracking for the therapeutic AI platform.

---

## 🎯 **Session Memory Architecture**

### **Automatic Memory System**
Claude Code loads these files automatically at **every session start**:

```
📋 Auto-Loaded Files (via .claude config):
├── CLAUDE.md                              # Main project memory & architecture
├── .claude-context/session-memory.md     # Session-specific discoveries  
├── README.md                              # Project overview & setup
├── Makefile                               # All available commands
├── TESTING_GUIDE.md                       # Testing procedures
├── docs/ARCHITECTURE.md                   # 858-line system design
└── docs/compliance/HIPAA_Controls_Matrix.md # Healthcare compliance
```

### **Requirements Documents (Reference Only)**
These are NOT auto-loaded but contain comprehensive implementation details:
- `docs/reqs/ai_features.md` - 28-week AI implementation roadmap
- `docs/reqs/tech_features.md` - Infrastructure and platform requirements  
- `docs/reqs/features_priority.md` - Master prioritization matrix

---

## 🚀 **Session Startup Protocol**

### **What Happens Automatically**
When you start a new Claude Code session:

1. **Hook Execution**: `./manage-claude-session.sh start` runs automatically
2. **System Health Check**: `make health-check` validates service status
3. **Memory Loading**: All auto-include files load with full project context
4. **Session Initialization**: New session-memory.md created from template

### **What You Should Do (Optional)**
```bash
# 1. Quick project status check (optional)
./manage-claude-session.sh status

# 2. Verify critical services are healthy
make health-check

# 3. Check current branch and recent changes
git status
git log --oneline -5

# 4. Review any active issues from previous session
head -20 .claude-context/session-memory.md
```

### **First Commands to Run**
```bash
# Validate system health (especially for healthcare compliance)
make test-hipaa      # REQUIRED - must pass 100%
make test-quick      # General validation
make health-check    # Service status
```

---

## 💾 **During Session - Memory Management**

### **What to Track in Session Memory**

#### **🚨 ALWAYS Track (BLOCKING Issues)**
These issues **block production deployment** and patient safety:

```bash
# Crisis detection failures
echo "$(date +%H:%M) BLOCKING: Crisis detection system failure - [describe issue]" >> .claude-context/session-memory.md

# HIPAA compliance violations  
echo "$(date +%H:%M) BLOCKING: HIPAA test failure - [specific control violated]" >> .claude-context/session-memory.md

# Patient safety concerns
echo "$(date +%H:%M) BLOCKING: Patient safety issue - [describe risk]" >> .claude-context/session-memory.md

# Production infrastructure failures
echo "$(date +%H:%M) BLOCKING: [Service] down/failing - [impact on patient care]" >> .claude-context/session-memory.md
```

#### **🎯 HIGH Priority (Track When Significant)**
```bash
# Major architecture changes
echo "$(date +%H:%M) CHANGED: MongoDB Atlas → PostgreSQL+pgvector migration - Performance: 9.5x improvement" >> .claude-context/session-memory.md

# Therapeutic AI implementations
echo "$(date +%H:%M) IMPLEMENTED: Agentic RAG Router/Dispatcher - Intent accuracy: 90%+" >> .claude-context/session-memory.md

# UI/UX accessibility improvements
echo "$(date +%H:%M) FIXED: WCAG 2.1 AAA compliance - Senior-friendly interface validated" >> .claude-context/session-memory.md

# Evidence-based module completions
echo "$(date +%H:%M) COMPLETED: Reminiscence Therapy module - Clinical validation: 2-point loneliness reduction" >> .claude-context/session-memory.md
```

#### **💡 MEDIUM Priority (Track When Notable)**
```bash
# Performance improvements
echo "$(date +%H:%M) OPTIMIZED: RAG pipeline latency - <100ms response time achieved" >> .claude-context/session-memory.md

# Clinical validation results
echo "$(date +%H:%M) VALIDATED: Behavioral Activation module - 35% anxiety reduction confirmed" >> .claude-context/session-memory.md
```

### **Use Checkpoints for Major Work**
Create git checkpoints after significant progress:

```bash
# After completing any Priority 1 features
./manage-claude-session.sh checkpoint

# After resolving blocking issues  
./manage-claude-session.sh checkpoint

# Before attempting complex changes
./manage-claude-session.sh checkpoint

# After successful HIPAA compliance validation
./manage-claude-session.sh checkpoint
```

---

## 🔄 **Session End Protocol**

### **What Happens Automatically**
When Claude Code session ends:

1. **Hook Execution**: `./manage-claude-session.sh save` runs automatically
2. **Memory Archival**: Current session-memory.md archived with timestamp
3. **Summary Creation**: Session summary generated with work completed
4. **Template Reset**: New session-memory.md template created

### **Manual Session End (If Needed)**
```bash
# If session ends unexpectedly, manually save
./manage-claude-session.sh save

# Create final checkpoint with all work
./manage-claude-session.sh checkpoint

# Verify memory was saved
ls -la .claude-context/session-*.md
```

---

## 📝 **Session Memory Templates**

### **Quick Logging Aliases**
Add to your shell configuration (`.bashrc` or `.zshrc`):

```bash
# Healthcare-specific session memory shortcuts
alias cs-block='echo "$(date +%H:%M) BLOCKING: " >> .claude-context/session-memory.md && echo "Added blocking issue"'
alias cs-hipaa='echo "$(date +%H:%M) HIPAA: " >> .claude-context/session-memory.md && echo "Added HIPAA compliance issue"'
alias cs-crisis='echo "$(date +%H:%M) CRISIS: " >> .claude-context/session-memory.md && echo "Added crisis detection issue"'
alias cs-ui='echo "$(date +%H:%M) UI: " >> .claude-context/session-memory.md && echo "Added UI/accessibility issue"'
alias cs-ai='echo "$(date +%H:%M) AI: " >> .claude-context/session-memory.md && echo "Added therapeutic AI issue"'
alias cs-fix='echo "$(date +%H:%M) FIXED: " >> .claude-context/session-memory.md && echo "Added fix"'
alias cs-learn='echo "$(date +%H:%M) LEARNED: " >> .claude-context/session-memory.md && echo "Added learning"'

# Session management
alias cs-checkpoint='./manage-claude-session.sh checkpoint'
alias cs-status='./manage-claude-session.sh status'
alias cs-show='tail -20 .claude-context/session-memory.md'

# Quick requirement references
alias reqs='echo "📋 Requirements: docs/reqs/features_priority.md (master priority matrix)"'
alias ai-reqs='echo "🤖 AI Features: docs/reqs/ai_features.md (28-week roadmap)"'
alias tech-reqs='echo "🏗️ Infrastructure: docs/reqs/tech_features.md (platform requirements)"'
```

### **Session Memory Format**
Your `.claude-context/session-memory.md` should follow this structure:

```markdown
# Active Session Memory - MultiDB Therapeutic AI

## ACTIVE ISSUES (Maximum 3)
- [ ] BLOCKING: [Critical issue blocking patient safety/compliance]
- [ ] HIGH: [Important issue affecting core functionality]  
- [ ] MEDIUM: [Enhancement or optimization needed]

## LAST CHANGES (Last 5 modifications)
1. [timestamp] [Major change with files affected]
2. [timestamp] [Important fix or implementation]
3. [timestamp] [Architecture change or optimization]
4. [timestamp] [Therapeutic AI enhancement]
5. [timestamp] [HIPAA/security improvement]

## WORKING CONTEXT
Current Branch: feat/phase1-emotional-ai-foundation
Current Focus: [Priority 1 features from 28-week roadmap]
Failed Tests: [Any failing test categories - especially HIPAA]
Key Discovery: [Major insight or breakthrough]

## NEXT SESSION FOCUS
Primary: [Main task to continue - reference Priority Matrix]
Secondary: [Supporting task or investigation needed]

## CLINICAL OUTCOMES TRACKING
- Loneliness Reduction: [Progress toward 2-point UCLA-3 improvement]
- Anxiety Management: [Progress toward 35% GAD-7 reduction]
- Crisis Detection: [Accuracy and response time improvements]
- UI Accessibility: [WCAG 2.1 AAA compliance status]
```

---

## 🛠️ **Troubleshooting Session Memory**

### **Common Issues & Solutions**

#### **Issue**: Session memory seems lost or incomplete
```bash
# Check if memory files exist
ls -la .claude-context/

# Check recent session archives
ls -la .claude-context/session-*.md

# Verify auto-include configuration
cat .claude | grep -A 10 "auto_include"

# Manual recovery from git history
git log --oneline -10
```

#### **Issue**: HIPAA tests failing consistently  
```bash
# This is BLOCKING - add to session memory immediately
echo "$(date +%H:%M) BLOCKING: HIPAA compliance failure - [specific test/control]" >> .claude-context/session-memory.md

# Investigate specific failure
make test-hipaa --verbose

# Check compliance documentation
cat docs/compliance/HIPAA_Controls_Matrix.md | grep -A 5 "[failing_control]"
```

#### **Issue**: Performance degradation in therapeutic AI
```bash
# Track performance issue
echo "$(date +%H:%M) PERFORMANCE: [specific degradation] - Impact: [patient experience effect]" >> .claude-context/session-memory.md

# Check current SLA targets
cat CLAUDE.md | grep -A 20 "Performance SLA Targets"

# Run performance benchmarks  
make test-performance
```

### **Emergency Recovery Procedures**

#### **Complete Session Memory Loss**
```bash
# 1. Check git history for recent work
git log --oneline -10
git diff HEAD~1 --name-only

# 2. Check archived sessions
ls -t .claude-context/session-*.md | head -3
cat .claude-context/session-$(date +%Y%m%d)*.md

# 3. Rebuild from project status
./manage-claude-session.sh status
make health-check
make test-quick

# 4. Reference current priorities from CLAUDE.md
grep -A 10 "Next Priority Tasks" CLAUDE.md
```

#### **System Health Issues**
```bash
# 1. Check service status
make health-check

# 2. Identify failing services
docker-compose ps
docker-compose logs [failing_service]

# 3. Check for HIPAA compliance issues  
make test-hipaa

# 4. Document in session memory
echo "$(date +%H:%M) BLOCKING: System health issues - [describe impact]" >> .claude-context/session-memory.md
```

---

## 🎯 **Best Practices Summary**

### **✅ DO This Every Session**
1. **Let automation work** - Auto-loading provides comprehensive context
2. **Run HIPAA tests first** - `make test-hipaa` must pass 100%
3. **Track blocking issues immediately** - Patient safety is non-negotiable
4. **Use checkpoints liberally** - After any significant progress
5. **Reference priority matrix** - Follow the 28-week safety-first roadmap

### **✅ DO This When Significant Work Done**
1. **Architecture changes** - Document MongoDB→PostgreSQL migrations, Agentic RAG implementations
2. **Therapeutic validations** - Track clinical outcomes and evidence-based module completions
3. **UI/accessibility improvements** - Document WCAG compliance and senior-friendly enhancements
4. **Performance optimizations** - Track SLA achievements and response time improvements

### **❌ DON'T Track (Already in Documentation)**
1. **Service ports and architecture** - Already in CLAUDE.md
2. **Requirements and roadmaps** - Already in docs/reqs/
3. **Standard commands** - Already in Makefile
4. **HIPAA controls** - Already in compliance documentation
5. **Clinical outcome targets** - Already in requirements documents

### **🚨 ALWAYS Escalate These Issues**
- **HIPAA compliance failures** - Blocking for patient data protection
- **Crisis detection system failures** - Blocking for patient safety  
- **Service health failures** - May impact patient care continuity
- **UI accessibility failures** - Blocking for senior user adoption
- **Performance degradation** - May affect therapeutic effectiveness

---

## 📊 **Session Health Checklist**

Before ending any session, verify:

- [ ] **No BLOCKING issues** left undocumented in session memory
- [ ] **HIPAA tests passing** - `make test-hipaa` returns 100% success
- [ ] **At least one significant change** recorded in session memory  
- [ ] **Next session focus** clearly defined
- [ ] **Checkpoint created** if major work completed
- [ ] **Service health validated** - `make health-check` passing

---

## 🔗 **Quick Reference Links**

**Session Management Commands:**
```bash
./manage-claude-session.sh status    # Check project state
./manage-claude-session.sh checkpoint # Save progress with git commit  
./manage-claude-session.sh test      # Validate system health
./manage-claude-session.sh clean     # Remove old session files
```

**Critical Validation Commands:**
```bash
make test-hipaa        # HIPAA compliance (100% required)
make test-quick        # General validation (3-5 min)
make health-check      # Service health status
make test-performance  # SLA validation
```

**Memory and Context Files:**
- **Main Memory**: `CLAUDE.md` (auto-loaded, comprehensive project context)
- **Session Memory**: `.claude-context/session-memory.md` (session-specific discoveries)
- **Requirements**: `docs/reqs/features_priority.md` (28-week roadmap)
- **Architecture**: `docs/ARCHITECTURE.md` (858-line system design)

---

## 🎯 **The Golden Rule**

> **Focus on safety-first development with comprehensive memory tracking for healthcare compliance**

Your session memory system is designed to support the development of a healthcare-grade therapeutic AI platform. Every session should prioritize:

1. **Patient Safety** - Crisis detection and safety systems
2. **Regulatory Compliance** - HIPAA and healthcare requirements  
3. **Senior Accessibility** - UI/UX for elderly users
4. **Clinical Effectiveness** - Evidence-based therapeutic outcomes
5. **System Reliability** - Enterprise-scale availability and performance

The memory system ensures continuous development context while maintaining focus on the critical path to production deployment of safe, effective therapeutic AI for senior care.

---

*Last Updated: 2025-09-05 | For questions or improvements, update this guide based on session experience*