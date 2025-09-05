#!/bin/bash

# MultiDB Therapeutic AI Chatbot - Interactive Demo Runner
# =====================================================
# This script sets up and runs the interactive demo system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo -e "🏥 MultiDB Therapeutic AI Chatbot"
echo -e "   Interactive Demo System"
echo -e "==========================================${NC}"
echo

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python version: ${PYTHON_VERSION}${NC}"

# Check if virtual environment should be used
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✓ Virtual environment active: $VIRTUAL_ENV${NC}"
else
    echo -e "${YELLOW}ℹ️  No virtual environment detected (optional)${NC}"
fi

# Install required dependencies if needed
REQUIRED_PACKAGES="asyncio dataclasses enum"
echo -e "${BLUE}📦 Checking dependencies...${NC}"

# Check if demo directory exists
if [ ! -d "demo" ]; then
    echo -e "${RED}❌ demo directory not found${NC}"
    echo -e "   Please run this script from the MultiDB-Chatbot root directory"
    exit 1
fi

echo -e "${GREEN}✓ Demo directory found${NC}"

# Set environment variables for demo
export DEMO_MODE=1
export APP_ENVIRONMENT=demo
export PYTHONPATH="${PWD}:${PYTHONPATH}"

echo
echo -e "${BLUE}🚀 Starting Interactive Demo...${NC}"
echo -e "${YELLOW}   Use Ctrl+C to exit at any time${NC}"
echo

# Add a small delay to let user read the startup message
sleep 2

# Change to demo UI directory
cd demo/ui

# Check for real data flag
if [[ "$1" == "--real-data" || "$1" == "--use-real-data" ]]; then
    echo -e "${BLUE}🗄️  Real database mode requested${NC}"
    echo -e "${YELLOW}📋 Ensure demo databases are running: cd demo/scripts && ./run_demo.sh --databases-only${NC}"
    echo
    python3 interactive_demo.py --use-real-data
else
    echo -e "${BLUE}🎭 Simulation mode (no databases required)${NC}"
    echo
    python3 interactive_demo.py
fi

echo
echo -e "${GREEN}✅ Demo session completed${NC}"
echo -e "${BLUE}📚 For more information:${NC}"
echo -e "   • Review docs/User_Guide.md for detailed feature documentation"
echo -e "   • Check CLAUDE.md for technical architecture notes"
echo -e "   • Run 'make test-quick' to see system health status"
echo