import uvicorn
import os

if __name__ == "__main__":
    # Run FastAPI app
    print("Starting Kinmen Land Cloud FastAPI Backend on http://localhost:8080 ...")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8080, reload=False, log_level="info")
