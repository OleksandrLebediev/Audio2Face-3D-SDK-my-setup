from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import shutil
import subprocess
import tempfile


app = FastAPI(title="Audio2X Service", version="0.1.0")


def _build_path(build_type: str, rel: str) -> str:
    base = f"/app/_build/{build_type}"
    return os.path.join(base, rel)


def _run(cmd):
    try:
        proc = subprocess.run(
            cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-20000:],  # clamp
            "stderr": proc.stderr[-20000:],
        }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "build_type": os.getenv("BUILD_TYPE", "release"),
        "cuda_path": os.getenv("CUDA_PATH", ""),
        "tensorrt_root": os.getenv("TENSORRT_ROOT_DIR", ""),
    }


@app.post("/infer/emotions")
async def infer_emotions(audio: UploadFile = File(...)):
    build_type = os.getenv("BUILD_TYPE", "release")
    # Sample binary path (if built)
    binary = _build_path(build_type, "audio2emotion-sdk/bin/sample-a2e-executor")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(
            status_code=500,
            content={"error": f"Binary not found or not executable: {binary}"},
        )

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        # The sample executables accept CLI arguments documented in sample README.
        # If no args are given, they typically run on embedded sample assets. We pass the file.
        result = _run([binary, wav_path])
        return result


@app.post("/infer/blendshapes")
async def infer_blendshapes(audio: UploadFile = File(...)):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2face-sdk/bin/sample-a2f-executor")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(
            status_code=500,
            content={"error": f"Binary not found or not executable: {binary}"},
        )

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        result = _run([binary, wav_path])
        return result





