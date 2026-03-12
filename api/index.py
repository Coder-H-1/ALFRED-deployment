import os
import sys

# Add the project root to sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from FILES.backend.server import app

# Vercel's @vercel/python runtime will look for the 'app' variable by default.
# No custom 'handler' or wsgi_app wrapping is needed for simple Flask apps.
