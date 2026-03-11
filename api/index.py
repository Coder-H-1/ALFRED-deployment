import os
import sys

# Add the project root to sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_path)

from FILES.backend.server import app

# This acts as the entrypoint for Vercel
