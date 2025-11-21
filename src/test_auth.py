import asyncio
import httpx

async def test_auth():
    """Test authentication endpoints"""
    
    async with httpx.AsyncClient() as client:
        try:
            # Test the user/me endpoint (should require auth)
            response = await client.get("http://localhost:8000/api/v1/user/me")
            print(f"User/me endpoint status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ User is authenticated")
                data = response.json()
                print(f"User data: {data}")
            elif response.status_code == 401:
                print("❌ User is not authenticated")
            else:
                print(f"Unexpected status: {response.status_code}")
                print(f"Response: {response.text}")
            
            # Test analytics endpoint without auth
            response = await client.get("http://localhost:8000/api/v1/analytics/user/projects")
            print(f"\nAnalytics projects endpoint status: {response.status_code}")
            
            if response.status_code == 401:
                print("✅ Analytics endpoint correctly requires authentication")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth()) 