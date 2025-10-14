#!/bin/bash

# Audio2X SDK Deployment Script
# Usage: ./deploy.sh user@server-ip [hf_token] [run_tests]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ "$#" -lt 1 ]; then
    echo -e "${RED}Usage: $0 user@server-ip [hf_token] [run_tests]${NC}"
    echo "Example: $0 ubuntu@192.168.1.100 hf_abc123xyz"
    echo "Example with tests: $0 ubuntu@192.168.1.100 hf_abc123xyz yes"
    exit 1
fi

SERVER=$1
HF_TOKEN=${2:-""}
RUN_TESTS=${3:-"no"}

echo -e "${GREEN}🚀 Starting deployment to ${SERVER}${NC}"

# Step 1: Check SSH connection
echo -e "${YELLOW}📡 Testing SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo 'SSH connection successful'"; then
    echo -e "${RED}❌ Cannot connect to ${SERVER}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection OK${NC}"

# Step 2: Install basic dependencies
echo -e "${YELLOW}📦 Checking basic dependencies...${NC}"
ssh "$SERVER" << 'EOF'
if ! command -v curl &> /dev/null || ! command -v wget &> /dev/null; then
    echo "Installing curl and wget..."
    sudo apt-get update
    sudo apt-get install -y curl wget
fi
EOF
echo -e "${GREEN}✓ Basic dependencies OK${NC}"

# Step 3: Check if Docker is installed
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
    echo -e "${YELLOW}⚠️  You may need to log out and back in for Docker group changes to take effect${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Step 3: Check GPU availability
echo -e "${YELLOW}🎮 Checking GPU availability...${NC}"
if ! ssh "$SERVER" "nvidia-smi &>/dev/null"; then
    echo -e "${RED}❌ No NVIDIA GPU detected or drivers not installed${NC}"
    echo -e "${YELLOW}Please install NVIDIA drivers first${NC}"
    exit 1
fi
echo -e "${GREEN}✓ GPU detected${NC}"

# Step 4: Check NVIDIA Container Toolkit
echo -e "${YELLOW}🐋 Checking NVIDIA Container Toolkit...${NC}"
if ! ssh "$SERVER" "docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi &>/dev/null"; then
    echo -e "${YELLOW}NVIDIA Container Toolkit not configured. Installing...${NC}"
    ssh "$SERVER" << 'EOF'
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
# Use new GPG key method (apt-key is deprecated)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
EOF
    echo -e "${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
else
    echo -e "${GREEN}✓ NVIDIA Container Toolkit OK${NC}"
fi

# Step 5: Check Git LFS
echo -e "${YELLOW}📦 Checking Git LFS...${NC}"
if ! ssh "$SERVER" "command -v git-lfs &> /dev/null"; then
    echo -e "${YELLOW}Git LFS not found. Installing...${NC}"
    ssh "$SERVER" << 'EOF'
sudo apt-get update
sudo apt-get install -y git-lfs
git lfs install
EOF
    echo -e "${GREEN}✓ Git LFS installed${NC}"
else
    echo -e "${GREEN}✓ Git LFS already installed${NC}"
fi

# Step 6: Clone/Update repository
echo -e "${YELLOW}📥 Setting up repository...${NC}"
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

# Step 7: Check if models exist
echo -e "${YELLOW}📥 Checking models...${NC}"
MODELS_EXIST=$(ssh "$SERVER" "[ -d 'Audio2Face-3D-SDK/_data/audio2face-models' ] && [ -n \"\$(ls -A Audio2Face-3D-SDK/_data/audio2face-models 2>/dev/null)\" ] && echo 'yes' || echo 'no'")

if [ "$MODELS_EXIST" = "no" ]; then
    echo -e "${YELLOW}Models not found. Downloading...${NC}"
    if [ -z "$HF_TOKEN" ]; then
        echo -e "${RED}❌ ERROR: Models not found and no HF_TOKEN provided${NC}"
        echo -e "${YELLOW}Please provide HF_TOKEN as second argument:${NC}"
        echo -e "${YELLOW}  $0 $SERVER hf_your_token_here${NC}"
        exit 1
    fi
    
    ssh "$SERVER" << EOF
cd Audio2Face-3D-SDK
export HF_TOKEN=${HF_TOKEN}
echo "Installing huggingface-hub..."
python3 -m pip install --quiet huggingface-hub
echo "Downloading models (this may take 5-10 minutes)..."
chmod +x download_models.sh
./download_models.sh
EOF
    echo -e "${GREEN}✓ Models downloaded successfully${NC}"
else
    echo -e "${GREEN}✓ Models already exist${NC}"
fi

# Step 8: Create .env file
echo -e "${YELLOW}⚙️  Configuring environment...${NC}"

# Determine if tests should run
if [ "$RUN_TESTS" = "yes" ] || [ "$RUN_TESTS" = "1" ]; then
    RUN_UNIT_TESTS_VALUE=1
    echo -e "${YELLOW}Unit tests will run after deployment${NC}"
else
    RUN_UNIT_TESTS_VALUE=0
fi

if [ -n "$HF_TOKEN" ]; then
    ssh "$SERVER" << EOF
cd Audio2Face-3D-SDK
cat > .env << 'ENVFILE'
BUILD_TYPE=release
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
HF_TOKEN=${HF_TOKEN}
DOWNLOAD_MODELS=0
RUN_UNIT_TESTS=${RUN_UNIT_TESTS_VALUE}
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
ENVFILE
EOF
    echo -e "${GREEN}✓ Environment configured${NC}"
else
    ssh "$SERVER" << 'EOF'
cd Audio2Face-3D-SDK
cat > .env << 'ENVFILE'
BUILD_TYPE=release
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
HF_TOKEN=your_token_here
DOWNLOAD_MODELS=0
RUN_UNIT_TESTS=${RUN_UNIT_TESTS_VALUE}
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
ENVFILE
EOF
    echo -e "${YELLOW}⚠️  No HF_TOKEN provided. You'll need to add it manually to .env${NC}"
fi

# Step 9: Build and start the service
echo -e "${YELLOW}🔨 Building and starting the service...${NC}"
ssh "$SERVER" << 'EOF'
cd Audio2Face-3D-SDK
docker compose down 2>/dev/null || true
docker compose up -d --build
EOF
echo -e "${GREEN}✓ Service started${NC}"

# Step 10: Wait for service to be ready
echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
sleep 10

# Step 11: Check health
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

# Step 12: Display service info
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

