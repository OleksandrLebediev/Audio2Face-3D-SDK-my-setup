#!/bin/bash

set -euo pipefail

BASE_DIR="/app"
BUILD_TYPE="${BUILD_TYPE:-release}"

# Set search paths for binaries and shared libs
export PATH="${BASE_DIR}/_build/${BUILD_TYPE}/audio2x-sdk/bin:${PATH}"
export PYTHONPATH="${BASE_DIR}/audio2x-common/scripts:${PYTHONPATH:-}"

if [[ -n "${CUDA_PATH:-}" ]]; then
  export PATH="${CUDA_PATH}/bin:${PATH}"
  export LD_LIBRARY_PATH="${CUDA_PATH}/lib64:${LD_LIBRARY_PATH:-}"
fi
if [[ -n "${TENSORRT_ROOT_DIR:-}" ]]; then
  # On some images, TensorRT libs live under /usr/lib/x86_64-linux-gnu or /usr/lib
  export LD_LIBRARY_PATH="${TENSORRT_ROOT_DIR}/lib:${TENSORRT_ROOT_DIR}:${LD_LIBRARY_PATH:-}"
fi

# Optional in-container build (for images built with SKIP_BUILD=1)
if [[ "${BUILD_IN_CONTAINER:-0}" == "1" ]]; then
  pushd "${BASE_DIR}" >/dev/null
  ./fetch_deps.sh "${BUILD_TYPE}"
  ./build.sh all "${BUILD_TYPE}"
  popd >/dev/null
fi

# Optionally download models (requires HF_TOKEN)
if [[ "${DOWNLOAD_MODELS:-0}" == "1" ]]; then
  if [[ -n "${HF_TOKEN:-}" ]]; then
    # Non-interactive login for huggingface hub (hf CLI)
    hf auth login --token "${HF_TOKEN}" || true
  fi
  "${BASE_DIR}/download_models.sh"
  "${BASE_DIR}/gen_testdata.sh"
fi

# Optionally run unit tests to validate the environment
if [[ "${RUN_UNIT_TESTS:-0}" == "1" ]]; then
  if [[ -x "${BASE_DIR}/run_sample.sh" ]]; then
    "${BASE_DIR}/run_sample.sh" "${BASE_DIR}/_build/${BUILD_TYPE}/audio2face-sdk/bin/audio2face-unit-tests"
  fi
fi

# If a command is provided, execute it. Otherwise, idle.
if [[ "$#" -gt 0 ]]; then
  exec "$@"
else
  echo "Container is ready. Provide a command (or set Startup Script) to run your service."
  tail -f /dev/null
fi


