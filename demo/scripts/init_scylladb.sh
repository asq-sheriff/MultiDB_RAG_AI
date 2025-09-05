#!/bin/bash

# Initialize ScyllaDB for Demo
# ===========================
# Creates keyspace and tables required for chat-history service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🗄️  Initializing ScyllaDB for demo...${NC}"

# Wait for ScyllaDB cluster to be ready
echo -e "${YELLOW}⏳ Waiting for ScyllaDB cluster to be ready...${NC}"
for i in {1..30}; do
    if docker exec demo-v1-scylla-node1 nodetool status 2>/dev/null | grep -q "UN.*172"; then
        NODES_UP=$(docker exec demo-v1-scylla-node1 nodetool status 2>/dev/null | grep -c "UN.*172" || echo "0")
        # Check if we have enough nodes for cluster (2 minimum for demo)
        REQUIRED_NODES=2
        if [ "$NODES_UP" -ge 3 ]; then
            echo -e "${GREEN}✅ ScyllaDB cluster is ready ($NODES_UP nodes up)${NC}"
            break
        elif [ "$NODES_UP" -ge 2 ] && [ $i -ge 15 ]; then
            # After 30s, accept 2 nodes for basic demo functionality
            echo -e "${YELLOW}⚠️  ScyllaDB cluster ready with $NODES_UP nodes (minimum for demo)${NC}"
            break
        else
            echo -e "${YELLOW}⏳ Waiting for more nodes... ($NODES_UP/2+ up)${NC}"
        fi
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ ScyllaDB cluster not ready after 60s${NC}"
        docker exec demo-v1-scylla-node1 nodetool status 2>/dev/null || echo "Could not check status"
        exit 1
    fi
    sleep 2
done

# Create keyspace
echo -e "${BLUE}📁 Creating keyspace demo_v1_chatbot_ks...${NC}"
docker exec demo-v1-scylla-node1 cqlsh -e "
    CREATE KEYSPACE IF NOT EXISTS demo_v1_chatbot_ks 
    WITH REPLICATION = {
        'class': 'NetworkTopologyStrategy', 
        'datacenter1': 3
    };" 2>/dev/null || true

# Create tables
echo -e "${BLUE}📊 Creating conversation_history table...${NC}"
docker exec demo-v1-scylla-node1 cqlsh -e "
    USE demo_v1_chatbot_ks;
    CREATE TABLE IF NOT EXISTS conversation_history (
        session_id UUID,
        timestamp TIMESTAMP,
        message_id UUID,
        actor TEXT,
        message TEXT,
        confidence FLOAT,
        cached BOOLEAN,
        response_time_ms INT,
        route_used TEXT,
        generation_used BOOLEAN,
        metadata MAP<TEXT, TEXT>,
        PRIMARY KEY (session_id, timestamp)
    ) WITH CLUSTERING ORDER BY (timestamp ASC);" 2>/dev/null || true

echo -e "${BLUE}📝 Creating user_feedback table...${NC}"
docker exec demo-v1-scylla-node1 cqlsh -e "
    USE demo_v1_chatbot_ks;
    CREATE TABLE IF NOT EXISTS user_feedback (
        feedback_id UUID PRIMARY KEY,
        session_id UUID,
        message_id UUID,
        user_id UUID,
        rating INT,
        feedback TEXT,
        category TEXT,
        created_at TIMESTAMP
    );" 2>/dev/null || true

# Verify setup
echo -e "${BLUE}🔍 Verifying ScyllaDB setup...${NC}"
TABLES_OUTPUT=$(docker exec demo-v1-scylla-node1 cqlsh -e "USE demo_v1_chatbot_ks; DESCRIBE TABLES;" 2>/dev/null)

if echo "$TABLES_OUTPUT" | grep -q "conversation_history" && echo "$TABLES_OUTPUT" | grep -q "user_feedback"; then
    echo -e "${GREEN}✅ ScyllaDB initialized successfully with required tables:${NC}"
    echo "$TABLES_OUTPUT" | sed 's/^/   • /'
else
    echo -e "${RED}❌ ScyllaDB initialization failed - missing required tables${NC}"
    echo "Expected: conversation_history, user_feedback"
    echo "Found: $TABLES_OUTPUT"
    exit 1
fi

echo -e "${GREEN}🎉 ScyllaDB ready for chat-history service!${NC}"