#!/bin/bash
set -e

# Configuration
REMOTE_USER="feras1960"
REMOTE_HOST="192.168.0.83"
REMOTE_DIR="/home/feras1960/erpmax-orchestrator"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Starting update deployment to ${REMOTE_HOST}...${NC}"

# Function to run commands on remote server
remote_exec() {
    ssh ${REMOTE_USER}@${REMOTE_HOST} "$@"
}

# Function to copy files to remote server
remote_copy() {
    rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='.env.production' "$@" ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/
}

# Step 1: Copy updated files
echo -e "${YELLOW}📦 Copying updated files...${NC}"
remote_copy .
echo -e "${GREEN}✅ Files copied${NC}"

# Step 2: Stop app and worker (keep database running)
echo -e "${YELLOW}🛑 Stopping app and worker...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production stop app worker
"
echo -e "${GREEN}✅ App and worker stopped${NC}"

# Step 3: Rebuild images
echo -e "${YELLOW}🏗️  Rebuilding Docker images...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production build
"
echo -e "${GREEN}✅ Images rebuilt${NC}"

# Step 4: Run migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production up migration
"
echo -e "${GREEN}✅ Migrations completed${NC}"

# Step 5: Check migration logs
echo -e "${YELLOW}📋 Migration logs:${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker logs erpmax_migration --tail 20
"

# Step 6: Start app and worker
echo -e "${YELLOW}🚀 Starting app and worker...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d app worker
"
echo -e "${GREEN}✅ Services started${NC}"

# Step 7: Wait and check health
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

echo -e "${YELLOW}🏥 Testing API health...${NC}"
if remote_exec "curl -f http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    echo -e "${YELLOW}📋 Recent logs:${NC}"
    remote_exec "
        cd ${REMOTE_DIR}
        docker logs erpmax_orchestrator --tail 30
    "
    exit 1
fi

# Step 8: Show status
echo -e "${YELLOW}📊 Service status:${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production ps
"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Update completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
