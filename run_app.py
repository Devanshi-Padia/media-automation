import os
import uvicorn
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",           # adjust if module path differs
        host="0.0.0.0",
        port=port,
        reload=False,             # no reload in production
        log_level="info"
    )
