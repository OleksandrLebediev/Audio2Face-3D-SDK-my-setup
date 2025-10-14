"""
Audio2X Python API using direct Python bindings instead of CLI tools
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import os
import sys
import tempfile
import shutil
from pathlib import Path
import io

# Add SDK to path
sys.path.insert(0, "/app/_build/release/audio2x-sdk/lib")

app = FastAPI(title="Audio2X Python Service", version="1.0.0")


@app.get("/health")
def health():
    """Health check endpoint"""
    try:
        # Try to import the SDK
        import audio2x
        sdk_available = True
        sdk_version = getattr(audio2x, '__version__', 'unknown')
    except ImportError as e:
        sdk_available = False
        sdk_version = f"Import error: {str(e)}"
    
    return {
        "status": "ok",
        "sdk_available": sdk_available,
        "sdk_version": sdk_version,
        "build_type": os.getenv("BUILD_TYPE", "release"),
        "cuda_path": os.getenv("CUDA_PATH", ""),
        "tensorrt_root": os.getenv("TENSORRT_ROOT_DIR", ""),
        "python_path": sys.path[:3],
    }


@app.get("/models")
def list_models():
    """List available models"""
    models_dir = Path("/app/_data/audio2face-models")
    
    if not models_dir.exists():
        return {"error": "Models directory not found", "path": str(models_dir)}
    
    models = []
    for model_dir in models_dir.iterdir():
        if model_dir.is_dir():
            model_json = model_dir / "model.json"
            if model_json.exists():
                models.append({
                    "name": model_dir.name,
                    "path": str(model_json),
                    "exists": True
                })
    
    return {
        "models_directory": str(models_dir),
        "available_models": models,
        "count": len(models)
    }


@app.post("/infer/blendshapes")
async def infer_blendshapes(
    audio: UploadFile = File(...), 
    model: str = "mark",
    return_format: str = "json"
):
    """
    Generate facial blendshapes from audio using Audio2Face
    
    Args:
        audio: WAV audio file (16kHz, mono, s16le recommended)
        model: Model name (mark, claire, james, v3.0)
        return_format: Response format - "json" or "summary" (default: json)
    
    Returns:
        JSON with processing results. If successful, includes:
        - success: bool
        - audio_info: dict with filename and size
        - model: str - model used
        - processing_summary: dict with tracks processed and frame counts
        - stdout/stderr: process output for debugging
    """
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = f"/app/_build/{build_type}/audio2face-sdk/bin/sample-a2f-executor"
    
    if not os.path.isfile(binary):
        raise HTTPException(status_code=500, detail=f"Executable not found: {binary}")
    
    # Map model names to paths  
    model_map = {
        "mark": "/app/_data/audio2face-models/audio2face-3d-v2.3-mark",
        "claire": "/app/_data/audio2face-models/audio2face-3d-v2.3.1-claire",
        "james": "/app/_data/audio2face-models/audio2face-3d-v2.3.1-james",
        "v3.0": "/app/_data/audio2face-models/audio2face-3d-v3.0",
    }
    
    model_path = model_map.get(model)
    if not model_path or not os.path.exists(model_path):
        raise HTTPException(status_code=400, detail=f"Invalid or missing model: {model}")
    
    with tempfile.TemporaryDirectory() as td:
        # Save uploaded audio
        wav_path = Path(td) / "input.wav"
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        
        try:
            # Run the sample executor
            import subprocess
            import re
            
            result = subprocess.run(
                [binary, str(wav_path)],
                env={
                    **os.environ,
                    "CUDA_PATH": os.getenv("CUDA_PATH", "/usr/local/cuda"),
                    "TENSORRT_ROOT_DIR": os.getenv("TENSORRT_ROOT_DIR", "/usr/lib/x86_64-linux-gnu"),
                },
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse processing summary from stdout
            processing_summary = {}
            if result.returncode == 0 and result.stdout:
                # Extract track processing info: "Track 0 processed 240 frames."
                track_pattern = r"Track (\d+) processed (\d+) frames\."
                tracks = re.findall(track_pattern, result.stdout)
                if tracks:
                    processing_summary["tracks"] = [
                        {"track_id": int(tid), "frames": int(frames)} 
                        for tid, frames in tracks
                    ]
                    processing_summary["total_tracks"] = len(tracks)
                    processing_summary["total_frames"] = sum(int(f) for _, f in tracks)
                
                # Extract audio info
                duration_match = re.search(r"Length in Seconds: (\d+)", result.stdout)
                if duration_match:
                    processing_summary["audio_duration_sec"] = int(duration_match.group(1))
            
            response = {
                "success": result.returncode == 0,
                "audio_info": {
                    "filename": audio.filename,
                    "size_bytes": wav_path.stat().st_size,
                },
                "model": model,
                "model_path": model_path,
                "processing_summary": processing_summary,
                "returncode": result.returncode,
            }
            
            # Add full output for debugging if requested or on error
            if return_format == "json" or result.returncode != 0:
                response["stdout"] = result.stdout[-5000:] if result.stdout else ""
                response["stderr"] = result.stderr[-5000:] if result.stderr else ""
            
            return response
            
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Processing timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "service": "Audio2X Python Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health - Check service health and SDK status",
            "models": "/models - List available models",
            "docs": "/docs - Interactive API documentation",
            "infer_blendshapes": "POST /infer/blendshapes - Generate facial blendshapes from audio",
        },
        "examples": {
            "blendshapes_full": "curl -X POST http://localhost:8000/infer/blendshapes -F 'audio=@audio.wav' -F 'model=mark' -F 'return_format=json'",
            "blendshapes_summary": "curl -X POST http://localhost:8000/infer/blendshapes -F 'audio=@audio.wav' -F 'model=mark' -F 'return_format=summary'",
            "blendshapes_csv": "curl -X POST http://localhost:8000/infer/blendshapes-csv -F 'audio=@audio.wav' -F 'model=mark' -F 'fps=60' -o output.csv",
            "geometry_npz": "curl -X POST http://localhost:8000/infer/geometry-npz -F 'audio=@audio.wav' -F 'model=mark' -o output.npz"
        }
    }


@app.post("/infer/blendshapes-csv")
async def infer_blendshapes_csv(
    audio: UploadFile = File(...),
    model: str = "mark",
    fps: int = 60
):
    """
    Generate facial blendshapes CSV from audio using Audio2Face
    
    Args:
        audio: WAV audio file
        model: Model name (mark, claire, james, v3.0)
        fps: Frames per second (default: 60)
    
    Returns:
        CSV file with blendshapes weights
    """
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = f"/app/_build/{build_type}/audio2face-sdk/bin/a2f_weights_csv"
    
    if not os.path.isfile(binary):
        raise HTTPException(status_code=500, detail=f"Tool not found: {binary}")
    
    # Map model names to paths
    model_map = {
        "mark": "/app/_data/audio2face-models/audio2face-3d-v2.3-mark",
        "claire": "/app/_data/audio2face-models/audio2face-3d-v2.3.1-claire",
        "james": "/app/_data/audio2face-models/audio2face-3d-v2.3.1-james",
        "v3.0": "/app/_data/audio2face-models/audio2face-3d-v3.0"
    }
    
    if model not in model_map:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}. Available: {list(model_map.keys())}")
    
    model_path = model_map[model]
    
    with tempfile.TemporaryDirectory() as td:
        # Save uploaded audio
        wav_path = Path(td) / "input.wav"
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        
        # Output CSV path
        csv_path = Path(td) / "output.csv"
        
        # Run a2f_weights_csv
        import subprocess
        cmd = [
            binary,
            "--audio", str(wav_path),
            "--model", model_path,
            "--out", str(csv_path),
            "--fps", str(fps)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0 or not csv_path.exists():
            return {
                "success": False,
                "error": "Failed to generate CSV",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        # Read CSV content
        csv_content = csv_path.read_text()
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=blendshapes_{model}_{fps}fps.csv"
            }
        )


@app.post("/infer/geometry-npz")
async def infer_geometry_npz(
    audio: UploadFile = File(...),
    model: str = "mark"
):
    """
    Generate facial geometry (skin, tongue, jaw, eyes) from audio as NPZ file
    
    Args:
        audio: WAV audio file
        model: Model name (mark, claire, james, v3.0)
    
    Returns:
        NPZ file with geometry data
    """
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = f"/app/_build/{build_type}/audio2face-sdk/bin/a2f_geometry_npz"
    
    if not os.path.isfile(binary):
        raise HTTPException(status_code=500, detail=f"Tool not found: {binary}")
    
    # Map model names to paths
    model_map = {
        "mark": "/app/_data/audio2face-models/audio2face-3d-v2.3-mark",
        "claire": "/app/_data/audio2face-models/audio2face-3d-v2.3.1-claire",
        "james": "/app/_data/audio2face-models/audio2face-3d-v2.3.1-james",
        "v3.0": "/app/_data/audio2face-models/audio2face-3d-v3.0"
    }
    
    if model not in model_map:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}. Available: {list(model_map.keys())}")
    
    model_path = model_map[model]
    
    with tempfile.TemporaryDirectory() as td:
        # Save uploaded audio
        wav_path = Path(td) / "input.wav"
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        
        # Output NPZ path
        npz_path = Path(td) / "output.npz"
        
        # Run a2f_geometry_npz
        import subprocess
        cmd = [
            binary,
            "--audio", str(wav_path),
            "--model", model_path,
            "--out", str(npz_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0 or not npz_path.exists():
            return {
                "success": False,
                "error": "Failed to generate NPZ",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        # Read NPZ content
        npz_content = npz_path.read_bytes()
        
        return StreamingResponse(
            io.BytesIO(npz_content),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=geometry_{model}.npz"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

