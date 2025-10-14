from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
import subprocess
import tempfile
import json
import uuid
from datetime import datetime
from pathlib import Path
import numpy as np


app = FastAPI(title="Audio2X Service Enhanced", version="1.0.0")

# Создаем папки для результатов
RESULTS_DIR = Path("/app/results")
RESULTS_DIR.mkdir(exist_ok=True)

# Монтируем статические файлы для скачивания
app.mount("/downloads", StaticFiles(directory=str(RESULTS_DIR)), name="downloads")


def _build_path(build_type: str, rel: str) -> str:
    base = f"/app/_build/{build_type}"
    return os.path.join(base, rel)


def _run(cmd, cwd=None):
    try:
        proc = subprocess.run(
            cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            text=True, cwd=cwd
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-20000:],  # clamp
            "stderr": proc.stderr[-20000:],
        }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def _extract_audio_info(stdout: str) -> dict:
    """Извлекает информацию об аудио из stdout"""
    info = {}
    lines = stdout.split('\n')
    
    for line in lines:
        if 'Num Channels:' in line:
            info['channels'] = int(line.split(':')[1].strip())
        elif 'Num Samples Per Channel:' in line:
            info['samples'] = int(line.split(':')[1].strip())
        elif 'Sample Rate:' in line:
            info['sample_rate'] = int(line.split(':')[1].strip())
        elif 'Bit Depth:' in line:
            info['bit_depth'] = int(line.split(':')[1].strip())
        elif 'Length in Seconds:' in line:
            info['duration'] = float(line.split(':')[1].strip())
    
    return info


def _extract_frame_info(stdout: str) -> dict:
    """Извлекает информацию о обработанных кадрах"""
    frames_info = {}
    lines = stdout.split('\n')
    
    for line in lines:
        if 'Track' in line and 'processed' in line and 'frames' in line:
            parts = line.split()
            track_num = int(parts[1])
            frames_count = int(parts[3])
            frames_info[f'track_{track_num}'] = frames_count
    
    return frames_info


def _create_result_summary(audio_info: dict, frames_info: dict, result_id: str) -> dict:
    """Создает сводку результатов"""
    return {
        "result_id": result_id,
        "timestamp": datetime.now().isoformat(),
        "audio_info": audio_info,
        "processing_info": frames_info,
        "total_frames": sum(frames_info.values()),
        "download_url": f"/downloads/{result_id}",
        "status": "completed"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "build_type": os.getenv("BUILD_TYPE", "release"),
        "cuda_path": os.getenv("CUDA_PATH", ""),
        "tensorrt_root": os.getenv("TENSORRT_ROOT_DIR", ""),
        "results_dir": str(RESULTS_DIR),
    }


@app.post("/infer/emotions")
async def infer_emotions(audio: UploadFile = File(...)):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2emotion-sdk/bin/sample-a2e-executor")
    
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(
            status_code=500,
            content={"error": f"Binary not found or not executable: {binary}"},
        )

    result_id = str(uuid.uuid4())
    result_dir = RESULTS_DIR / result_id
    result_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        # Запускаем обработку
        result = _run([binary, wav_path])
        
        if result["returncode"] != 0:
            return JSONResponse(
                status_code=500,
                content={"error": "Processing failed", "details": result}
            )

        # Извлекаем информацию
        audio_info = _extract_audio_info(result["stdout"])
        
        # Сохраняем результаты
        result_file = result_dir / "emotion_result.json"
        with open(result_file, "w") as f:
            json.dump({
                "audio_info": audio_info,
                "processing_output": result["stdout"],
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

        # Создаем сводку
        summary = _create_result_summary(audio_info, {}, result_id)
        
        return {
            "success": True,
            "result": summary,
            "message": "Emotion analysis completed successfully"
        }


@app.post("/infer/blendshapes")
async def infer_blendshapes(audio: UploadFile = File(...)):
    build_type = os.getenv("BUILD_TYPE", "release")
    binary = _build_path(build_type, "audio2face-sdk/bin/sample-a2f-executor")
    
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return JSONResponse(
            status_code=500,
            content={"error": f"Binary not found or not executable: {binary}"},
        )

    result_id = str(uuid.uuid4())
    result_dir = RESULTS_DIR / result_id
    result_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "input.wav")
        with open(wav_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        # Запускаем обработку
        result = _run([binary, wav_path])
        
        if result["returncode"] != 0:
            return JSONResponse(
                status_code=500,
                content={"error": "Processing failed", "details": result}
            )

        # Извлекаем информацию
        audio_info = _extract_audio_info(result["stdout"])
        frames_info = _extract_frame_info(result["stdout"])
        
        # Копируем эталонные данные модели (как пример результата)
        model_data_path = "/app/_data/generated/audio2face-sdk/samples/data/mark/model_data.npz"
        if os.path.exists(model_data_path):
            shutil.copy2(model_data_path, result_dir / "model_data.npz")
            
            # Читаем и анализируем данные модели
            try:
                model_data = np.load(model_data_path)
                model_info = {
                    "keys": list(model_data.keys()),
                    "shapes": {k: list(model_data[k].shape) for k in model_data.keys()},
                    "description": {
                        "shapes_matrix_skin": f"Skin blendshapes: {model_data['shapes_matrix_skin'].shape[0]} shapes, {model_data['shapes_matrix_skin'].shape[1]} vertices",
                        "shapes_matrix_tongue": f"Tongue blendshapes: {model_data['shapes_matrix_tongue'].shape[0]} shapes, {model_data['shapes_matrix_tongue'].shape[1]} vertices",
                        "neutral_jaw": f"Jaw neutral position: {model_data['neutral_jaw'].shape[0]} points",
                        "eye_animations": f"Eye animation data: {model_data['saccade_rot_matrix'].shape[0]} frames"
                    }
                }
            except Exception as e:
                model_info = {"error": f"Could not analyze model data: {str(e)}"}
        else:
            model_info = {"error": "Model data not found"}

        # Сохраняем результаты
        result_file = result_dir / "blendshape_result.json"
        with open(result_file, "w") as f:
            json.dump({
                "audio_info": audio_info,
                "processing_info": frames_info,
                "model_info": model_info,
                "processing_output": result["stdout"],
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

        # Создаем сводку
        summary = _create_result_summary(audio_info, frames_info, result_id)
        summary["model_info"] = model_info
        
        return {
            "success": True,
            "result": summary,
            "message": "Blendshape generation completed successfully"
        }


@app.get("/results/{result_id}")
async def get_result(result_id: str):
    """Получить информацию о результате"""
    result_dir = RESULTS_DIR / result_id
    
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Ищем JSON файл с результатами
    json_files = list(result_dir.glob("*.json"))
    if not json_files:
        raise HTTPException(status_code=404, detail="Result data not found")
    
    with open(json_files[0], "r") as f:
        result_data = json.load(f)
    
    return {
        "result_id": result_id,
        "files": [f.name for f in result_dir.iterdir()],
        "data": result_data
    }


@app.get("/results/{result_id}/download/{filename}")
async def download_file(result_id: str, filename: str):
    """Скачать файл результата"""
    result_dir = RESULTS_DIR / result_id
    
    if not result_dir.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    
    file_path = result_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )


@app.get("/results")
async def list_results():
    """Список всех результатов"""
    results = []
    
    for result_dir in RESULTS_DIR.iterdir():
        if result_dir.is_dir():
            json_files = list(result_dir.glob("*.json"))
            if json_files:
                with open(json_files[0], "r") as f:
                    data = json.load(f)
                
                results.append({
                    "result_id": result_dir.name,
                    "timestamp": data.get("timestamp", "unknown"),
                    "type": "blendshapes" if "model_info" in data else "emotions",
                    "files": [f.name for f in result_dir.iterdir()]
                })
    
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
