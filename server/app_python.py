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


@app.post("/infer/simple")
async def infer_simple(audio: UploadFile = File(...)):
    """
    Simple inference endpoint that processes audio and returns basic info
    This is a placeholder that will be expanded once we verify SDK availability
    """
    with tempfile.TemporaryDirectory() as td:
        # Save uploaded audio
        wav_path = Path(td) / "input.wav"
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        
        # Get file size
        file_size = wav_path.stat().st_size
        
        return {
            "success": True,
            "audio_received": {
                "filename": audio.filename,
                "content_type": audio.content_type,
                "size_bytes": file_size,
            },
            "message": "Audio received successfully. SDK integration in progress.",
            "note": "Use /health to check SDK availability"
        }


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
            "infer_simple": "POST /infer/simple - Simple audio inference (placeholder)",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

