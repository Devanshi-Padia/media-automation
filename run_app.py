import uvicorn
import os
import sys

# Ensure local src path is included
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",                           # Required by Render
        port=int(os.getenv("PORT", 8000)),        # Required by Render
        reload=False,                             # reload=True requires Rust; fails on Render
        log_level="info"
    )
