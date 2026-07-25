"""
manage.py - Management script for the Enterprise AI Data Assistant.

Usage:
    python manage.py runserver           # Start the server on port 8000
    python manage.py runserver 9000      # Start on a custom port
    python manage.py build-frontend      # Build the React frontend into frontend/dist
    python manage.py help
"""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
FRONTEND_INDEX = os.path.join(FRONTEND_DIR, "dist", "index.html")

# Let `app.*` imports resolve from backend/
sys.path.insert(0, BACKEND_DIR)


def runserver(port=8000):
    """Start the development server (API + built frontend)."""
    import uvicorn

    # Relative paths in config (./data/...) are resolved against backend/
    os.chdir(BACKEND_DIR)

    print(f"\n>>> Enterprise AI Data Assistant -> http://localhost:{port}")
    print(f">>> API docs                    -> http://localhost:{port}/docs")
    if os.path.isfile(FRONTEND_INDEX):
        print(f">>> UI (built frontend)         -> http://localhost:{port}/\n")
    else:
        print(">>> UI not built yet. Run: python manage.py build-frontend\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["app"],
    )


def build_frontend():
    """Install deps (if needed) and build the React frontend."""
    npm = "npm.cmd" if os.name == "nt" else "npm"

    if not os.path.isdir(os.path.join(FRONTEND_DIR, "node_modules")):
        print(">>> Installing frontend dependencies...")
        subprocess.check_call([npm, "install"], cwd=FRONTEND_DIR)

    print(">>> Building frontend...")
    subprocess.check_call([npm, "run", "build"], cwd=FRONTEND_DIR)
    print(">>> Build complete: frontend/dist")


def show_help():
    print("""
Enterprise AI Data Assistant - Management Commands
====================================================
  python manage.py runserver          Start server (port 8000)
  python manage.py runserver <port>   Start on a custom port
  python manage.py build-frontend     Build the React frontend
  python manage.py help               Show this help
""")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "help":
        show_help()
    elif args[0] == "runserver":
        runserver(int(args[1]) if len(args) > 1 else 8000)
    elif args[0] == "build-frontend":
        build_frontend()
    else:
        print(f"Unknown command: {args[0]}")
        show_help()
