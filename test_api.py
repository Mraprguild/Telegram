#!/usr/bin/env python3
"""
Test script to verify the status API is working
"""
import requests
import json
import sys

def test_api():
    """Test all API endpoints"""
    base_url = "http://localhost:8000"
    
    print("Testing Movie Bot Status API...")
    print("-" * 40)
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"✓ Root endpoint: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Root endpoint failed: {e}")
        return False
    
    print()
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✓ Health endpoint: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Health endpoint failed: {e}")
        return False
    
    print()
    
    # Test status endpoint
    try:
        response = requests.get(f"{base_url}/status")
        print(f"✓ Status endpoint: {response.status_code}")
        status_data = response.json()
        print(f"  Bot Status: {status_data.get('status')}")
        print(f"  Total Movies: {status_data.get('total_movies_posted')}")
        print(f"  Uptime: {status_data.get('uptime_formatted')}")
        print(f"  Telegram Connected: {status_data.get('telegram_connected')}")
        print(f"  TMDB Connected: {status_data.get('tmdb_connected')}")
        print(f"  RSS Connected: {status_data.get('rss_feed_connected')}")
    except Exception as e:
        print(f"✗ Status endpoint failed: {e}")
        return False
    
    print()
    
    # Test metrics endpoint
    try:
        response = requests.get(f"{base_url}/metrics")
        print(f"✓ Metrics endpoint: {response.status_code}")
        metrics = response.json()
        print(f"  Total Movies: {metrics.get('total_movies_posted')}")
        print(f"  Uptime: {metrics.get('uptime_seconds')} seconds")
    except Exception as e:
        print(f"✗ Metrics endpoint failed: {e}")
        return False
    
    print("-" * 40)
    print("All API tests passed!")
    return True

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
