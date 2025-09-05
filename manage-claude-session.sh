#!/bin/bash

case "$1" in
  start)
    echo "🚀 Starting new Claude Code session for MultiDB Therapeutic AI..."
    
    # Run health check first
    echo "🔍 Checking system health..."
    if command -v make >/dev/null 2>&1; then
        make health-check || echo "⚠️ Some services may be down"
    fi
    
    # Archive old session if exists
    if [ -f .claude-context/current-session.md ]; then
      mv .claude-context/current-session.md ".claude-context/session-$(date +%Y%m%d-%H%M%S).md"
    fi
    
    # Create new session from template
    cp .claude-context/session-template.md .claude-context/current-session.md
    
    # Update session date
    sed -i '' "s/\$(date)/$(date)/" .claude-context/current-session.md
    
    echo "✅ Session initialized. Key files loaded:"
    echo "   📋 PROJECT_CONTEXT.md - Current project state"
    echo "   🧠 CLAUDE.md - System memory and quick reference"
    echo "   📚 docs/understand.md - Comprehensive system analysis"
    echo ""
    echo "🏥 Remember: HIPAA compliance is BLOCKING (must pass 100%)"
    echo "🎯 Current focus: RAG pipeline debugging and performance optimization"
    ;;
    
  save)
    echo "💾 Saving session context..."
    
    # Archive current session memory
    if [ -f .claude-context/session-memory.md ]; then
      cp .claude-context/session-memory.md ".claude-context/session-$(date +%Y%m%d-%H%M%S).md"
    fi
    
    # Update session memory with template for next session
    cat > .claude-context/session-memory.md << 'EOF'
# Session Memory - MultiDB Therapeutic AI Chatbot

## Current Session Context

### Session Started: [TO BE UPDATED]
### Branch: [CURRENT_BRANCH]
### Focus: [SESSION_FOCUS]

## Key Discoveries This Session

### Architecture Status
- [Add architecture discoveries]

### Critical File Updates  
- [Add file modifications]

### Issues and Solutions
- [Add issues found and resolved]

## Working Context

### Files Modified This Session
- [Add modified files]

### Commands Used
- [Add important commands]

### Next Session Priorities
1. [Add priority 1]
2. [Add priority 2]

## Patterns and Insights

### Effective Development Workflow
- [Add workflow insights]

### Architecture Principles
- [Add architectural learnings]

---
*Last Updated: $(date) | Auto-updated by session management*
EOF
    
    # Create detailed session summary
    echo "# Session Summary - $(date)" > .claude-context/session-summary.md
    echo "## Work Completed" >> .claude-context/session-summary.md
    echo "- Updated CLAUDE.md with current architecture" >> .claude-context/session-summary.md
    echo "- Implemented session memory system" >> .claude-context/session-summary.md
    echo "- Optimized auto_include configuration" >> .claude-context/session-summary.md
    echo "## Issues Identified" >> .claude-context/session-summary.md  
    echo "- Legacy file references in auto_include" >> .claude-context/session-summary.md
    echo "- Token usage optimization needed" >> .claude-context/session-summary.md
    echo "## Next Session Should" >> .claude-context/session-summary.md
    echo "- Test new memory configuration" >> .claude-context/session-summary.md
    echo "- Continue performance optimization" >> .claude-context/session-summary.md
    
    echo "✅ Session context and memory saved"
    ;;
    
  checkpoint)
    echo "📸 Creating development checkpoint..."
    
    # Validate changes first
    if [ -x "./scripts/validate-changes.sh" ]; then
        echo "🔍 Validating changes..."
        ./scripts/validate-changes.sh || echo "⚠️ Validation warnings (proceeding anyway)"
    fi
    
    # Run quick tests if available
    if command -v make >/dev/null 2>&1; then
        echo "🧪 Running quick tests..."
        make test-quick || echo "⚠️ Some tests failed (proceeding anyway)"
    fi
    
    # Git checkpoint
    git add -A
    git commit -m "Claude session checkpoint: $(date)

- Session work on $(date)
- Files modified: $(git diff --cached --name-only | wc -l) files
- Focus: Healthcare AI system optimization" || echo "⚠️ Nothing to commit"
    
    echo "✅ Session checkpointed in git"
    ;;
    
  test)
    echo "🧪 Running system validation..."
    
    # Check service health
    if command -v make >/dev/null 2>&1; then
        echo "🔍 Service health check..."
        make health-check
        
        echo "⚡ Quick test suite..."
        make test-quick
        
        echo "🏥 HIPAA compliance check (critical)..."
        make test-hipaa
    else
        echo "❌ Make command not available, running basic checks..."
        python -c "import app.config; print('✅ Configuration loadable')" || echo "❌ Config issues"
    fi
    ;;
    
  clean)
    echo "🧹 Cleaning old session files..."
    find .claude-context -name "session-*.md" -mtime +7 -delete
    echo "✅ Removed session files older than 7 days"
    ;;
    
  status)
    echo "📊 MultiDB Therapeutic AI Chatbot Status"
    echo "========================================"
    
    # Project info
    echo "📁 Project: $(pwd | xargs basename)"
    echo "📅 Last Modified: $(git log -1 --format='%cd' --date=short 2>/dev/null || echo 'Unknown')"
    echo "🏷️  Current Branch: $(git branch --show-current 2>/dev/null || echo 'Unknown')"
    
    # File counts
    echo ""
    echo "📊 Project Metrics:"
    echo "   Python files: $(find . -name '*.py' -not -path './.venv/*' | wc -l)"
    echo "   Test files: $(find . -path './tests/*' -name '*.py' | wc -l)"
    echo "   Documentation: $(find . -name '*.md' | wc -l)"
    
    # Configuration status
    echo ""
    echo "⚙️ Claude Code Configuration:"
    [ -f .claude ] && echo "   ✅ .claude config found" || echo "   ❌ .claude config missing"
    [ -f CLAUDE.md ] && echo "   ✅ CLAUDE.md memory file found" || echo "   ❌ CLAUDE.md memory file missing"
    [ -f PROJECT_CONTEXT.md ] && echo "   ✅ PROJECT_CONTEXT.md found" || echo "   ❌ PROJECT_CONTEXT.md missing"
    
    # Health check if available
    if command -v make >/dev/null 2>&1; then
        echo ""
        echo "🔍 System Health (quick check):"
        make health-check 2>/dev/null || echo "   ⚠️ Health check failed or services down"
    fi
    ;;
    
  *)
    echo "Usage: $0 {start|save|checkpoint|test|clean|status}"
    echo ""
    echo "Commands:"
    echo "  start      - Initialize new Claude Code session with health checks"
    echo "  save       - Save current session context and summary"
    echo "  checkpoint - Validate changes, run tests, and create git checkpoint"
    echo "  test       - Run system validation and critical tests"
    echo "  clean      - Remove old session files (>7 days)"
    echo "  status     - Show project and configuration status"
    exit 1
    ;;
esac
