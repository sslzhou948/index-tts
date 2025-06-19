"""
Mock IndexTTS module for testing API server functionality
This is a simplified version for demonstration purposes
"""

import time
import logging
import numpy as np
import soundfile as sf
from pathlib import Path

logger = logging.getLogger(__name__)

class IndexTTS:
    """Mock IndexTTS class for testing"""
    
    def __init__(self, model_dir="checkpoints", cfg_path=None):
        self.model_dir = model_dir
        self.cfg_path = cfg_path
        self.device = "cpu"  # Mock device
        self.is_fp16 = False
        self.model_ver = "mock-1.0"
        
        logger.info(f"Mock IndexTTS initialized with model_dir: {model_dir}")
        
    def infer(self, audio_prompt, text, output_path, **kwargs):
        """Mock inference method"""
        logger.info(f"Mock inference: text='{text[:50]}...', audio_prompt={audio_prompt}")
        
        # Simulate processing time
        time.sleep(1)
        
        # Generate mock audio (1 second of sine wave)
        sample_rate = 22050
        duration = 1.0
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Save mock audio file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, audio, sample_rate)
        
        logger.info(f"Mock audio saved to: {output_path}")
        return output_path
