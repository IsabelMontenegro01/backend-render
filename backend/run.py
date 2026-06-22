#!/usr/bin/env python3
import uvicorn
import sys

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)
