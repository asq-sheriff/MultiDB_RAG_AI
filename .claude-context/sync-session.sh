#!/bin/bash

# Quick session memory sync during active session
echo "🔄 Syncing session memory..."

# Update session timestamp
sed -i '' "s/Session Started: .*/Session Started: $(date)/" .claude-context/session-memory.md

# Update branch info
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
sed -i '' "s/Branch: .*/Branch: $CURRENT_BRANCH/" .claude-context/session-memory.md

echo "✅ Session memory synced with current context"
echo "📝 To add discoveries: edit .claude-context/session-memory.md"