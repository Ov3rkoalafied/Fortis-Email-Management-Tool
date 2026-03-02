"""Entry point - run with: python run.py"""
import sys

if sys.version_info < (3, 11):
    print("ERROR: Python 3.11 or higher is required.")
    sys.exit(1)

import uvicorn

if __name__ == "__main__":
    print("Starting Fortis Email Management Tool backend...")
    print("API: http://localhost:8000")
    print("Press Ctrl+C to stop.\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
