# Audio2X SDK

The Audio2X SDK is a comprehensive toolkit for fast audio-driven animation and emotion detection. It consists of two main components:

- **Audio2Emotion SDK**: Analyzes audio (speech) input to detect and classify emotional states
- **Audio2Face SDK**: Generates facial animations from audio (speech) input, supporting both regression and diffusion-based approaches

The SDK is designed for high-performance applications requiring fast audio processing and animation generation. It leverages NVIDIA's GPU computing capabilities through CUDA and TensorRT for optimal performance.

## 🚀 Quick Start

**Want to get started quickly?** Check out [QUICKSTART.md](QUICKSTART.md) for:
- One-command deployment to server
- Docker Compose setup
- Local development guide

### Key Features

- **Faster Than Real-time Processing**: Faster than 60 FPS frame generation
- **Multi-track Support**: Process multiple audio streams simultaneously
- **GPU Acceleration**: Full CUDA/TensorRT integration
- **Flexible Architecture**: Support for both batch and interactive processing modes
- **Cross-platform**: Windows and Linux support

# Build

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11 or Linux (Ubuntu 20.04+)
- **GPU**: NVIDIA GPU with CUDA 12.8.0+ support
- **Memory**: 8GB+ RAM, 4GB+ GPU memory recommended
- **Storage**: 10GB+ free space for SDK and models

**Build Tools**

To build Audio2X SDK, you will first need the following software packages.

1. ### Windows
    - MSBuild (Visual Studio 2022+)
2. ### Linux
    - g++
    - make
3. ### Common
    Note: You can use your own dependencies or use the pre-fetched versions, which will be downloaded to `_deps\build-deps` by running `.\fetch_deps.{bat|sh}`.
    - CMake
    - Ninja (Optional)

**System Packages**

- [CUDA](https://developer.nvidia.com/cuda-toolkit) >=12.8, <13.0 (12.9 is recommended)
- [git](https://git-scm.com/) 
- [git-lfs](https://github.com/git-lfs/git-lfs)
- [python](https://www.python.org/downloads/) >= v3.8, <= v3.10.x
- [pip](https://pypi.org/project/pip/#history) >= v19.0
- [TensorRT](https://developer.nvidia.com/tensorrt) >=10.13, <11.0

## Building Audio2X SDK

1. ### Using the default build script

(Note: Use `debug` instead of `release` below for a debug build)

#### Windows
```shell
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
git lfs pull # Pull large files in sample-data
.\fetch_deps.bat release

$env:TENSORRT_ROOT_DIR="C:\path\to\tensorrt"
$env:CUDA_PATH="C:\path\to\cuda" # Usually not needed if the CUDA Toolkit installer has already set it
.\build.bat clean release # Optional: Remove previous build
.\build.bat all release # Uses CMake and Ninja from `_deps\build-deps` and builds to `_build` by default.
```

#### Linux
```shell
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
git lfs pull # Pull large files in sample-data
./fetch_deps.sh release

export TENSORRT_ROOT_DIR="path/to/tensorrt"
./build.sh clean release # Optional: Remove previous build
./build.sh all release # Uses CMake and Ninja from `_deps\build-deps` and builds to `_build` by default.
```

2. ### Using CMake

#### Windows
```shell
$env:TENSORRT_ROOT_DIR="C:\path\to\tensorrt"
$env:CUDA_PATH="C:\path\to\cuda" # Usually not needed if the CUDA Toolkit installer has already set it
cmake -B _build -G "Visual Studio 17 2022" -S . -DTENSORRT_ROOT_DIR="$env:TENSORRT_ROOT_DIR" -DCUDA_PATH="$env:CUDA_PATH" -DCMAKE_GENERATOR_TOOLSET="cuda=$env:CUDA_PATH"
cmake --build _build --target ALL_BUILD --config Release --parallel
```

#### Linux
```shell
export TENSORRT_ROOT_DIR="path/to/tensorrt"
cmake -B _build -G "Unix Makefiles" -S . -DCMAKE_BUILD_TYPE=Release
cmake --build _build --target all --config Release --parallel
```

## Build Output Structure
After a successful build, you should see a directory structure like this:

```
_build/
└── release/               # Release (or debug) build artifacts
    ├── audio2emotion-sdk/
    │   ├── bin/           # Audio2Emotion samples and unit test executables
    │   └── lib/           # Audio2Emotion static libraries
    ├── audio2face-sdk/
    │   ├── bin/           # Audio2Face samples and unit test executables
    │   └── lib/           # Audio2Face static libraries
    ├── audio2x-common/
    │   ├── bin/           # Audio2X Common unit test executables
    │   └── lib/           # Audio2X Common static libraries
    └── audio2x-sdk/       # Combines A2E + A2F + A2X Common into a single shared library
        ├── bin/           # audio2x.dll (on Windows)
        ├── include/       # Header files
        └── lib/           # Import libraries (on Windows) or libaudio2x.so (on Linux)
```

The `audio2x-sdk` directory contains the unified SDK that combines both Audio2Emotion and Audio2Face functionality into a single shared library for easy integration.

# Downloading Models and Generating Test Data

## License-protected models (Gated Models)

`Audio2Emotion` models are gated on Hugging Face and require a license click-through tied to your Hugging Face account. To download them, you must:
- Accept the model's license on its Hugging Face page (click `Agree and access repository`).
    - The default model used is https://huggingface.co/nvidia/Audio2Emotion-v2.2. Please visit the page with your Hugging Face account and accept the license. You should see the license prompt the first time you visit.  
- Authenticate the CLI so the script can use your credentials.
    - Generate a [user access token](https://huggingface.co/docs/hub/security-tokens) from your Hugging Face account.
        - Please ensure `Read access to contents of all public gated repos you can access` permission is enabled for this token.
    - Log in via the CLI using: `hf auth login`

Here's a complete example of the whole process:

1. #### Windows
```shell
# Create venv
python -m venv venv # Requires python >= v3.8, <= v3.10.x
.\venv\Scripts\activate
pip install -r deps\requirements.txt # If this step fails, please verify your Python version (python --version).

# Run these scripts in venv
hf auth login         # One-time setup: when prompted, paste the user access token you generated on Hugging Face
.\download_models.bat # Download all the Audio2Face & Audio2Emotion models

# Generate unit test data
# Convert downloaded models to TensorRT format
.\gen_testdata.bat
```

2. #### Linux
```shell
# Create venv
python -m venv venv # Requires python >= v3.8, <= v3.10.x
source ./venv/bin/activate
pip install -r deps/requirements.txt # If this step fails, please verify your Python version (python --version).

# Run these scripts in venv
hf auth login         # One-time setup: when prompted, paste the user access token you generated on Hugging Face
./download_models.sh  # Download all the Audio2Face & Audio2Emotion models

# Generate unit test data
# Convert downloaded models to TensorRT format
./gen_testdata.sh
```

# Running Audio2X SDK Unit Tests and Samples

To verify your setup is correct, run the provided samples and unit tests. This process involves several steps:

1. **Install Python dependencies** - Required packages for downloading models from Hugging Face and generating test data
2. **Download models and generate test data** - Using the provided scripts
3. **Run samples using the wrapper script** - The `run_sample.{bat|sh}` script is necessary because the SDK is a single DLL that depends on CUDA and TensorRT libraries, which must be properly located in the system PATH. 

Below are the platform-specific instructions for Windows and Linux:

1. #### Windows
```shell
# Run samples (Please ensure that the environment variables CUDA_PATH and TENSORRT_ROOT_DIR are set)
.\run_sample.bat .\_build\release\audio2face-sdk\bin\audio2face-unit-tests.exe
.\run_sample.bat .\_build\release\audio2face-sdk\bin\sample-a2f-executor.exe

# By default, the script runs a release build. To run a debug build, pass the debug argument.
.\run_sample.bat debug .\_build\debug\audio2face-sdk\bin\sample-a2f-executor.exe

# Run benchmarks
.\run_sample.bat .\_build\release\audio2face-sdk\bin\audio2face-benchmarks.exe --benchmark_filter=<filter>

# Run benchmarks with a default set of filters
.\run_sample.bat .\audio2face-sdk\source\benchmarks\test_benchmark.bat .\_build\release\audio2face-sdk\bin\audio2face-benchmarks.exe
```

2. #### Linux
```shell
# Run samples (Please ensure that the environment variables CUDA_PATH and TENSORRT_ROOT_DIR are set)
./run_sample.sh ./_build/release/audio2face-sdk/bin/audio2face-unit-tests
./run_sample.sh ./_build/release/audio2face-sdk/bin/sample-a2f-executor

# By default, the script runs a release build. To run a debug build, pass the debug argument.
./run_sample.sh debug ./_build/debug/audio2face-sdk/bin/sample-a2f-executor

# Run benchmarks
./run_sample.sh ./_build/release/audio2face-sdk/bin/audio2face-benchmarks.exe --benchmark_filter=<filter>

# Run benchmarks with a default set of filters
./run_sample.sh ./audio2face-sdk/source/benchmarks/test_benchmark.bat ./_build/release/audio2face-sdk/bin/audio2face-benchmarks.exe
```

## ✅ What to Expect After Running the Samples

- All unit tests should pass
- Sample executables should complete without any errors

    The sample does not include a GUI, so there is no visualization of the generated vertex positions.  
    To view the results, you can either:
    - Export the data to a `.bin` file and visualize it in a DCC (Digital Content Creation) tool of your choice, or
    - Use [Maya-ACE](https://github.com/NVIDIA/Maya-ACE) for direct integration with Autodesk Maya.

## ⚠️ Common Issues and Troubleshooting

If you encounter errors, here are some common causes:

1. `build.bat` shows "Visual Studio installation not found"

    Visual Studio with the C++ compiler toolchain was not found. Please install it or set the `VS_PATH` variable manually in `build.bat`.

2. `build.bat` shows "TENSORRT_ROOT_DIR is not defined"

    Make sure the `TENSORRT_ROOT_DIR` environment variable points to your TensorRT directory.

3. Samples printed `[A2F SDK] [ERROR] Unable to parse file...`

    Make sure to run the download_models and gen_testdata scripts before running the samples or unit tests. These scripts will create the required `_data\generated` directory.

4. `.\venv\Scripts\Activate.ps1` cannot be loaded because running scripts is disabled on this system.

    You need to allow PowerShell to run local scripts. To fix this, open PowerShell and run:
    ```shell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
    Please check [about_Execution_Policies - Powershell | Microsoft learn](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies) for more details.

# Getting Started with Development

Now that you've set up the SDK, here are some recommended next steps to explore and get the most out of it:

### Read the High-Level Overview
Check out the [high-level overview document](docs/) to understand the architecture, core concepts, and key components in the SDK.

### Explore the Samples
Check out the provided samples to see example code and typical use cases for the SDK:
- [Audio2Face Samples](audio2face-sdk/source/samples/)
- [Audio2Emotion Samples](audio2emotion-sdk/source/samples/)

### Try the Maya Plugin
[Maya-ACE](https://github.com/NVIDIA/Maya-ACE) includes a local inference player node that demonstrates direct SDK integration. Setup is more complex than the samples but provides visual results.

### Hugging Face Pretrained Models & Custom Training
Browse the [Audio2Face-3D Hugging Face Collection](https://huggingface.co/collections/nvidia/audio2face-3d-6865d22d6daec4ac85887b17) for available models compatible with this SDK, or use the [Audio2Face-3D Training Framework](https://github.com/NVIDIA/Audio2Face-3D-Training-Framework) to customize and train your own models!


# Citation

If you use Audio2Face-3D Training Framework or Audio2Face-3D models in publications or other outputs, please use citations in the following format (BibTeX entry for LaTeX):

```bibtex
@misc{
      nvidia2025audio2face3d,
      title={Audio2Face-3D: Audio-driven Realistic Facial Animation For Digital Avatars},
      author={Chaeyeon Chung and Ilya Fedorov and Michael Huang and Aleksey Karmanov and Dmitry Korobchenko and Roger Ribera and Yeongho Seol},
      year={2025},
      eprint={2508.16401},
      archivePrefix={arXiv},
      primaryClass={cs.GR},
      url={https://arxiv.org/abs/2508.16401},
      note={Authors listed in alphabetical order}
}
```