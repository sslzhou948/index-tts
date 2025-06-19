#!/usr/bin/env python3
"""
Test script for IndexTTS Docker deployment
Validates the Docker setup and basic functionality
"""

import os
import sys
import time
import requests
import subprocess
import tempfile
from pathlib import Path

def print_status(message):
    print(f"[INFO] {message}")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"Docker is available: {result.stdout.strip()}")
            return True
        else:
            print_error("Docker is not working properly")
            return False
    except FileNotFoundError:
        print_error("Docker is not installed")
        return False

def check_image():
    """Check if IndexTTS Docker image exists"""
    try:
        result = subprocess.run(["docker", "image", "inspect", "indextts:latest"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print_success("IndexTTS Docker image found")
            return True
        else:
            print_error("IndexTTS Docker image not found. Please build it first.")
            return False
    except Exception as e:
        print_error(f"Error checking Docker image: {e}")
        return False

def test_api_container():
    """Test API container startup and basic functionality"""
    print_status("Testing API container...")
    
    container_name = "indextts-test-api"
    
    # Stop and remove existing test container
    subprocess.run(["docker", "stop", container_name], capture_output=True)
    subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    try:
        # Start container in background
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", "8001:8000",  # Use different port to avoid conflicts
            "indextts:latest",
            "python", "api_server.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"Failed to start API container: {result.stderr}")
            return False
        
        print_status("API container started, waiting for initialization...")
        
        # Wait for container to be ready
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get("http://localhost:8001/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    print_success(f"API health check passed: {health_data}")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
            print_status(f"Waiting for API... ({attempt + 1}/{max_attempts})")
        
        print_error("API container failed to respond within timeout")
        return False
        
    except Exception as e:
        print_error(f"Error testing API container: {e}")
        return False
    
    finally:
        # Cleanup
        subprocess.run(["docker", "stop", container_name], capture_output=True)
        subprocess.run(["docker", "rm", container_name], capture_output=True)

def test_webui_container():
    """Test Web UI container startup"""
    print_status("Testing Web UI container...")
    
    container_name = "indextts-test-webui"
    
    # Stop and remove existing test container
    subprocess.run(["docker", "stop", container_name], capture_output=True)
    subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    try:
        # Start container in background
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", "7861:7860",  # Use different port to avoid conflicts
            "indextts:latest",
            "python", "webui.py", "--host", "0.0.0.0", "--port", "7860"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"Failed to start Web UI container: {result.stderr}")
            return False
        
        print_status("Web UI container started, waiting for initialization...")
        
        # Wait for container to be ready
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                response = requests.get("http://localhost:7861", timeout=5)
                if response.status_code == 200:
                    print_success("Web UI is accessible")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(3)
            print_status(f"Waiting for Web UI... ({attempt + 1}/{max_attempts})")
        
        print_error("Web UI container failed to respond within timeout")
        return False
        
    except Exception as e:
        print_error(f"Error testing Web UI container: {e}")
        return False
    
    finally:
        # Cleanup
        subprocess.run(["docker", "stop", container_name], capture_output=True)
        subprocess.run(["docker", "rm", container_name], capture_output=True)

def test_cli_container():
    """Test CLI container functionality"""
    print_status("Testing CLI container...")
    
    try:
        # Test basic Python import
        cmd = [
            "docker", "run", "--rm",
            "indextts:latest",
            "python", "-c", "from indextts.infer import IndexTTS; print('IndexTTS import successful')"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and "IndexTTS import successful" in result.stdout:
            print_success("CLI container test passed")
            return True
        else:
            print_error(f"CLI container test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print_error("CLI container test timed out")
        return False
    except Exception as e:
        print_error(f"Error testing CLI container: {e}")
        return False

def test_volume_mounts():
    """Test volume mounting functionality"""
    print_status("Testing volume mounts...")
    
    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            test_output_dir = os.path.join(temp_dir, "outputs")
            os.makedirs(test_output_dir, exist_ok=True)
            
            # Test file creation in mounted volume
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{test_output_dir}:/app/outputs",
                "indextts:latest",
                "python", "-c", "open('/app/outputs/test.txt', 'w').write('test')"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Check if file was created on host
                test_file = os.path.join(test_output_dir, "test.txt")
                if os.path.exists(test_file):
                    print_success("Volume mount test passed")
                    return True
                else:
                    print_error("Volume mount test failed: file not created on host")
                    return False
            else:
                print_error(f"Volume mount test failed: {result.stderr}")
                return False
                
    except Exception as e:
        print_error(f"Error testing volume mounts: {e}")
        return False

def main():
    """Run all tests"""
    print_status("IndexTTS Docker Test Suite")
    print_status("=" * 40)
    
    tests = [
        ("Docker availability", check_docker),
        ("Docker image", check_image),
        ("Volume mounts", test_volume_mounts),
        ("CLI container", test_cli_container),
        ("API container", test_api_container),
        ("Web UI container", test_webui_container),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print_status(f"Running test: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_error(f"Test {test_name} failed with exception: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print_status("Test Results Summary")
    print_status("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print()
    print_status(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print_success("All tests passed! Docker setup is working correctly.")
        return 0
    else:
        print_error(f"{total - passed} tests failed. Please check the setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
