#!/bin/bash
set -e

# Configuration
REMOTE_USER="feras1960"
REMOTE_HOST="192.168.0.83"
REMOTE_DIR="/home/feras1960/erpmax-orchestrator"
PROJECT_NAME="erpmax-orchestrator"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment to ${REMOTE_HOST}...${NC}"

# Function to run commands on remote server
remote_exec() {
    ssh ${REMOTE_USER}@${REMOTE_HOST} "$@"
}

# Function to copy files to remote server
remote_copy() {
    rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='.env.production' "$@" ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/
}

# Step 1: Check SSH connection
echo -e "${YELLOW}📡 Checking SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 ${REMOTE_USER}@${REMOTE_HOST} "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to ${REMOTE_HOST}${NC}"
    echo "Please check your SSH credentials and network connection"
    exit 1
fi
echo -e "${GREEN}✅ SSH connection successful${NC}"

# Step 2: Install Docker and Docker Compose on remote server if needed
echo -e "${YELLOW}🐳 Checking Docker installation...${NC}"
remote_exec "
    if ! command -v docker &> /dev/null; then
        echo 'Installing Docker...'
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker \$USER
        rm get-docker.sh
        echo 'Docker installed successfully'
    else
        echo 'Docker already installed'
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo 'Installing Docker Compose...'
        sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        echo 'Docker Compose installed successfully'
    else
        echo 'Docker Compose already installed'
    fi
"
echo -e "${GREEN}✅ Docker environment ready${NC}"

# Step 3: Create remote directory
echo -e "${YELLOW}📁 Creating remote directory...${NC}"
remote_exec "mkdir -p ${REMOTE_DIR}"
echo -e "${GREEN}✅ Remote directory created${NC}"

# Step 4: Copy project files
echo -e "${YELLOW}📦 Copying project files...${NC}"
remote_copy .
echo -e "${GREEN}✅ Files copied successfully${NC}"

# Step 5: Setup environment file
echo -e "${YELLOW}⚙️  Setting up environment file...${NC}"
if [ -f ".env.production" ]; then
    echo "Copying existing .env.production file..."
    scp .env.production ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/.env.production
else
    echo "Creating new .env.production file on remote server..."
    remote_exec "
        cd ${REMOTE_DIR}
        if [ ! -f .env.production ]; then
            cp .env.production.example .env.production
            
            # Generate secure passwords
            POSTGRES_PASS=\$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
            REDIS_PASS=\$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
            RABBITMQ_PASS=\$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
            SECRET_KEY=\$(openssl rand -hex 32)
            
            # Update .env.production
            sed -i \"s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=\${POSTGRES_PASS}/\" .env.production
            sed -i \"s/REDIS_PASSWORD=.*/REDIS_PASSWORD=\${REDIS_PASS}/\" .env.production
            sed -i \"s/RABBITMQ_PASSWORD=.*/RABBITMQ_PASSWORD=\${RABBITMQ_PASS}/\" .env.production
            sed -i \"s/SECRET_KEY=.*/SECRET_KEY=\${SECRET_KEY}/\" .env.production
            
            echo '✅ Environment file created with secure passwords'
        else
            echo '⚠️  .env.production already exists, skipping...'
        fi
    "
fi
echo -e "${GREEN}✅ Environment configured${NC}"

# Step 6: Stop existing containers (if any)
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    if [ -f docker-compose.prod.yml ]; then
        docker compose -f docker-compose.prod.yml --env-file .env.production down || true
    fi
"
echo -e "${GREEN}✅ Existing containers stopped${NC}"

# Step 7: Build and start containers
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production build
"
echo -e "${GREEN}✅ Docker images built${NC}"

echo -e "${YELLOW}🚀 Starting services...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d
"
echo -e "${GREEN}✅ Services started${NC}"

# Step 8: Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Step 9: Check migration status
echo -e "${YELLOW}🔍 Checking migration status...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker logs erpmax_migration
"

# Step 10: Check service status
echo -e "${YELLOW}📊 Checking service status...${NC}"
remote_exec "
    cd ${REMOTE_DIR}
    docker compose -f docker-compose.prod.yml --env-file .env.production ps
"

# Step 11: Test API health
echo -e "${YELLOW}🏥 Testing API health...${NC}"
sleep 5
if remote_exec "curl -f http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  API health check failed, checking logs...${NC}"
    remote_exec "
        cd ${REMOTE_DIR}
        docker logs erpmax_orchestrator --tail 50
    "
fi

# Step 12: Display access information
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📍 Access Information:${NC}"
echo -e "   API URL: http://${REMOTE_HOST}:8000"
echo -e "   API Docs: http://${REMOTE_HOST}:8000/docs"
echo -e "   Health Check: http://${REMOTE_HOST}:8000/health"
echo ""
echo -e "${YELLOW}🔧 Useful Commands:${NC}"
echo -e "   View logs: ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR} && docker compose -f docker-compose.prod.yml logs -f'"
echo -e "   Restart: ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR} && docker compose -f docker-compose.prod.yml restart'"
echo -e "   Stop: ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR} && docker compose -f docker-compose.prod.yml down'"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
