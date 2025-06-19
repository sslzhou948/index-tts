#!/usr/bin/env python3
"""
Model download script for IndexTTS
Downloads required model files from HuggingFace
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model configurations
MODELS = {
    "IndexTTS-1.5": {
        "repo": "IndexTeam/IndexTTS-1.5",
        "files": [
            "config.yaml",
            "bigvgan_discriminator.pth", 
            "bigvgan_generator.pth",
            "bpe.model",
            "dvae.pth",
            "gpt.pth",
            "unigram_12000.vocab"
        ]
    },
    "IndexTTS-1.0": {
        "repo": "IndexTeam/IndexTTS",
        "files": [
            "config.yaml",
            "bigvgan_discriminator.pth",
            "bigvgan_generator.pth", 
            "bpe.model",
            "dvae.pth",
            "gpt.pth",
            "unigram_12000.vocab"
        ]
    }
}

def check_huggingface_cli():
    """Check if huggingface-cli is available"""
    try:
        result = subprocess.run(["huggingface-cli", "--version"], 
                              capture_output=True, text=True, check=True)
        logger.info(f"Found huggingface-cli: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("huggingface-cli not found, will try to install...")
        return False

def install_huggingface_hub():
    """Install huggingface_hub package"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub[cli]"], 
                      check=True)
        logger.info("Successfully installed huggingface_hub")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install huggingface_hub: {e}")
        return False

def download_with_hf_cli(repo, files, local_dir, use_mirror=False):
    """Download files using huggingface-cli"""
    env = os.environ.copy()
    if use_mirror:
        env["HF_ENDPOINT"] = "https://hf-mirror.com"
        logger.info("Using HuggingFace mirror for faster download in China")
    
    cmd = [
        "huggingface-cli", "download", repo,
        *files,
        "--local-dir", local_dir
    ]
    
    logger.info(f"Downloading from {repo} to {local_dir}")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        logger.info("Download completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Download failed: {e}")
        logger.error(f"stderr: {e.stderr}")
        return False

def download_with_wget(repo, files, local_dir):
    """Download files using wget as fallback"""
    base_url = f"https://huggingface.co/{repo}/resolve/main"
    
    os.makedirs(local_dir, exist_ok=True)
    
    for file in files:
        url = f"{base_url}/{file}"
        output_path = os.path.join(local_dir, file)
        
        logger.info(f"Downloading {file}...")
        cmd = ["wget", "-O", output_path, url]
        
        try:
            subprocess.run(cmd, check=True)
            logger.info(f"Successfully downloaded {file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download {file}: {e}")
            return False
    
    return True

def verify_downloads(local_dir, files):
    """Verify that all required files were downloaded"""
    missing_files = []
    
    for file in files:
        file_path = os.path.join(local_dir, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
        else:
            size = os.path.getsize(file_path)
            logger.info(f"✓ {file} ({size:,} bytes)")
    
    if missing_files:
        logger.error(f"Missing files: {missing_files}")
        return False
    
    logger.info("All required files downloaded successfully!")
    return True

def main():
    parser = argparse.ArgumentParser(description="Download IndexTTS model files")
    parser.add_argument(
        "--model", 
        choices=list(MODELS.keys()),
        default="IndexTTS-1.5",
        help="Model version to download"
    )
    parser.add_argument(
        "--output-dir",
        default="checkpoints",
        help="Output directory for model files"
    )
    parser.add_argument(
        "--use-mirror",
        action="store_true",
        help="Use HuggingFace mirror (recommended for users in China)"
    )
    parser.add_argument(
        "--force-wget",
        action="store_true", 
        help="Force use wget instead of huggingface-cli"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing downloads without downloading"
    )
    
    args = parser.parse_args()
    
    model_config = MODELS[args.model]
    repo = model_config["repo"]
    files = model_config["files"]
    
    logger.info(f"Model: {args.model}")
    logger.info(f"Repository: {repo}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Files to download: {len(files)}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Verify only mode
    if args.verify_only:
        success = verify_downloads(args.output_dir, files)
        sys.exit(0 if success else 1)
    
    # Choose download method
    if args.force_wget:
        logger.info("Using wget for download")
        success = download_with_wget(repo, files, args.output_dir)
    else:
        # Try huggingface-cli first
        if check_huggingface_cli() or install_huggingface_hub():
            success = download_with_hf_cli(repo, files, args.output_dir, args.use_mirror)
        else:
            logger.info("Falling back to wget")
            success = download_with_wget(repo, files, args.output_dir)
    
    if success:
        # Verify downloads
        success = verify_downloads(args.output_dir, files)
    
    if success:
        logger.info("✅ Model download completed successfully!")
        logger.info(f"Model files are available in: {os.path.abspath(args.output_dir)}")
    else:
        logger.error("❌ Model download failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
