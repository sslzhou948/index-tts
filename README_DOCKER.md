# IndexTTS Docker Deployment Guide

This guide provides comprehensive instructions for deploying IndexTTS using Docker, optimized for cross-platform compatibility including macOS with Apple Silicon (M4).

## 🚀 Quick Start

### 1. Download Models
```bash
# Download IndexTTS-1.5 models (recommended)
python download_models.py --model IndexTTS-1.5

# For users in China (faster download)
python download_models.py --model IndexTTS-1.5 --use-mirror
```

### 2. Build Docker Image
```bash
# Build with automatic platform detection
./docker/build.sh

# Build without cache (clean build)
./docker/build.sh --no-cache
```

### 3. Run the Service
```bash
# Run API server
./docker/run.sh api

# Run Web UI
./docker/run.sh webui

# Run with docker-compose (recommended for production)
./docker/run.sh compose --detach
```

## 📋 Prerequisites

### System Requirements
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later (for compose mode)
- **Disk Space**: At least 15GB free space
- **Memory**: 8GB RAM recommended (4GB minimum)
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended)

### Platform Support
- ✅ **macOS** (Intel and Apple Silicon M1/M2/M4)
- ✅ **Linux** (x86_64 and ARM64)
- ✅ **Windows** (with WSL2)

### For macOS Users
1. Install Docker Desktop for Mac
2. Enable "Use Rosetta for x86/amd64 emulation" in Docker settings (for M1/M2/M4)
3. Allocate at least 8GB RAM to Docker in preferences

## 🏗️ Building the Docker Image

### Basic Build
```bash
./docker/build.sh
```

### Advanced Build Options
```bash
# Build with custom tag
./docker/build.sh --tag v1.5

# Build without cache (clean build)
./docker/build.sh --no-cache

# Skip image testing
./docker/build.sh --no-test
```

### Manual Build (Alternative)
```bash
# For Apple Silicon Macs
docker build --platform linux/arm64 -t indextts:latest .

# For Intel/AMD systems
docker build --platform linux/amd64 -t indextts:latest .
```

## 🚀 Running the Service

### Method 1: Using Run Script (Recommended)

#### API Server Mode
```bash
# Basic API server
./docker/run.sh api

# API server with GPU support
./docker/run.sh api --gpu

# API server in background
./docker/run.sh api --detach

# Custom ports and directories
./docker/run.sh api --api-port 9000 --model-dir ./my-models --output-dir ./my-outputs
```

#### Web UI Mode
```bash
# Basic Web UI
./docker/run.sh webui

# Web UI with GPU support
./docker/run.sh webui --gpu --detach

# Custom Web UI port
./docker/run.sh webui --webui-port 8080
```

#### CLI Mode (Interactive)
```bash
# Interactive shell for CLI usage
./docker/run.sh cli

# Inside the container, use:
indextts "Hello, this is a test" --voice /app/prompts/sample.wav --output /app/outputs/test.wav
```

### Method 2: Docker Compose (Production)

#### Basic Usage
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down
```

#### With GPU Support
Edit `docker-compose.yml` and uncomment the GPU section:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### Method 3: Manual Docker Commands

#### API Server
```bash
docker run -d \
  --name indextts-api \
  -p 8000:8000 \
  -v ./checkpoints:/app/checkpoints:ro \
  -v ./outputs:/app/outputs \
  indextts:latest python api_server.py
```

#### Web UI
```bash
docker run -d \
  --name indextts-webui \
  -p 7860:7860 \
  -v ./checkpoints:/app/checkpoints:ro \
  -v ./outputs:/app/outputs \
  indextts:latest python webui.py --host 0.0.0.0 --port 7860
```

## 🔧 Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `MODEL_DIR` | `/app/checkpoints` | Model files directory |
| `CONFIG_PATH` | `/app/checkpoints/config.yaml` | Config file path |
| `CUDA_VISIBLE_DEVICES` | `0` | GPU device selection |

### Volume Mounts
| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./checkpoints` | `/app/checkpoints` | Model files (read-only) |
| `./outputs` | `/app/outputs` | Generated audio files |
| `./prompts` | `/app/prompts` | Reference audio files |

### Port Mapping
| Service | Container Port | Host Port | Description |
|---------|----------------|-----------|-------------|
| API Server | 8000 | 8000 | REST API endpoints |
| Web UI | 7860 | 7860 | Gradio web interface |

## 🌐 API Usage

### Health Check
```bash
curl http://localhost:8000/health
```

### Text-to-Speech Synthesis
```bash
curl -X POST "http://localhost:8000/tts/synthesize" \
  -H "Content-Type: multipart/form-data" \
  -F "text=Hello, this is IndexTTS speaking!" \
  -F "voice_file=@reference_voice.wav"
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 Model Management

### Download Models
```bash
# Download IndexTTS-1.5 (latest)
python download_models.py --model IndexTTS-1.5

# Download IndexTTS-1.0
python download_models.py --model IndexTTS-1.0

# Use mirror for faster download in China
python download_models.py --use-mirror

# Verify existing downloads
python download_models.py --verify-only
```

### Model Files Structure
```
checkpoints/
├── config.yaml              # Model configuration
├── bigvgan_generator.pth     # BigVGAN generator weights
├── bigvgan_discriminator.pth # BigVGAN discriminator weights
├── bpe.model                 # Byte-pair encoding model
├── dvae.pth                  # DVAE weights
├── gpt.pth                   # GPT model weights
└── unigram_12000.vocab       # Vocabulary file
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Model Files Not Found
```bash
# Check if models are downloaded
ls -la checkpoints/

# Download missing models
python download_models.py --model IndexTTS-1.5
```

#### 2. GPU Not Detected
```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

#### 3. Permission Issues
```bash
# Fix ownership of output directory
sudo chown -R $USER:$USER outputs/

# Or run with user mapping
docker run --user $(id -u):$(id -g) ...
```

#### 4. Memory Issues
```bash
# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Memory > 8GB+

# Or use swap if needed
docker run --memory=6g --memory-swap=8g ...
```

#### 5. Port Already in Use
```bash
# Check what's using the port
lsof -i :8000

# Use different port
./docker/run.sh api --api-port 9000
```

### Mac-Specific Issues

#### Apple Silicon Compatibility
```bash
# Force ARM64 build
docker build --platform linux/arm64 -t indextts:latest .

# Check platform
docker image inspect indextts:latest | grep Architecture
```

#### Rosetta Emulation
If you encounter issues with x86_64 images on Apple Silicon:
1. Enable Rosetta in Docker Desktop settings
2. Use `--platform linux/amd64` flag when needed

### Logs and Debugging

#### View Container Logs
```bash
# API server logs
docker logs indextts-service

# Follow logs in real-time
docker logs -f indextts-service

# Web UI logs
docker logs indextts-webui
```

#### Debug Mode
```bash
# Run with debug output
docker run -it --rm \
  -v ./checkpoints:/app/checkpoints:ro \
  indextts:latest python -c "
from indextts.infer import IndexTTS
tts = IndexTTS(model_dir='/app/checkpoints')
print('Model loaded successfully!')
"
```

## 🚀 Production Deployment

### Using Docker Compose with Nginx
```bash
# Start with production profile
docker-compose --profile production up -d
```

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4'
    reservations:
      memory: 4G
      cpus: '2'
```

### Health Monitoring
```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect --format='{{.State.Health}}' indextts-service
```

## 📊 Performance Optimization

### GPU Acceleration
- Ensure NVIDIA drivers are installed
- Use `--gpu` flag or enable GPU in docker-compose
- Monitor GPU usage with `nvidia-smi`

### Memory Management
- Allocate sufficient RAM to Docker
- Use swap if physical memory is limited
- Monitor memory usage with `docker stats`

### Storage Optimization
- Use read-only mounts for model files
- Regular cleanup of output files
- Consider using Docker volumes for persistent data

## 🔒 Security Considerations

### Container Security
- Runs as non-root user (`appuser`)
- Read-only model directory
- Limited resource allocation
- Health checks enabled

### Network Security
- Use reverse proxy (Nginx) for production
- Enable HTTPS with SSL certificates
- Restrict API access with authentication if needed

## 📚 Additional Resources

- [IndexTTS GitHub Repository](https://github.com/index-tts/index-tts)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit)

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review container logs for error messages
3. Ensure all prerequisites are met
4. Try rebuilding the image with `--no-cache`
5. Open an issue on the GitHub repository

## 📝 License

This Docker packaging follows the same license as the original IndexTTS project.
