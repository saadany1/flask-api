import requests
import json

def test_server():
    """Test the Flask server endpoints"""
    
    # Test the home endpoint
    try:
        response = requests.get('http://localhost:5000/')
        print(f"✅ Home endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Home endpoint failed: {e}")
    
    # Test the image endpoint
    try:
        response = requests.get('http://localhost:5000/image')
        print(f"✅ Image endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Image endpoint failed: {e}")
    
    # Test the generate-image endpoint (GET)
    try:
        response = requests.get('http://localhost:5000/generate-image')
        print(f"✅ Generate-image GET endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Generate-image GET endpoint failed: {e}")
    
    # Test the generate-image endpoint (POST) with a simple prompt
    try:
        test_data = {'prompt': 'a beautiful sunset over mountains'}
        response = requests.post('http://localhost:5000/generate-image', 
                               json=test_data,
                               headers={'Content-Type': 'application/json'})
        print(f"✅ Generate-image POST endpoint: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"   ✅ Image generated successfully!")
                print(f"   Filename: {result.get('filename')}")
            else:
                print(f"   ❌ Image generation failed: {result.get('error')}")
        else:
            print(f"   ❌ Request failed: {response.text}")
    except Exception as e:
        print(f"❌ Generate-image POST endpoint failed: {e}")

if __name__ == "__main__":
    print("Testing Flask server...")
    print("Make sure the server is running on http://localhost:5000")
    print("=" * 50)
    test_server()
