# Multi-stage build: builder + runtime to reduce final image size

ARG BASE_IMAGE=nvcr.io/nvidia/tensorrt:25.01-py3

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
    # Pin a single NumPy version for the whole image to avoid resolver conflicts
    /opt/conda/bin/conda run -n py310 pip install --no-cache-dir numpy==1.24.4 && \
    # Install core deps first (will reuse the pinned NumPy)
    /opt/conda/bin/conda run -n py310 pip install --no-cache-dir -r requirements.txt && \
    # Install service deps without pulling transitive deps (to prevent re-pinning NumPy)
    /opt/conda/bin/conda run -n py310 pip install --no-cache-dir -r requirements-service.txt --no-deps && \
    mkdir -p /opt/venv && cp -a /opt/conda/envs/py310/. /opt/venv/ && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + || true

# ============ Runtime stage ============
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs build-essential cmake ninja-build curl ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*

# Install ZLIB 1.3.1 (required version)
RUN cd /tmp && \
    wget https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz && \
    tar -xzf zlib-1.3.1.tar.gz && \
    cd zlib-1.3.1 && \
    ./configure --prefix=/usr && \
    make && make install && \
    cd /tmp && rm -rf zlib-1.3.1*

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

# Set executable permissions for scripts
RUN chmod +x fetch_deps.sh build.sh download_models.sh gen_testdata.sh run_sample.sh && \
    chmod +x tools/packman/packman

# Build SDK (libraries only, excluding tools that have linking issues)
RUN echo "Starting dependency fetch..." && \
    ./fetch_deps.sh release && \
    echo "Dependencies fetched successfully. Starting build..." && \
    ./build.sh audio2x release && \
    echo "Build completed successfully."

# Entrypoint
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
