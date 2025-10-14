#!/bin/bash

# Audio2X SDK Deployment Script
# Usage: ./deploy.sh user@server-ip [hf_token]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ "$#" -lt 1 ]; then
    echo -e "${RED}Usage: $0 user@server-ip [hf_token]${NC}"
    echo "Example: $0 ubuntu@192.168.1.100 hf_abc123xyz"
    exit 1
fi

SERVER=$1
HF_TOKEN=${2:-""}

echo -e "${GREEN}🚀 Starting deployment to ${SERVER}${NC}"

# Step 1: Check SSH connection
echo -e "${YELLOW}📡 Testing SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo 'SSH connection successful'"; then
    echo -e "${RED}❌ Cannot connect to ${SERVER}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection OK${NC}"

# Step 2: Check if Docker is installed
echo -e "${YELLOW}🐳 Checking Docker installation...${NC}"
if ! ssh "$SERVER" "command -v docker &> /dev/null"; then
    echo -e "${YELLOW}Docker not found. Installing...${NC}"
    ssh "$SERVER" << 'EOF'
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh
EOF
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Step 3: Check NVIDIA Container Toolkit
echo -e "${YELLOW}🎮 Checking NVIDIA Container Toolkit...${NC}"
if ! ssh "$SERVER" "docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi &>/dev/null"; then
    echo -e "${YELLOW}NVIDIA Container Toolkit not configured. Installing...${NC}"
    ssh "$SERVER" << 'EOF'
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
EOF
    echo -e "${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
else
    echo -e "${GREEN}✓ NVIDIA Container Toolkit OK${NC}"
fi

# Step 4: Clone/Update repository
echo -e "${YELLOW}📦 Setting up repository...${NC}"
ssh "$SERVER" 'git config --global --add safe.directory /root/Audio2Face-3D-SDK || true'
ssh "$SERVER" << EOF
if [ -d "Audio2Face-3D-SDK" ]; then
    echo "Repository exists, pulling latest changes..."
    cd Audio2Face-3D-SDK
    git pull
    git lfs pull
else
    echo "Cloning repository..."
    git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
    cd Audio2Face-3D-SDK
    git lfs install
    git lfs pull
fi
EOF
echo -e "${GREEN}✓ Repository ready${NC}"

# Step 5: Download models if needed
echo -e "${YELLOW}📥 Checking and downloading models...${NC}"
if [ -n "$HF_TOKEN" ]; then
    ssh "$SERVER" << EOF
cd Audio2Face-3D-SDK
if [ ! -d "_data/audio2face-models" ] || [ ! -d "_data/generated" ]; then
    echo "Models not found, downloading..."
    export HF_TOKEN=${HF_TOKEN}
    python3 -m pip install huggingface-hub
    python3 -c "
import os
from huggingface_hub import hf_hub_download
os.environ['HF_TOKEN'] = '${HF_TOKEN}'
try:
    hf_hub_download(repo_id='nvidia/audio2face-3d-v2.3-mark', filename='model.json', local_dir='_data/audio2face-models')
    print('Models downloaded successfully')
except Exception as e:
    print(f'Model download failed: {e}')
"
else
    echo "Models already exist, skipping download"
fi
EOF
    echo -e "${GREEN}✓ Models ready${NC}"
else
    echo -e "${YELLOW}⚠️  No HF_TOKEN provided. Models must be downloaded manually${NC}"
fi

# Step 6: Create .env file
echo -e "${YELLOW}⚙️  Configuring environment...${NC}"
if [ -n "$HF_TOKEN" ]; then
    ssh "$SERVER" << EOF
cd Audio2Face-3D-SDK
cat > .env << 'ENVFILE'
BUILD_TYPE=release
SKIP_BUILD=0
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
HF_TOKEN=${HF_TOKEN}
DOWNLOAD_MODELS=1
RUN_UNIT_TESTS=0
BUILD_IN_CONTAINER=0
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
ENVFILE
EOF
    echo -e "${GREEN}✓ Environment configured with HF_TOKEN${NC}"
else
    echo -e "${YELLOW}⚠️  No HF_TOKEN provided. You'll need to add it manually to .env${NC}"
    ssh "$SERVER" << 'EOF'
cd Audio2Face-3D-SDK
cat > .env << 'ENVFILE'
BUILD_TYPE=release
SKIP_BUILD=0
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
HF_TOKEN=your_token_here
DOWNLOAD_MODELS=1
RUN_UNIT_TESTS=0
BUILD_IN_CONTAINER=0
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
ENVFILE
EOF
fi

# Step 7: Build and start the service
echo -e "${YELLOW}🔨 Building and starting the service...${NC}"
ssh "$SERVER" << 'EOF'
cd Audio2Face-3D-SDK
docker compose down 2>/dev/null || true
docker compose up -d --build
EOF
echo -e "${GREEN}✓ Service started${NC}"

# Step 8: Wait for service to be ready
echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
sleep 10

# Step 9: Check health
echo -e "${YELLOW}🏥 Checking service health...${NC}"
for i in {1..30}; do
    if ssh "$SERVER" "curl -s http://localhost:8000/health" &>/dev/null; then
        echo -e "${GREEN}✓ Service is healthy!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Service health check failed${NC}"
        echo "Check logs with: ssh $SERVER 'cd Audio2Face-3D-SDK && docker compose logs'"
        exit 1
    fi
    sleep 2
done

# Step 10: Display service info
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "Service URL: ${GREEN}http://${SERVER#*@}:8000${NC}"
echo -e "Health check: ${GREEN}http://${SERVER#*@}:8000/health${NC}"
echo ""
echo -e "Useful commands:"
echo -e "  View logs:    ${YELLOW}ssh $SERVER 'cd Audio2Face-3D-SDK && docker compose logs -f'${NC}"
echo -e "  Restart:      ${YELLOW}ssh $SERVER 'cd Audio2Face-3D-SDK && docker compose restart'${NC}"
echo -e "  Stop:         ${YELLOW}ssh $SERVER 'cd Audio2Face-3D-SDK && docker compose down'${NC}"
echo -e "  SSH to server:${YELLOW}ssh $SERVER${NC}"
echo ""

if [ -z "$HF_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  IMPORTANT: Add your HuggingFace token:${NC}"
    echo -e "  1. SSH to server: ${YELLOW}ssh $SERVER${NC}"
    echo -e "  2. Edit .env: ${YELLOW}nano Audio2Face-3D-SDK/.env${NC}"
    echo -e "  3. Add your HF_TOKEN"
    echo -e "  4. Restart: ${YELLOW}docker compose restart${NC}"
    echo ""
fi

echo -e "${GREEN}Done! 🎉${NC}"

