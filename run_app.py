import uvicorn
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    print("🚀 Starting FastAPI application on http://127.0.0.1:8000")
    print("📱 All routes are now consolidated on port 8000")
    print("🔗 Access the application at: http://127.0.0.1:8000")
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 