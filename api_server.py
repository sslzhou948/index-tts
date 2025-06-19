#!/usr/bin/env python3
"""
FastAPI-based REST API server for IndexTTS
Provides HTTP endpoints for text-to-speech synthesis
"""

import os
import sys
import time
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "indextts"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import IndexTTS after path setup
try:
    from indextts.infer import IndexTTS
except ImportError as e:
    logger.error(f"Failed to import IndexTTS: {e}")
    sys.exit(1)

# Global TTS instance
tts_instance = None
executor = ThreadPoolExecutor(max_workers=2)

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    voice_file: Optional[str] = Field(None, description="Path to reference voice file")
    output_filename: Optional[str] = Field(None, description="Output filename (without extension)")
    
    # Advanced parameters
    do_sample: bool = Field(True, description="Whether to use sampling")
    top_p: float = Field(0.8, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: int = Field(30, ge=0, le=100, description="Top-k sampling parameter")
    temperature: float = Field(1.0, ge=0.1, le=2.0, description="Temperature for sampling")
    length_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="Length penalty")
    num_beams: int = Field(3, ge=1, le=10, description="Number of beams for beam search")
    repetition_penalty: float = Field(10.0, ge=0.1, le=20.0, description="Repetition penalty")
    max_mel_tokens: int = Field(600, ge=50, le=2000, description="Maximum mel tokens")
    max_text_tokens_per_sentence: int = Field(120, ge=20, le=500, description="Max tokens per sentence")

class TTSResponse(BaseModel):
    success: bool
    message: str
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    task_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    version: str

# Initialize FastAPI app
app = FastAPI(
    title="IndexTTS API",
    description="REST API for IndexTTS - Industrial-Level Text-to-Speech System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def initialize_tts():
    """Initialize the TTS model"""
    global tts_instance
    
    model_dir = os.environ.get("MODEL_DIR", "checkpoints")
    config_path = os.environ.get("CONFIG_PATH", os.path.join(model_dir, "config.yaml"))
    
    if not os.path.exists(model_dir):
        logger.error(f"Model directory {model_dir} does not exist")
        return False
        
    if not os.path.exists(config_path):
        logger.error(f"Config file {config_path} does not exist")
        return False
    
    # Check for required model files
    required_files = [
        "bigvgan_generator.pth",
        "bpe.model", 
        "gpt.pth",
        "config.yaml"
    ]
    
    for file in required_files:
        file_path = os.path.join(model_dir, file)
        if not os.path.exists(file_path):
            logger.error(f"Required model file {file_path} does not exist")
            return False
    
    try:
        logger.info("Initializing IndexTTS model...")
        tts_instance = IndexTTS(
            model_dir=model_dir,
            cfg_path=config_path
        )
        logger.info(f"IndexTTS model loaded successfully on device: {tts_instance.device}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize IndexTTS: {e}")
        return False

def run_tts_inference(
    text: str,
    voice_file: str,
    output_path: str,
    **kwargs
) -> Dict[str, Any]:
    """Run TTS inference in a separate thread"""
    try:
        start_time = time.time()
        
        # Run inference
        result = tts_instance.infer(
            audio_prompt=voice_file,
            text=text,
            output_path=output_path,
            **kwargs
        )
        
        duration = time.time() - start_time
        
        return {
            "success": True,
            "output_path": result,
            "duration": duration
        }
    except Exception as e:
        logger.error(f"TTS inference failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.on_event("startup")
async def startup_event():
    """Initialize the TTS model on startup"""
    success = initialize_tts()
    if not success:
        logger.error("Failed to initialize TTS model. Server will start but TTS endpoints will not work.")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if tts_instance is not None else "unhealthy",
        model_loaded=tts_instance is not None,
        device=tts_instance.device if tts_instance else "unknown",
        version="1.0.0"
    )

@app.post("/tts/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    voice_file: UploadFile = File(...),
    output_filename: Optional[str] = Form(None),
    do_sample: bool = Form(True),
    top_p: float = Form(0.8),
    top_k: int = Form(30),
    temperature: float = Form(1.0),
    length_penalty: float = Form(0.0),
    num_beams: int = Form(3),
    repetition_penalty: float = Form(10.0),
    max_mel_tokens: int = Form(600),
    max_text_tokens_per_sentence: int = Form(120)
):
    """Synthesize speech from text and reference voice"""
    
    if tts_instance is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Validate voice file
    if not voice_file.filename.lower().endswith(('.wav', '.mp3', '.flac')):
        raise HTTPException(status_code=400, detail="Voice file must be in WAV, MP3, or FLAC format")
    
    try:
        # Create temporary file for uploaded voice
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_voice:
            content = await voice_file.read()
            temp_voice.write(content)
            temp_voice_path = temp_voice.name
        
        # Generate output filename
        if not output_filename:
            output_filename = f"tts_output_{int(time.time())}"
        
        output_path = os.path.join("outputs", f"{output_filename}.wav")
        os.makedirs("outputs", exist_ok=True)
        
        # Prepare inference parameters
        inference_params = {
            "do_sample": do_sample,
            "top_p": top_p,
            "top_k": top_k if top_k > 0 else None,
            "temperature": temperature,
            "length_penalty": length_penalty,
            "num_beams": num_beams,
            "repetition_penalty": repetition_penalty,
            "max_mel_tokens": max_mel_tokens,
            "max_text_tokens_per_sentence": max_text_tokens_per_sentence
        }
        
        # Run inference in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            run_tts_inference,
            text,
            temp_voice_path,
            output_path,
            **inference_params
        )
        
        # Clean up temporary voice file
        background_tasks.add_task(lambda: os.unlink(temp_voice_path))
        
        if result["success"]:
            return TTSResponse(
                success=True,
                message="Speech synthesis completed successfully",
                audio_url=f"/audio/{output_filename}.wav",
                duration=result["duration"]
            )
        else:
            raise HTTPException(status_code=500, detail=f"TTS inference failed: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in synthesize_speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio files"""
    file_path = os.path.join("outputs", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename=filename
    )

@app.get("/models/info")
async def get_model_info():
    """Get information about the loaded model"""
    if tts_instance is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    return {
        "model_version": getattr(tts_instance, 'model_ver', 'unknown'),
        "device": tts_instance.device,
        "fp16_enabled": tts_instance.is_fp16,
        "cuda_kernel_enabled": getattr(tts_instance, 'use_cuda_kernel', False)
    }

@app.post("/models/reload")
async def reload_model():
    """Reload the TTS model"""
    global tts_instance
    tts_instance = None
    
    success = initialize_tts()
    if success:
        return {"message": "Model reloaded successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reload model")

if __name__ == "__main__":
    # Configuration from environment variables
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    workers = int(os.environ.get("API_WORKERS", "1"))
    
    logger.info(f"Starting IndexTTS API server on {host}:{port}")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
        access_log=True
    )
