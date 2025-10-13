#!/bin/bash

set -e

# Get the directory where this script is located
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BASE_DIR/_data"

# Download A2F models
A2F_MODEL_DIR="$BASE_DIR/_data/audio2face-models"
mkdir -p "$A2F_MODEL_DIR"
python -m huggingface_hub.commands.huggingface_cli download nvidia/Audio2Face-3D-v3.0          --local-dir "$A2F_MODEL_DIR/audio2face-3d-v3.0"
python -m huggingface_hub.commands.huggingface_cli download nvidia/Audio2Face-3D-v2.3.1-Claire --local-dir "$A2F_MODEL_DIR/audio2face-3d-v2.3.1-claire"
python -m huggingface_hub.commands.huggingface_cli download nvidia/Audio2Face-3D-v2.3.1-James  --local-dir "$A2F_MODEL_DIR/audio2face-3d-v2.3.1-james"
python -m huggingface_hub.commands.huggingface_cli download nvidia/Audio2Face-3D-v2.3-Mark     --local-dir "$A2F_MODEL_DIR/audio2face-3d-v2.3-mark"

# Download A2E models
A2E_MODEL_DIR="$BASE_DIR/_data/audio2emotion-models"
mkdir -p "$A2E_MODEL_DIR"
python -m huggingface_hub.commands.huggingface_cli download nvidia/Audio2Emotion-v2.2          --local-dir $A2E_MODEL_DIR/audio2emotion-v2.2

echo Models are downloaded to "$A2F_MODEL_DIR" and "$A2E_MODEL_DIR"