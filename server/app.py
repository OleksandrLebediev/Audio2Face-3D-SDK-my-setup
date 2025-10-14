from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
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


@app.post("/infer/emotions.csv")
async def infer_emotions_csv(audio: UploadFile = File(...)):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2emotion-sdk/bin/a2e_csv")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(
            status_code=500,
            content={"error": f"Binary not found or not executable: {binary}"},
        )

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        # Expect model path from ENV or default test dir
        model_json = os.getenv("A2E_MODEL_JSON", "/app/_data/generated/audio2emotion-sdk/samples/model/model.json")
        if not os.path.isfile(model_json):
            return JSONResponse(status_code=500, content={"error": f"A2E model not found: {model_json}"})
        proc = subprocess.Popen([binary, "-i", wav_path, "-m", model_json], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return StreamingResponse(proc.stdout, media_type="text/csv")


@app.post("/infer/blendshapes.csv")
async def infer_blendshapes_csv(audio: UploadFile = File(...), model_type: str = "regression", fps: int = 60, identity: int = 0, gpu_solver: bool = False):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2face-sdk/bin/a2f_weights_csv")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(
            status_code=500,
            content={"error": f"Binary not found or not executable: {binary}"},
        )

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        model_json = os.getenv("A2F_MODEL_JSON", "/app/_data/generated/audio2face-sdk/samples/data/mark/model.json")
        if not os.path.isfile(model_json):
            return JSONResponse(status_code=500, content={"error": f"A2F model not found: {model_json}"})
        args = [binary, "-i", wav_path, "--type", model_type, "--model", model_json, "--fps", str(fps), "--identity", str(identity)]
        if gpu_solver:
            args += ["--gpu-solver", "true"]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return StreamingResponse(proc.stdout, media_type="text/csv")


@app.post("/infer/combined.csv")
async def infer_combined_csv(audio: UploadFile = File(...), model_type: str = "regression", fps: int = 60, identity: int = 0, gpu_solver: bool = False):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2face-sdk/bin/a2f_a2e_combined_csv")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(status_code=500, content={"error": f"Binary not found or not executable: {binary}"})

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        a2e_model = os.getenv("A2E_MODEL_JSON", "/app/_data/generated/audio2emotion-sdk/samples/model/model.json")
        a2f_model = os.getenv("A2F_MODEL_JSON", "/app/_data/generated/audio2face-sdk/samples/data/mark/model.json")
        if not os.path.isfile(a2e_model) or not os.path.isfile(a2f_model):
            return JSONResponse(status_code=500, content={"error": "Models not found", "a2e": a2e_model, "a2f": a2f_model})
        args = [binary, "-i", wav_path, "--a2e-model", a2e_model, "--type", model_type, "--a2f-model", a2f_model, "--fps", str(fps), "--identity", str(identity)]
        if gpu_solver:
            args += ["--gpu-solver", "true"]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return StreamingResponse(proc.stdout, media_type="text/csv")


@app.post("/infer/geometry.npz")
async def infer_geometry_npz(audio: UploadFile = File(...), model_type: str = "regression", fps: int = 60, identity: int = 0):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2face-sdk/bin/a2f_geometry_npz")
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(status_code=500, content={"error": f"Binary not found or not executable: {binary}"})

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        out_path = os.path.join(td, "geometry.npz")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        model_json = os.getenv("A2F_MODEL_JSON", "/app/_data/generated/audio2face-sdk/samples/data/mark/model.json")
        if not os.path.isfile(model_json):
            return JSONResponse(status_code=500, content={"error": f"A2F model not found: {model_json}"})
        args = [binary, "-i", wav_path, "--type", model_type, "--model", model_json, "--fps", str(fps), "--identity", str(identity), "-o", out_path]
        proc = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return JSONResponse(status_code=500, content={"error": "processing failed", "stderr": proc.stderr[-20000:]})
        def _iterfile():
            with open(out_path, "rb") as f:
                yield from iter(lambda: f.read(1024 * 64), b"")
        return StreamingResponse(_iterfile(), media_type="application/octet-stream")






