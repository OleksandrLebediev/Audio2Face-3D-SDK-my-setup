#!/bin/bash

set -e  # Exit on any error

# Get the directory where this script is located
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BUILD_CONFIG=release
# Check if a build configuration was provided as an argument
if [ "$1" != "" ]; then
    BUILD_CONFIG="$1"
fi

if [ "$PYTHON" = "" ]; then
    PYTHON="python"
fi

if [ "$PACKMAN" = "" ]; then
    PACKMAN="${BASE_DIR}/tools/packman/packman"
fi

echo "Fetching dependencies for configuration: ${BUILD_CONFIG}"
echo "Using packman: ${PACKMAN}"

# Check if packman exists and is executable
if [ ! -f "$PACKMAN" ]; then
    echo "ERROR: Packman not found at $PACKMAN"
    exit 1
fi

if [ ! -x "$PACKMAN" ]; then
    echo "WARNING: Packman is not executable. Setting executable permission..."
    chmod +x "$PACKMAN"
fi

# Pull build dependencies using packman
echo "Pulling build dependencies..."
"$PACKMAN" pull -t config="$BUILD_CONFIG" --platform linux-x86_64 "${BASE_DIR}/deps/build-deps.packman.xml"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to pull dependencies in build-deps.packman.xml"
    exit 1
fi

# Pull target dependencies using packman
echo "Pulling target dependencies..."
"$PACKMAN" pull -t config="$BUILD_CONFIG" --platform linux-x86_64 "${BASE_DIR}/deps/target-deps.packman.xml"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to pull dependencies in target-deps.packman.xml"
    exit 1
fi

echo "Dependencies fetched successfully!"