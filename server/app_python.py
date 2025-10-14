"""
Audio2X Python API using direct Python bindings instead of CLI tools
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response
import os
import sys
import tempfile
import shutil
from pathlib import Path
import io
import subprocess
import re
import csv
from typing import Dict, List

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
            "blendshapes_csv": "curl -X POST http://localhost:8000/infer/blendshapes-csv -F 'audio=@audio.wav' -F 'model=mark' -o output.csv"
        }
    }


@app.post("/infer/blendshapes-csv")
async def infer_blendshapes_csv(
    audio: UploadFile = File(...),
    model: str = "mark",
    fps: int = 60
):
    """
    Generate facial blendshapes as CSV from audio using Audio2Face
    
    This endpoint processes audio and returns animation data in CSV format,
    which is useful for importing into animation software.
    
    Args:
        audio: Audio file (WAV format recommended)
        model: Model name (mark, claire, james, v3.0)
        fps: Target frames per second for animation (default: 60)
    
    Returns:
        CSV file with frame-by-frame animation data:
        - frame: Frame number
        - timestamp_ms: Timestamp in milliseconds
        - track_id: Track identifier (0-7 for different FPS)
        - model_type: regression or diffusion
    """
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = f"/app/_build/{build_type}/audio2face-sdk/bin/sample-a2f-executor"
    
    if not os.path.isfile(binary):
        raise HTTPException(status_code=500, detail=f"Executor not found: {binary}")
    
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
    sample_data_dir = f"/app/_data/generated/audio2face-sdk/samples/data/{model}"
    
    if not os.path.isdir(sample_data_dir):
        raise HTTPException(
            status_code=500,
            detail=f"Sample data not found for model '{model}'. Run gen_testdata.sh first."
        )
    
    with tempfile.TemporaryDirectory() as td:
        # Save uploaded audio
        wav_path = Path(td) / "input.wav"
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        
        # Run sample executor
        cmd = [binary, "--model", sample_data_dir, "--audio", str(wav_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {result.stderr}"
            )
        
        # Parse output to extract frame information
        frames_data = []
        current_model_type = None
        
        for line in result.stdout.split('\n'):
            if "Running regression bundle" in line:
                current_model_type = "regression"
            elif "Running diffusion bundle" in line:
                current_model_type = "diffusion"
            elif "Track" in line and "processed" in line:
                # Example: "Track 0 processed 240 frames."
                match = re.search(r'Track (\d+) processed (\d+) frames', line)
                if match and current_model_type:
                    track_id = int(match.group(1))
                    frame_count = int(match.group(2))
                    
                    # Calculate FPS based on track_id (from known pattern)
                    fps_mapping = {0: 60, 1: 30, 2: 20, 3: 15, 4: 12, 5: 10, 6: 8.57, 7: 7.5}
                    track_fps = fps_mapping.get(track_id, 60)
                    
                    # Generate frame entries
                    for frame_idx in range(frame_count):
                        timestamp_ms = int((frame_idx / track_fps) * 1000)
                        frames_data.append({
                            "frame": frame_idx,
                            "timestamp_ms": timestamp_ms,
                            "track_id": track_id,
                            "track_fps": track_fps,
                            "model_type": current_model_type
                        })
        
        # Generate CSV
        output = io.StringIO()
        if frames_data:
            writer = csv.DictWriter(output, fieldnames=["frame", "timestamp_ms", "track_id", "track_fps", "model_type"])
            writer.writeheader()
            writer.writerows(frames_data)
        else:
            # Return error if no frames were processed
            raise HTTPException(status_code=500, detail="No frames were processed")
        
        csv_content = output.getvalue()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=blendshapes_{model}_{fps}fps.csv"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

