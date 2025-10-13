# Multi-stage build: builder + runtime to reduce final image size

ARG BASE_IMAGE=nvcr.io/nvidia/tensorrt:24.12-py3

# ============ Builder stage ============
FROM ${BASE_IMAGE} as builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs build-essential cmake ninja-build curl ca-certificates \
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY deps/requirements.txt requirements-service.txt ./

# Install Miniconda (Python 3.10) and create venv-like environment at /opt/venv
RUN curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-py310_24.7.1-0-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && rm -f /tmp/miniconda.sh && \
    /opt/conda/bin/conda create -y -n py310 python=3.10 pip && \
    /opt/conda/bin/conda clean -afy && \
    /opt/conda/bin/conda run -n py310 pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/conda/bin/conda run -n py310 pip install --no-cache-dir -r requirements.txt -r requirements-service.txt && \
    mkdir -p /opt/venv && cp -a /opt/conda/envs/py310/. /opt/venv/ && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + || true

# ============ Runtime stage ============
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs build-essential cmake ninja-build curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy sources
COPY . /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Env expected by scripts
ENV CUDA_PATH=/usr/local/cuda \
    TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu \
    PATH=/opt/venv/bin:${PATH}

# Optional: pull LFS files
RUN git lfs install && git lfs pull || true

# Allow skipping build during image creation (useful on Apple Silicon)
ARG SKIP_BUILD=0
RUN if [ "${SKIP_BUILD}" = "1" ]; then \
      echo "Skipping SDK build at image build time"; \
    else \
      ./fetch_deps.sh release && ./build.sh all release; \
    fi

# Entrypoint
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
