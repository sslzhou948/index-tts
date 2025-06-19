#!/bin/bash
# Build script for IndexTTS Docker image
# Optimized for Mac M4 and cross-platform compatibility

set -e

# Configuration
IMAGE_NAME="indextts"
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile"
BUILD_CONTEXT="."

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

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    # Check architecture
    ARCH=$(uname -m)
    print_status "Detected architecture: $ARCH"
    
    # Check available disk space (at least 10GB recommended)
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        print_warning "Available disk space is less than 10GB. Build may fail."
    fi
    
    print_success "System requirements check passed"
}

# Function to detect platform and set build args
detect_platform() {
    case "$ARCH" in
        "arm64"|"aarch64")
            PLATFORM="linux/arm64"
            print_status "Building for ARM64 (Apple Silicon)"
            ;;
        "x86_64"|"amd64")
            PLATFORM="linux/amd64"
            print_status "Building for AMD64 (Intel/AMD)"
            ;;
        *)
            print_warning "Unknown architecture: $ARCH. Using default platform."
            PLATFORM="linux/$ARCH"
            ;;
    esac
}

# Function to build Docker image
build_image() {
    print_status "Starting Docker build..."
    print_status "Image: $IMAGE_NAME:$IMAGE_TAG"
    print_status "Platform: $PLATFORM"
    print_status "Context: $BUILD_CONTEXT"
    
    # Build arguments
    BUILD_ARGS=(
        "--platform=$PLATFORM"
        "--tag=$IMAGE_NAME:$IMAGE_TAG"
        "--file=$DOCKERFILE"
        "--progress=plain"
        "$BUILD_CONTEXT"
    )
    
    # Add build cache options for faster rebuilds
    if [ "$USE_CACHE" != "false" ]; then
        BUILD_ARGS+=("--cache-from=$IMAGE_NAME:latest")
    fi
    
    # Add no-cache option if requested
    if [ "$NO_CACHE" = "true" ]; then
        BUILD_ARGS+=("--no-cache")
        print_status "Building without cache"
    fi
    
    # Execute build
    print_status "Executing: docker build ${BUILD_ARGS[*]}"
    
    if docker build "${BUILD_ARGS[@]}"; then
        print_success "Docker image built successfully!"
    else
        print_error "Docker build failed!"
        exit 1
    fi
}

# Function to verify the built image
verify_image() {
    print_status "Verifying built image..."
    
    # Check if image exists
    if docker image inspect "$IMAGE_NAME:$IMAGE_TAG" &> /dev/null; then
        print_success "Image $IMAGE_NAME:$IMAGE_TAG exists"
        
        # Get image size
        IMAGE_SIZE=$(docker image inspect "$IMAGE_NAME:$IMAGE_TAG" --format='{{.Size}}' | numfmt --to=iec)
        print_status "Image size: $IMAGE_SIZE"
        
        # Get image creation date
        CREATED=$(docker image inspect "$IMAGE_NAME:$IMAGE_TAG" --format='{{.Created}}' | cut -d'T' -f1)
        print_status "Created: $CREATED"
        
    else
        print_error "Image verification failed!"
        exit 1
    fi
}

# Function to run basic tests
test_image() {
    print_status "Running basic image tests..."
    
    # Test 1: Check if container starts
    print_status "Test 1: Container startup test"
    if docker run --rm --platform="$PLATFORM" "$IMAGE_NAME:$IMAGE_TAG" python --version; then
        print_success "✓ Python is working"
    else
        print_error "✗ Python test failed"
        return 1
    fi
    
    # Test 2: Check if IndexTTS can be imported
    print_status "Test 2: IndexTTS import test"
    if docker run --rm --platform="$PLATFORM" "$IMAGE_NAME:$IMAGE_TAG" python -c "from indextts.infer import IndexTTS; print('IndexTTS import successful')"; then
        print_success "✓ IndexTTS import successful"
    else
        print_error "✗ IndexTTS import failed"
        return 1
    fi
    
    print_success "All basic tests passed!"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --no-cache          Build without using cache"
    echo "  --no-test           Skip image testing"
    echo "  --tag TAG           Set custom image tag (default: latest)"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Build with default settings"
    echo "  $0 --no-cache       # Build without cache"
    echo "  $0 --tag v1.0       # Build with custom tag"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="true"
            shift
            ;;
        --no-test)
            SKIP_TESTS="true"
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
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
    print_status "IndexTTS Docker Build Script"
    print_status "============================"
    
    check_requirements
    detect_platform
    build_image
    verify_image
    
    if [ "$SKIP_TESTS" != "true" ]; then
        test_image
    fi
    
    print_success "Build completed successfully!"
    print_status "Image: $IMAGE_NAME:$IMAGE_TAG"
    print_status "Platform: $PLATFORM"
    print_status ""
    print_status "Next steps:"
    print_status "1. Download models: python download_models.py"
    print_status "2. Run container: docker-compose up"
    print_status "3. Access API: http://localhost:8000/docs"
    print_status "4. Access Web UI: http://localhost:7860"
}

# Run main function
main "$@"
