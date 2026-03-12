import os
import sys

# Add the project root to sys.path so FILES can be imported
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from FILES.backend.server import app

# Vercel entry point
def handler(request, response):
    return app(request, response)

if __name__ == "__main__":
    app.run()
