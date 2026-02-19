"""
WSGI configuration for PythonAnywhere.

This file is automatically written to your PythonAnywhere account
by deploy.py. You do not need to edit or upload this manually.
"""

import sys

# Replace YOUR_USERNAME with your actual PythonAnywhere username.
# deploy.py does this substitution automatically.
project_home = "/home/YOUR_USERNAME/mathquest/src"

if project_home not in sys.path:
    sys.path.insert(0, project_home)

from mathquest.app import app as application  # noqa: E402
