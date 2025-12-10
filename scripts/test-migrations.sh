#!/bin/bash
# Test migrations locally before production deployment

set -e

echo "🧪 Testing Database Migrations"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Create test database
echo -e "${YELLOW}📦 Starting test PostgreSQL...${NC}"
docker compose up -d postgres

# Wait for PostgreSQL
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
sleep 5

# Test: Fresh migration
echo -e "\n${YELLOW}Test 1: Fresh database migration${NC}"
echo "================================"
alembic upgrade head
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Fresh migration successful${NC}"
else
    echo -e "${RED}❌ Fresh migration failed${NC}"
    exit 1
fi

# Test: Check current version
echo -e "\n${YELLOW}Test 2: Check current version${NC}"
echo "================================"
CURRENT_VERSION=$(alembic current)
echo "Current version: $CURRENT_VERSION"
if [ -n "$CURRENT_VERSION" ]; then
    echo -e "${GREEN}✅ Version check successful${NC}"
else
    echo -e "${RED}❌ Version check failed${NC}"
    exit 1
fi

# Test: Downgrade
echo -e "\n${YELLOW}Test 3: Downgrade migration${NC}"
echo "================================"
alembic downgrade -1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Downgrade successful${NC}"
else
    echo -e "${RED}❌ Downgrade failed${NC}"
    exit 1
fi

# Test: Re-upgrade
echo -e "\n${YELLOW}Test 4: Re-upgrade migration${NC}"
echo "================================"
alembic upgrade head
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Re-upgrade successful${NC}"
else
    echo -e "${RED}❌ Re-upgrade failed${NC}"
    exit 1
fi

# Test: Verify tables
echo -e "\n${YELLOW}Test 5: Verify tables exist${NC}"
echo "================================"
TABLES=$(docker exec erpmax_postgres psql -U erpmax -d erpmax_orchestrator -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
TABLES=$(echo $TABLES | tr -d ' ')
echo "Found $TABLES tables"
if [ "$TABLES" -ge 7 ]; then
    echo -e "${GREEN}✅ All tables exist${NC}"
else
    echo -e "${RED}❌ Missing tables (expected >= 7, got $TABLES)${NC}"
    exit 1
fi

# Test: Run connection test
echo -e "\n${YELLOW}Test 6: Database connection test${NC}"
echo "================================"
python test_db_connection.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Connection test successful${NC}"
else
    echo -e "${RED}❌ Connection test failed${NC}"
    exit 1
fi

# Summary
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}✅ All migration tests passed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "You can now safely deploy to production:"
echo "  docker compose -f docker-compose.prod.yml up -d"
