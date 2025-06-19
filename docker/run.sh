#!/bin/bash
# Run script for IndexTTS Docker container
# Supports multiple deployment modes and configurations

set -e

# Configuration
IMAGE_NAME="indextts"
IMAGE_TAG="latest"
CONTAINER_NAME="indextts-service"
NETWORK_NAME="indextts-network"

# Default paths
MODEL_DIR="./checkpoints"
OUTPUT_DIR="./outputs"
PROMPTS_DIR="./prompts"

# Default ports
API_PORT="8000"
WEBUI_PORT="7860"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [MODE] [OPTIONS]"
    echo ""
    echo "Modes:"
    echo "  api                 Run API server (default)"
    echo "  webui               Run Web UI"
    echo "  cli                 Run in CLI mode (interactive)"
    echo "  compose             Use docker-compose"
    echo ""
    echo "Options:"
    echo "  --gpu               Enable GPU support"
    echo "  --model-dir DIR     Model directory (default: ./checkpoints)"
    echo "  --output-dir DIR    Output directory (default: ./outputs)"
    echo "  --api-port PORT     API port (default: 8000)"
    echo "  --webui-port PORT   Web UI port (default: 7860)"
    echo "  --detach            Run in background"
    echo "  --remove            Remove container on exit"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 api              # Run API server"
    echo "  $0 webui --gpu      # Run Web UI with GPU"
    echo "  $0 cli              # Interactive CLI mode"
    echo "  $0 compose          # Use docker-compose"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Check if image exists
    if ! docker image inspect "$IMAGE_NAME:$IMAGE_TAG" &> /dev/null; then
        print_error "Docker image $IMAGE_NAME:$IMAGE_TAG not found"
        print_status "Please build the image first: ./docker/build.sh"
        exit 1
    fi
    
    # Create directories
    mkdir -p "$MODEL_DIR" "$OUTPUT_DIR" "$PROMPTS_DIR"
    
    print_success "Prerequisites check passed"
}

# Function to check model files
check_models() {
    print_status "Checking model files..."
    
    REQUIRED_FILES=(
        "config.yaml"
        "bigvgan_generator.pth"
        "bpe.model"
        "gpt.pth"
    )
    
    MISSING_FILES=()
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$MODEL_DIR/$file" ]; then
            MISSING_FILES+=("$file")
        fi
    done
    
    if [ ${#MISSING_FILES[@]} -gt 0 ]; then
        print_warning "Missing model files: ${MISSING_FILES[*]}"
        print_status "Download models with: python download_models.py"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "All required model files found"
    fi
}

# Function to detect GPU support
detect_gpu() {
    if [ "$USE_GPU" = "true" ]; then
        if command -v nvidia-smi &> /dev/null; then
            print_status "NVIDIA GPU detected"
            GPU_ARGS="--gpus all"
            GPU_ENV="-e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility"
        else
            print_warning "GPU requested but nvidia-smi not found"
            print_warning "Falling back to CPU mode"
            GPU_ARGS=""
            GPU_ENV=""
        fi
    else
        GPU_ARGS=""
        GPU_ENV=""
    fi
}

# Function to stop existing container
stop_existing_container() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Stopping existing container..."
        docker stop "$CONTAINER_NAME" || true
    fi
    
    if [ "$REMOVE_CONTAINER" = "true" ]; then
        if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
            print_status "Removing existing container..."
            docker rm "$CONTAINER_NAME" || true
        fi
    fi
}

# Function to run API server
run_api_server() {
    print_status "Starting IndexTTS API server..."
    
    DOCKER_ARGS=(
        "run"
        "--name" "$CONTAINER_NAME"
        "--platform" "linux/$(uname -m)"
        "-p" "$API_PORT:8000"
        "-v" "$(pwd)/$MODEL_DIR:/app/checkpoints:ro"
        "-v" "$(pwd)/$OUTPUT_DIR:/app/outputs"
        "-v" "$(pwd)/$PROMPTS_DIR:/app/prompts"
        "-e" "API_HOST=0.0.0.0"
        "-e" "API_PORT=8000"
        "-e" "MODEL_DIR=/app/checkpoints"
        "-e" "CONFIG_PATH=/app/checkpoints/config.yaml"
    )
    
    # Add GPU support if enabled
    if [ -n "$GPU_ARGS" ]; then
        DOCKER_ARGS+=($GPU_ARGS)
    fi
    if [ -n "$GPU_ENV" ]; then
        DOCKER_ARGS+=($GPU_ENV)
    fi
    
    # Add detach mode if requested
    if [ "$DETACH_MODE" = "true" ]; then
        DOCKER_ARGS+=("-d")
    else
        DOCKER_ARGS+=("-it")
    fi
    
    # Add remove on exit if requested
    if [ "$REMOVE_CONTAINER" = "true" ]; then
        DOCKER_ARGS+=("--rm")
    fi
    
    DOCKER_ARGS+=("$IMAGE_NAME:$IMAGE_TAG" "python" "api_server.py")
    
    print_status "Command: docker ${DOCKER_ARGS[*]}"
    docker "${DOCKER_ARGS[@]}"
    
    if [ "$DETACH_MODE" = "true" ]; then
        print_success "API server started in background"
        print_status "API documentation: http://localhost:$API_PORT/docs"
        print_status "Health check: http://localhost:$API_PORT/health"
    fi
}

# Function to run Web UI
run_webui() {
    print_status "Starting IndexTTS Web UI..."
    
    DOCKER_ARGS=(
        "run"
        "--name" "$CONTAINER_NAME"
        "--platform" "linux/$(uname -m)"
        "-p" "$WEBUI_PORT:7860"
        "-v" "$(pwd)/$MODEL_DIR:/app/checkpoints:ro"
        "-v" "$(pwd)/$OUTPUT_DIR:/app/outputs"
        "-v" "$(pwd)/$PROMPTS_DIR:/app/prompts"
        "-e" "MODEL_DIR=/app/checkpoints"
    )
    
    # Add GPU support if enabled
    if [ -n "$GPU_ARGS" ]; then
        DOCKER_ARGS+=($GPU_ARGS)
    fi
    if [ -n "$GPU_ENV" ]; then
        DOCKER_ARGS+=($GPU_ENV)
    fi
    
    # Add detach mode if requested
    if [ "$DETACH_MODE" = "true" ]; then
        DOCKER_ARGS+=("-d")
    else
        DOCKER_ARGS+=("-it")
    fi
    
    # Add remove on exit if requested
    if [ "$REMOVE_CONTAINER" = "true" ]; then
        DOCKER_ARGS+=("--rm")
    fi
    
    DOCKER_ARGS+=("$IMAGE_NAME:$IMAGE_TAG" "python" "webui.py" "--host" "0.0.0.0" "--port" "7860")
    
    print_status "Command: docker ${DOCKER_ARGS[*]}"
    docker "${DOCKER_ARGS[@]}"
    
    if [ "$DETACH_MODE" = "true" ]; then
        print_success "Web UI started in background"
        print_status "Access Web UI: http://localhost:$WEBUI_PORT"
    fi
}

# Function to run CLI mode
run_cli() {
    print_status "Starting IndexTTS CLI mode..."
    
    DOCKER_ARGS=(
        "run"
        "--name" "$CONTAINER_NAME"
        "--platform" "linux/$(uname -m)"
        "-it"
        "-v" "$(pwd)/$MODEL_DIR:/app/checkpoints:ro"
        "-v" "$(pwd)/$OUTPUT_DIR:/app/outputs"
        "-v" "$(pwd)/$PROMPTS_DIR:/app/prompts"
        "-e" "MODEL_DIR=/app/checkpoints"
    )
    
    # Add GPU support if enabled
    if [ -n "$GPU_ARGS" ]; then
        DOCKER_ARGS+=($GPU_ARGS)
    fi
    if [ -n "$GPU_ENV" ]; then
        DOCKER_ARGS+=($GPU_ENV)
    fi
    
    # Add remove on exit if requested
    if [ "$REMOVE_CONTAINER" = "true" ]; then
        DOCKER_ARGS+=("--rm")
    fi
    
    DOCKER_ARGS+=("$IMAGE_NAME:$IMAGE_TAG" "/bin/bash")
    
    print_status "Command: docker ${DOCKER_ARGS[*]}"
    print_status "Use 'indextts --help' for CLI usage"
    docker "${DOCKER_ARGS[@]}"
}

# Function to run with docker-compose
run_compose() {
    print_status "Starting with docker-compose..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found"
        exit 1
    fi
    
    COMPOSE_ARGS=("up")
    
    if [ "$DETACH_MODE" = "true" ]; then
        COMPOSE_ARGS+=("-d")
    fi
    
    print_status "Command: docker-compose ${COMPOSE_ARGS[*]}"
    docker-compose "${COMPOSE_ARGS[@]}"
    
    if [ "$DETACH_MODE" = "true" ]; then
        print_success "Services started in background"
        print_status "API: http://localhost:8000/docs"
        print_status "Web UI: http://localhost:7860"
    fi
}

# Parse command line arguments
MODE="api"
USE_GPU="false"
DETACH_MODE="false"
REMOVE_CONTAINER="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        api|webui|cli|compose)
            MODE="$1"
            shift
            ;;
        --gpu)
            USE_GPU="true"
            shift
            ;;
        --model-dir)
            MODEL_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --api-port)
            API_PORT="$2"
            shift 2
            ;;
        --webui-port)
            WEBUI_PORT="$2"
            shift 2
            ;;
        --detach)
            DETACH_MODE="true"
            shift
            ;;
        --remove)
            REMOVE_CONTAINER="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "IndexTTS Docker Run Script"
    print_status "=========================="
    print_status "Mode: $MODE"
    
    if [ "$MODE" != "compose" ]; then
        check_prerequisites
        check_models
        detect_gpu
        stop_existing_container
    fi
    
    case $MODE in
        "api")
            run_api_server
            ;;
        "webui")
            run_webui
            ;;
        "cli")
            run_cli
            ;;
        "compose")
            run_compose
            ;;
        *)
            print_error "Unknown mode: $MODE"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
