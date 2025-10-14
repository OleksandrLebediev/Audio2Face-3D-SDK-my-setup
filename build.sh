#!/bin/bash

set -e  # Exit on any error

# Set the default build configuration to release
BUILD_CONFIG="release"
# Set the default build project to all
BUILD_PROJECT="all"

# Handle clean command first
if [ "$1" = "clean" ]; then
    BASE_DIR="$(dirname ${BASH_SOURCE})"
    BUILD_DIR="${BASE_DIR}/_build/${BUILD_CONFIG}"
    rm -rf "$BUILD_DIR"
    echo "Build directory cleaned: $BUILD_DIR"
    exit 0
fi

# Select the build configuration and the project to build in arbitrary order.
if [ "$1" = "release" ] || [ "$1" = "debug" ]; then
    BUILD_CONFIG="$1"
    if [ -n "$2" ]; then
        BUILD_PROJECT="$2"
    fi
elif [ -n "$1" ]; then
    BUILD_PROJECT="$1"
    if [ "$2" = "release" ] || [ "$2" = "debug" ]; then
        BUILD_CONFIG="$2"
    fi
fi

BASE_DIR="$(dirname ${BASH_SOURCE})"
BUILD_DIR="${BASE_DIR}/_build/${BUILD_CONFIG}"
export PATH="$PATH:${BASE_DIR}/_deps/build-deps/ninja"

CMAKE="${BASE_DIR}/_deps/build-deps/cmake/bin/cmake"

echo "Build configuration: ${BUILD_CONFIG}"
echo "Build project: ${BUILD_PROJECT}"
echo "Build directory: ${BUILD_DIR}"

if [ ! -d "${BASE_DIR}/_deps" ]; then
    echo "ERROR: Dependencies not found. Please run ./fetch_deps.sh ${BUILD_CONFIG} first."
    exit 1
fi

if [ ! -d "$BUILD_DIR" ]; then
    echo "Creating build directory: $BUILD_DIR"
    mkdir -p "$BUILD_DIR"
fi

# Check if cmake exists
if [ ! -f "$CMAKE" ]; then
    echo "ERROR: CMake not found at $CMAKE. Please ensure dependencies are fetched."
    exit 1
fi

# Check if ninja exists
if ! command -v ninja >/dev/null 2>&1; then
    echo "ERROR: Ninja not found in PATH. Please ensure dependencies are fetched."
    echo "PATH: $PATH"
    exit 1
fi

echo "Configuring CMake..."
"$CMAKE" -B "$BUILD_DIR" -G Ninja -S . -DCMAKE_BUILD_TYPE="${BUILD_CONFIG^}"

echo "Building project..."
"$CMAKE" --build "$BUILD_DIR" --target "$BUILD_PROJECT" --config "$BUILD_CONFIG" --parallel

echo "Build completed successfully!"
